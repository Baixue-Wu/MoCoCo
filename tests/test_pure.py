"""Tests for the parts that need no model, no network, no film."""

from itertools import pairwise

from mococo import styles
from mococo.stages.cut import plan_unit
from mococo.stages.ingest import representative_shots
from mococo.stages.render import _piece_times, fit_clips, split_lines
from mococo.stages.script import _sample_lines, paragraphs


def test_paragraphs_split_on_blank_lines():
    assert paragraphs("a\n\nb\r\n\r\n\n c \n") == ["a", "b", "c"]


def test_long_transcript_keeps_beginning_and_end():
    lines = [f"[{i * 60}s] " + "dialogue " * 10 for i in range(100)]
    sample = _sample_lines(lines, 1000)
    assert lines[0] in sample
    assert lines[-1] in sample
    assert "sampled across the full film" in sample


def test_split_lines_zh_breaks_at_punctuation():
    text = "这是第一句话，然后是第二句话。最后一句很长很长很长很长很长很长很长很长很长很长。"
    pieces = split_lines(text, "zh", 18)
    assert all(len(p) <= 18 for p in pieces)
    assert "".join(pieces) == text


def test_split_lines_en_keeps_words():
    text = "One two three four five six seven eight nine ten eleven twelve, thirteen fourteen."
    pieces = split_lines(text, "en", 30)
    assert " ".join(pieces).split() == text.split()


def test_fit_clips_scales_to_target():
    shots = {"a": {"start": 0, "end": 10}, "b": {"start": 20, "end": 22}}
    clips = [{"shot_id": "a", "in": 0, "out": 4, "seconds": 4}, {"shot_id": "b", "in": 20, "out": 22, "seconds": 2}]
    fitted = fit_clips(clips, 12.0, shots)
    assert abs(sum(c["seconds"] for c in fitted) - 12.0) < 0.06
    assert fitted[1]["out"] <= 22  # never past the real shot


def test_fit_clips_freezes_when_no_room():
    shots = {"a": {"start": 0, "end": 2}}
    fitted = fit_clips([{"shot_id": "a", "in": 0, "out": 2, "seconds": 2}], 5.0, shots)
    assert fitted[0]["freeze"] == 3.0


def test_piece_times_use_word_boundaries():
    t = {"start": 10.0, "end": 14.0, "words": [{"start": 10.0, "end": 11.0, "word": "hello"}, {"start": 11.2, "end": 13.5, "word": "world"}]}
    times = _piece_times(["hello", "world"], t)
    assert times[0] == (10.0, 11.0)
    assert times[1][1] == 13.5


def test_plan_unit_avoids_reuse_and_respects_min_clip():
    st = styles.get("recap")
    shots = {"s1": {"start": 0, "end": 10, "duration": 10}, "s2": {"start": 10, "end": 13, "duration": 3}}
    cands = [{"shot_id": "s1", "score": 90}, {"shot_id": "s2", "score": 80}]
    used = {"s1"}
    clips = plan_unit({}, cands, shots, used, st, need=3.0)
    assert [c["shot_id"] for c in clips] == ["s2"]
    assert clips[0]["seconds"] >= st["min_clip"]


def test_representative_shots_cover_the_full_film():
    shots = [{"id": str(i), "start": float(i), "end": float(i + 1)} for i in range(100)]
    selected = representative_shots(shots, max_count=10)
    assert len(selected) == 10
    assert selected[0]["id"] == "0"
    assert selected[-1]["id"] == "99"
    assert all(b["start"] - a["start"] <= 12 for a, b in pairwise(selected))


def test_representative_shots_preserve_finished_captions():
    shots = [{"id": str(i), "start": float(i), "end": float(i + 1)} for i in range(100)]
    finished = {str(i) for i in range(20)}
    selected = representative_shots(shots, max_count=25, already_captioned=finished)
    assert len(selected) == 25
    assert finished.issubset({shot["id"] for shot in selected})
    assert selected[-1]["id"] == "99"
