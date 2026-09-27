"""Speech to text with faster-whisper on CPU."""

from __future__ import annotations

from pathlib import Path

from mococo import config

_model = None


def _get(size: str):
    global _model
    if _model is None or _model[0] != size:
        from faster_whisper import WhisperModel

        _model = (size, WhisperModel(size, device="cpu", compute_type="int8", download_root=str(config.models_dir())))
    return _model[1]


def transcribe(audio: Path, size: str = "small", language: str | None = None) -> dict:
    """Return {"language": str, "segments": [{"start","end","text"}]}."""
    model = _get(size)
    segments, info = model.transcribe(str(audio), language=language, vad_filter=True, beam_size=5)
    out = [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()} for s in segments]
    return {"language": info.language, "segments": out}


def align_words(audio: Path, size: str = "small", language: str | None = None) -> list[dict]:
    """Word-level timestamps, used to align an uploaded narration to script units."""
    model = _get(size)
    segments, _ = model.transcribe(str(audio), language=language, word_timestamps=True, vad_filter=True)
    words = []
    for s in segments:
        for w in s.words or []:
            words.append({"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip()})
    return words
