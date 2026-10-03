"""Thin ffmpeg wrapper. Binary comes from imageio-ffmpeg so all three OSes work."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import imageio_ffmpeg


class FFmpegError(RuntimeError):
    pass


def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str], *, timeout: int = 3600) -> subprocess.CompletedProcess:
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False,
    )
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg failed ({proc.returncode})\ncmd: {' '.join(cmd)}\n{proc.stderr}")
    return proc


def probe(path: Path) -> dict:
    """Duration, fps, width, height, has_audio. Uses ffmpeg itself (no ffprobe shipped)."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-i", str(path)]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    info = proc.stderr
    import re

    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", info)
    if not m:
        raise FFmpegError(f"cannot probe {path}:\n{info}")
    h, mi, s = m.groups()
    duration = int(h) * 3600 + int(mi) * 60 + float(s)
    v = re.search(r"Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?) fps", info)
    width, height, fps = (int(v.group(1)), int(v.group(2)), float(v.group(3))) if v else (0, 0, 0)
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": "Audio:" in info,
    }


def extract_frame(video: Path, t: float, out: Path, width: int = 640) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "3", str(out)])
    return out


def extract_audio(video: Path, out: Path, sample_rate: int = 16000) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["-i", str(video), "-vn", "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(out)])
    return out


def cut_clip(video: Path, start: float, end: float, out: Path, width: int = 1280, fps: int = 25) -> Path:
    """Re-encode a clip so concat is safe regardless of source keyframes."""
    out.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(video),
            "-vf", f"scale={width}:-2,fps={fps},setsar=1",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            "-af", "aresample=async=1:first_pts=0",
            str(out),
        ]
    )
    return out


def image_clip(image: Path, seconds: float, out: Path, width: int = 1280, height: int = 720, fps: int = 25) -> Path:
    """A still image as a video clip with silent audio, letterboxed to the output size."""
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},setsar=1,format=yuv420p"
    )
    run(
        [
            "-loop", "1", "-framerate", str(fps), "-i", str(image),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", f"{seconds:.3f}", "-vf", vf, "-shortest",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ar", "48000",
            str(out),
        ]
    )
    return out


def concat(clips: list[Path], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in clips), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    return out


def audio_duration(path: Path) -> float:
    return probe(path)["duration"]


def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
