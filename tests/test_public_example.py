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


def test_analysis_workflow_matches_finished_script_and_rendered_media():
    root = Path(__file__).resolve().parents[1] / 'web/public/examples/sintel-analysis'
    text = (root / 'study.json').read_text()
    data = json.loads(text)
    workflow = data['workflow']
    units = workflow['segments']['units']
    assert '\n\n'.join(u['text']['zh'] for u in units).strip() == data['movie']['script'].strip()
    ids = [u['id'] for u in units]
    assert ids == [u['id'] for u in workflow['timeline']] == [u['id'] for u in workflow['timing']['units']]
    assert len(ids) == len(data['movie']['chapters'])
    sources = {s['id'] for s in workflow['sources']}
    assert all(set(e['source_ids']) <= sources for e in workflow['evidence'])
    cursor = 0
    for unit in workflow['timeline']:
        for clip in unit['clips']:
            assert clip['render_start'] == cursor
            assert clip['render_end'] > cursor
            cursor = clip['render_end']
            file = clip['file'] if clip.get('kind') == 'image' else f"frames/{clip['shot_id']}.jpg"
            assert (root / file).is_file()
            if clip.get('kind') == 'image':
                assert clip['attribution']['artist'] and clip['attribution']['license_url']
    assert cursor == workflow['content_end'] < data['movie']['duration']
    assert (root / 'subtitles.zh.srt').read_text() == workflow['subtitles']
    assert workflow['narration_url'].startswith('https://github.com/Baixue-Wu/')
    assert '/nvme-disk/' not in text and '/home/' not in text
