"""Export the finished Sherlock Jr. project as a read-only web example.

Run from the repository root after producing projects/sherlock-jr. The source
film and intermediate render clips stay out of Git; this exports only small
project decisions, the selected keyframes, and the narration audio.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from mococo.media import ffmpeg

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "sherlock-jr"
DEST = ROOT / "web" / "public" / "examples" / "sherlock-jr"


def read(path: str):
    return json.loads((PROJECT / path).read_text(encoding="utf-8"))


def main() -> None:
    settings = read("project.json")
    shots = read("ingest/shots.json")
    captions = read("ingest/captions.json")
    segments = read("script/segments.json")
    candidates = read("retrieval/candidates.json")
    timeline = read("cut/timeline.json")
    timing = read("voice/timing.zh.json")
    script = (PROJECT / "script" / "script.zh.md").read_text(encoding="utf-8").strip()

    candidate_ids = {shot["shot_id"] for unit in candidates["units"] for shot in unit["shots"]}
    used_ids = {
        clip["shot_id"]
        for unit in timeline["units"]
        for clip in unit["clips"]
        if "shot_id" in clip
    }
    frame_ids = candidate_ids | used_ids
    selected_shots = [shot for shot in shots if shot["id"] in frame_ids]
    missing = frame_ids - {shot["id"] for shot in selected_shots}
    if missing:
        raise ValueError(f"shots missing from ingest metadata: {sorted(missing)}")

    frames = DEST / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for shot in selected_shots:
        src = PROJECT / "ingest" / "frames" / f"{shot['id']}.jpg"
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copyfile(src, frames / src.name)
    shutil.copyfile(PROJECT / "voice" / "narration.zh.mp3", DEST / "narration.zh.mp3")

    data = {
        "title": settings["title"],
        "style": settings["style"],
        "target_minutes": settings["target_minutes"],
        "brief": settings["brief"],
        "film": ffmpeg.probe(ROOT / "data" / "films" / "Sherlock_Jr.1924.webm"),
        "shot_count": len(shots),
        "caption_count": sum(bool(value.get("description_zh")) for value in captions.values()),
        "script": script,
        "segments": segments,
        "candidates": candidates,
        "timeline": timeline,
        "timing": timing,
        "shots": selected_shots,
        "captions": {shot_id: captions[shot_id] for shot_id in frame_ids if shot_id in captions},
        "source_url": "https://github.com/Baixue-Wu/MoCoCo/releases/download/demo-sherlock-jr-v1/Sherlock_Jr.1924.webm",
        "result_url": "https://baixue-wu.github.io/MoCoCo/assets/sherlock-jr-recap.mp4",
        "full_result_url": "https://github.com/Baixue-Wu/MoCoCo/releases/download/demo-sherlock-jr-v1/sherlock-jr-recap-full.mp4",
    }
    (DEST / "project.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Exported {len(selected_shots)} keyframes and {len(segments['units'])} units to {DEST}")


if __name__ == "__main__":
    main()
