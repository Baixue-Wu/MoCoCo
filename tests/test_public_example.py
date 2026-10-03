"""The published example must contain every frame referenced by its decisions."""

import json
from pathlib import Path


def test_public_example_decisions_have_media_and_no_private_paths():
    root = Path(__file__).resolve().parents[1] / "web" / "public" / "examples" / "sherlock-jr"
    data = json.loads((root / "project.json").read_text(encoding="utf-8"))

    assert len(data["segments"]["units"]) == len(data["candidates"]["units"])
    assert len(data["segments"]["units"]) == len(data["timeline"]["units"])
    assert len(data["script"].split("\n\n")) == len(data["segments"]["units"])

    frame_ids = {shot["id"] for shot in data["shots"]}
    referenced = {
        shot["shot_id"]
        for unit in data["candidates"]["units"]
        for shot in unit["shots"]
    } | {
        clip["shot_id"]
        for unit in data["timeline"]["units"]
        for clip in unit["clips"]
        if "shot_id" in clip
    }
    assert referenced == frame_ids
    assert all((root / "frames" / f"{shot_id}.jpg").is_file() for shot_id in frame_ids)
    assert (root / "narration.zh.mp3").is_file()

    text = (root / "project.json").read_text(encoding="utf-8")
    assert "D:\\" not in text and "C:\\" not in text
    assert "火星特快" not in text
