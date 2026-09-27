"""Text to speech with edge-tts (Microsoft neural voices, no key needed).

synthesize() also returns word boundaries so subtitles can be timed precisely.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts


async def _synth(text: str, voice: str, rate: str, out: Path) -> list[dict]:
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words: list[dict] = []
    with out.open("wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offsets are in 100ns ticks
                words.append(
                    {
                        "start": round(chunk["offset"] / 1e7, 3),
                        "end": round((chunk["offset"] + chunk["duration"]) / 1e7, 3),
                        "word": chunk["text"],
                    }
                )
    return words


def synthesize(text: str, voice: str, out: Path, rate: str = "+0%") -> list[dict]:
    """Write mp3 to out; return word boundaries [{start, end, word}] in seconds."""
    out.parent.mkdir(parents=True, exist_ok=True)
    words = asyncio.run(_synth(text, voice, rate, out))
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"edge-tts produced nothing for voice {voice}; check network and voice name")
    return words


def list_voices(lang_prefix: str) -> list[str]:
    voices = asyncio.run(edge_tts.list_voices())
    return sorted(v["ShortName"] for v in voices if v["ShortName"].startswith(lang_prefix))
