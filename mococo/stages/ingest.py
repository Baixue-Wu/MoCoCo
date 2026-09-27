"""Stage 0: turn a film into shots, keyframes, transcript, captions, and an index."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from mococo import prompts
from mococo.media import ffmpeg, shots as shotdet, stt
from mococo.project import Project
from mococo.provider import embed, llm

CAPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "shots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description_en": {"type": "string"},
                    "description_zh": {"type": "string"},
                    "mood": {"type": "string"},
                    "characters": {"type": "array", "items": {"type": "string"}},
                    "setting": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "description_en", "description_zh", "mood", "characters", "setting", "tags"],
            },
        }
    },
    "required": ["shots"],
}


def detect(project: Project, *, force: bool = False) -> list[dict]:
    """shots.json: [{id, start, end, duration, frame}]"""
    if project.shots_json.exists() and not force:
        return project.read_json(project.shots_json)
    s = project.load()
    film = Path(s.film)
    spans = shotdet.detect_shots(film)
    shots = []
    for i, (a, b) in enumerate(spans, 1):
        sid = f"s{i:04d}"
        shots.append(
            {
                "id": sid,
                "start": round(a, 3),
                "end": round(b, 3),
                "duration": round(b - a, 3),
                "frame": f"frames/{sid}.jpg",
            }
        )
    project.write_json(project.shots_json, shots)
    project.log_event("stage_done", stage="ingest.detect", shots=len(shots))
    return shots


def frames(project: Project, shots: list[dict], *, workers: int = 8, force: bool = False) -> None:
    film = Path(project.load().film)

    def one(sh):
        out = project.ingest / sh["frame"]
        if out.exists() and not force:
            return
        mid = (sh["start"] + sh["end"]) / 2
        ffmpeg.extract_frame(film, mid, out)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, shots))


def transcribe(project: Project, *, model_size: str = "small", force: bool = False) -> dict:
    if project.transcript_json.exists() and not force:
        return project.read_json(project.transcript_json)
    film = Path(project.load().film)
    wav = project.ingest / "audio16k.wav"
    if not wav.exists():
        ffmpeg.extract_audio(film, wav)
    result = stt.transcribe(wav, size=model_size)
    project.write_json(project.transcript_json, result)
    project.log_event("stage_done", stage="ingest.transcribe", segments=len(result["segments"]), language=result["language"])
    return result


def dialogue_for(shot: dict, transcript: dict) -> str:
    """Transcript text overlapping the shot's time range."""
    parts = [
        seg["text"]
        for seg in transcript["segments"]
        if seg["end"] > shot["start"] and seg["start"] < shot["end"]
    ]
    return " ".join(parts).strip()


def caption(
    project: Project,
    shots: list[dict],
    transcript: dict,
    *,
    batch: int = 8,
    workers: int = 4,
    force: bool = False,
) -> dict:
    """captions.json: {shot_id: {description_en, description_zh, mood, characters, setting, tags, dialogue}}"""
    existing = project.read_json(project.captions_json) if project.captions_json.exists() and not force else {}
    title = project.load().title
    todo = [sh for sh in shots if sh["id"] not in existing]
    batches = [todo[i : i + batch] for i in range(0, len(todo), batch)]

    def one(group):
        lines = []
        for k, sh in enumerate(group, 1):
            d = dialogue_for(sh, transcript)
            lines.append(f'{k}. id={sh["id"]} time={sh["start"]:.1f}-{sh["end"]:.1f}s dialogue="{d}"')
        prompt = prompts.render("caption_shots", title=title, n=len(group), shots="\n".join(lines))
        images = [project.ingest / sh["frame"] for sh in group]
        result = llm.ask(prompt, tier="fast", images=images, schema=CAPTION_SCHEMA, log=project.log_event)
        out = {}
        for item in result["shots"]:
            out[item["id"]] = item
        missing = [sh["id"] for sh in group if sh["id"] not in out]
        if missing:
            raise llm.LLMError(f"caption batch returned no entry for shots {missing}")
        return out

    with ThreadPoolExecutor(workers) as ex:
        for res in ex.map(one, batches):
            for sid, item in res.items():
                item["dialogue"] = dialogue_for(next(s for s in shots if s["id"] == sid), transcript)
                existing[sid] = item
            project.write_json(project.captions_json, existing)  # checkpoint after every batch
    project.log_event("stage_done", stage="ingest.caption", shots=len(existing))
    return existing


def index(project: Project, shots: list[dict], captions: dict, *, force: bool = False) -> None:
    """index.npz: ids + unit vectors over 'description_en. dialogue' per shot."""
    if project.index_npz.exists() and not force:
        return
    ids = [sh["id"] for sh in shots]
    texts = []
    for sid in ids:
        c = captions[sid]
        text = f'{c["description_en"]} Mood: {c["mood"]}. Tags: {", ".join(c["tags"])}.'
        if c.get("dialogue"):
            text += f' Dialogue: {c["dialogue"]}'
        texts.append(text)
    vecs = embed.embed(texts)
    np.savez(project.index_npz, ids=np.array(ids), vecs=vecs)
    project.log_event("stage_done", stage="ingest.index", shots=len(ids))


def run(project: Project, *, force: bool = False, whisper_size: str = "small", workers: int = 4) -> dict:
    """Everything, resumable. Returns a small summary."""
    shots = detect(project, force=force)
    frames(project, shots, force=force)
    transcript = transcribe(project, model_size=whisper_size, force=force)
    captions = caption(project, shots, transcript, workers=workers, force=force)
    index(project, shots, captions, force=force)
    return {"shots": len(shots), "transcript_segments": len(transcript["segments"]), "language": transcript["language"]}
