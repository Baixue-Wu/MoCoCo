"""Shot boundary detection with PySceneDetect."""

from __future__ import annotations

from pathlib import Path

from scenedetect import AdaptiveDetector, detect


def detect_shots(video: Path, min_len_s: float = 0.8, adaptive_threshold: float = 3.0) -> list[tuple[float, float]]:
    """Return [(start_s, end_s), ...] covering the film in order."""
    scenes = detect(str(video), AdaptiveDetector(adaptive_threshold=adaptive_threshold, min_scene_len=15), show_progress=False)
    out: list[tuple[float, float]] = []
    for a, b in scenes:
        s, e = a.get_seconds(), b.get_seconds()
        if out and (e - s) < min_len_s:
            ps, _ = out[-1]
            out[-1] = (ps, e)  # merge tiny shots into the previous one
        else:
            out.append((s, e))
    return out
