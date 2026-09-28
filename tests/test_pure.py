"""Tests for the parts that need no model, no network, no film."""

from mococo.stages.cut import plan_unit
from mococo.stages.render import _piece_times, fit_clips, split_lines
from mococo.stages.script import paragraphs
from mococo import styles


def test_paragraphs_split_on_blank_lines():
    assert paragraphs("a\n\nb\r\n\r\n\n c \n") == ["a", "b", "c"]


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


def test_fit_clips_runs_on_into_film_instead_of_freezing():
    shots = {"a": {"start": 0, "end": 2}}
    fitted = fit_clips([{"shot_id": "a", "in": 0, "out": 2, "seconds": 2}], 5.0, shots, film_end=100.0)
    assert fitted[0]["out"] == 5.0 and "freeze" not in fitted[0]


def test_fit_clips_freezes_only_at_film_end():
    shots = {"a": {"start": 0, "end": 2}}
    fitted = fit_clips([{"shot_id": "a", "in": 0, "out": 2, "seconds": 2}], 5.0, shots, film_end=2.0)
    assert fitted[0]["freeze"] == 3.0


def test_plan_unit_continues_with_following_shots():
    st = styles.get("recap")
    shots = {f"s{i}": {"start": i * 2.0, "end": i * 2.0 + 2.0, "duration": 2.0} for i in range(6)}
    cands = [{"shot_id": "s1", "score": 90}]
    clips = plan_unit({}, cands, shots, set(), st, need=7.0, order=[f"s{i}" for i in range(6)], skip={"s3"})
    assert [c["shot_id"] for c in clips] == ["s1", "s2", "s4", "s5"]
    assert abs(sum(c["seconds"] for c in clips) - 7.0) < 0.05


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
