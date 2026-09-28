"""Stage 4a: narration audio per language, from TTS or an uploaded recording.

Outputs per language:
  voice/narration.<lang>.mp3   the full narration
  voice/timing.<lang>.json     {"units": [{id, start, end, words: [{start,end,word}]}]}
"""

from __future__ import annotations

from pathlib import Path

from mococo.media import ffmpeg, stt, tts
from mococo.project import Project

GAP = 0.35  # seconds of silence between units


def run(project: Project, *, lang: str | None = None, force: bool = False) -> list[Path]:
    s = project.load()
    out = []
    for l in s.voice_langs:
        if lang and l != lang:
            continue
        if project.uploaded_narration(l).exists():
            out.append(align_upload(project, l, force=force))
        else:
            out.append(synthesize(project, l, force=force))
    return out


def synthesize(project: Project, lang: str, *, force: bool = False) -> Path:
    s = project.load()
    audio, timing = project.narration_audio(lang), project.narration_timing(lang)
    if audio.exists() and timing.exists() and not force:
        return audio
    seg = project.read_json(project.segments_json)
    voice = getattr(s.voice, lang)
    parts_dir = project.voice_dir / f"parts.{lang}"
    parts_dir.mkdir(parents=True, exist_ok=True)
    silence = parts_dir / "gap.mp3"
    ffmpeg.run(["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{GAP}", "-c:a", "libmp3lame", "-q:a", "4", str(silence)])

    units, files, cursor = [], [], 0.0
    for u in seg["units"]:
        text = u["text"].get(lang)
        if not text:
            raise RuntimeError(f"unit {u['id']} has no {lang} text; run `mococo script translate {lang}`")
        part = parts_dir / f'{u["id"]}.mp3'
        words = tts.synthesize(text, voice, part, rate=s.voice.rate)
        dur = ffmpeg.audio_duration(part)
        units.append(
            {
                "id": u["id"],
                "start": round(cursor, 3),
                "end": round(cursor + dur, 3),
                "words": [{**w, "start": round(w["start"] + cursor, 3), "end": round(w["end"] + cursor, 3)} for w in words],
            }
        )
        files += [part, silence]
        cursor += dur + GAP
    files = files[:-1]  # no trailing gap
    _concat_audio(files, audio)
    project.write_json(timing, {"lang": lang, "voice": voice, "source": "tts", "units": units})
    project.log_event("stage_done", stage="voice.tts", lang=lang, seconds=round(cursor, 1))
    return audio


def _concat_audio(files: list[Path], out: Path) -> None:
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in files), encoding="utf-8")
    ffmpeg.run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "3", "-ar", "24000", str(out)])


def align_upload(project: Project, lang: str, *, force: bool = False) -> Path:
    """Map an uploaded narration to units by matching whisper words to unit text."""
    import difflib

    audio, timing = project.narration_audio(lang), project.narration_timing(lang)
    if audio.exists() and timing.exists() and not force:
        return audio
    upload = project.uploaded_narration(lang)
    seg = project.read_json(project.segments_json)
    words = stt.align_words(upload, language=lang)
    if not words:
        raise RuntimeError(f"no speech found in {upload}")

    def toks(text: str) -> list[str]:
        text = "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace())
        return list(text.replace(" ", "")) if lang == "zh" else text.split()

    stream = [toks(w["word"]) for w in words]
    flat, owner = [], []
    for i, ts in enumerate(stream):
        flat += ts
        owner += [i] * len(ts)
    units, pos = [], 0
    for u in seg["units"]:
        ut = toks(u["text"][lang])
        window = flat[pos : pos + int(len(ut) * 1.6) + 20]
        m = difflib.SequenceMatcher(None, window, ut, autojunk=False).get_matching_blocks()
        m = [b for b in m if b.size > 0]
        if not m:
            raise RuntimeError(f"could not find unit {u['id']} in the recording; check the upload matches the script")
        first, last = pos + m[0].a, pos + m[-1].a + m[-1].size - 1
        w0, w1 = words[owner[first]], words[owner[last]]
        units.append({"id": u["id"], "start": w0["start"], "end": w1["end"], "words": words[owner[first] : owner[last] + 1]})
        pos = last + 1
    ffmpeg.run(["-i", str(upload), "-c:a", "libmp3lame", "-q:a", "3", str(audio)])
    project.write_json(timing, {"lang": lang, "voice": "upload", "source": "upload", "units": units})
    project.log_event("stage_done", stage="voice.upload", lang=lang, units=len(units))
    return audio
