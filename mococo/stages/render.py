"""Stage 4b: clips + narration + subtitles -> output.<lang>.mp4.

For each language the unit's clips are stretched or trimmed proportionally so the
unit's video lasts exactly as long as its narration (plus the gap). Original film
audio is kept under the narration at low volume.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mococo.media import ffmpeg
from mococo.project import Project

DUCK = 0.12  # original audio volume under narration
FONT_SIZE = 22


def run(project: Project, *, lang: str | None = None, force: bool = False, workers: int = 6) -> list[Path]:
    s = project.load()
    out = []
    langs = [l for l in s.voice_langs if not lang or l == lang]
    for l in langs:
        out.append(render_lang(project, l, force=force, workers=workers))
    return out


def fit_clips(clips: list[dict], target: float, shots: dict, film_end: float | None = None) -> list[dict]:
    """Scale clip lengths to sum to target, never exceeding the shot's real length.
    Any shortfall lets the last clip run on into the film (the picture keeps
    moving); only at the end of the film is a frame frozen."""
    total = sum(c["seconds"] for c in clips) or 1.0
    fitted = []
    for c in clips:
        want = c["seconds"] * target / total
        if c.get("kind") == "image":
            fitted.append({**c, "seconds": round(want, 3)})
            continue
        sh = shots[c["shot_id"]]
        room = sh["end"] - c["in"]
        take = min(want, room)
        fitted.append({**c, "out": round(c["in"] + take, 3), "seconds": round(take, 3)})
    short = target - sum(c["seconds"] for c in fitted)
    # give the shortfall to clips that still have room, last clip first
    for c in reversed(fitted):
        if short <= 0.05:
            break
        if c.get("kind") == "image":
            c["seconds"] = round(c["seconds"] + short, 3)
            short = 0.0
            break
        room = shots[c["shot_id"]]["end"] - c["out"]
        ext = min(room, short)
        if ext > 0:
            c["out"] = round(c["out"] + ext, 3)
            c["seconds"] = round(c["seconds"] + ext, 3)
            short -= ext
    if short > 0.05 and film_end is not None:
        for c in reversed(fitted):
            if c.get("kind") == "image":
                continue
            ext = min(short, film_end - c["out"])
            if ext > 0:
                c["out"] = round(c["out"] + ext, 3)
                c["seconds"] = round(c["seconds"] + ext, 3)
                c["why"] = (c.get("why", "") + " (runs on into the next shots)").strip()
                short -= ext
            break
    if short > 0.05:  # at the very end of the film: freeze the final frame
        fitted[-1]["freeze"] = round(short, 3)
    return fitted


def render_lang(project: Project, lang: str, *, force: bool = False, workers: int = 6) -> Path:
    s = project.load()
    output = project.output_mp4(lang)
    if output.exists() and not force:
        return output
    film = Path(s.film)
    timeline = project.read_json(project.timeline_json)
    timing = {u["id"]: u for u in project.read_json(project.narration_timing(lang))["units"]}
    shots = {sh["id"]: sh for sh in project.read_json(project.shots_json)}
    seg = {u["id"]: u for u in project.read_json(project.segments_json)["units"]}

    work = project.render_dir / f"clips.{lang}"
    work.mkdir(parents=True, exist_ok=True)
    info = ffmpeg.probe(film)
    out_w = 1280
    out_h = max(2, round(info["height"] * out_w / max(1, info["width"]) / 2) * 2)  # match cut_clip's scale=1280:-2
    jobs, plan = [], []
    ends = [t["end"] for t in timing.values()]
    for i, unit in enumerate(timeline["units"]):
        t = timing[unit["id"]]
        nxt = timeline["units"][i + 1]["id"] if i + 1 < len(timeline["units"]) else None
        span = (timing[nxt]["start"] if nxt else t["end"]) - t["start"]
        fitted = fit_clips(unit["clips"], span, shots, film_end=info["duration"])
        for k, c in enumerate(fitted):
            path = work / f'{unit["id"]}_{k:02d}.mp4'
            jobs.append((c, path))
            plan.append(path)
    if force:
        for _, p in jobs:
            p.unlink(missing_ok=True)

    def one(job):
        c, path = job
        if path.exists():
            return
        if c.get("kind") == "image":
            ffmpeg.image_clip(project.retrieval_dir / c["file"], c["seconds"], path, width=out_w, height=out_h)
            return
        ffmpeg.cut_clip(film, c["in"], c["out"], path)
        if c.get("freeze"):
            frozen = path.with_name(path.stem + "_f.mp4")
            ffmpeg.run(["-i", str(path), "-vf", f"tpad=stop_mode=clone:stop_duration={c['freeze']}", "-af", f"apad=pad_dur={c['freeze']}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", str(frozen)])
            frozen.replace(path)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, jobs))

    video = work / "video.mp4"
    ffmpeg.concat(plan, video)

    srt = write_srt(project, lang) if lang in s.subtitle_langs else None
    if s.subtitle_langs and lang not in s.subtitle_langs:
        srt = write_srt(project, s.subtitle_langs[0])  # subtitle another language over this narration
    second = [l for l in s.subtitle_langs if l != lang]
    if lang in s.subtitle_langs and second:
        srt = write_srt(project, lang, second=second[0])

    args = ["-i", str(video), "-i", str(project.narration_audio(lang))]
    filt = f"[0:a]volume={DUCK}[bg];[bg][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]"
    vf = _subtitles_filter(srt) if srt else None
    args += ["-filter_complex", filt + (f";[0:v]{vf}[v]" if vf else ""), "-map", "[v]" if vf else "0:v", "-map", "[a]"]
    # write beside the final name and rename at the end, so a half-written file
    # never looks like a finished render
    partial = output.with_name(output.stem + ".partial.mp4")
    args += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(partial)]
    ffmpeg.run(args)
    partial.replace(output)
    project.log_event("stage_done", stage="render", lang=lang, seconds=round(max(ends), 1))
    return output


def _subtitles_filter(srt: Path) -> str:
    # ffmpeg's filter parser needs ':' and '\' escaped inside the path
    p = srt.resolve().as_posix().replace("\\", "/").replace(":", "\\:")
    style = f"FontSize={FONT_SIZE},Outline=1,Shadow=0,MarginV=28"
    return f"subtitles='{p}':force_style='{style}'"


def _fmt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_lines(text: str, lang: str, max_chars: int) -> list[str]:
    """Break unit text into subtitle-sized pieces: split into clauses at
    punctuation, pack clauses into lines, hard-cut only clauses far over the limit."""
    import re

    text = re.sub(r"\s+", " ", text).strip()
    clauses = [c for c in re.split(r"(?<=[。！？；，、,;:：.!?])\s*|(?<=——)", text) if c and c.strip()]
    clauses = [c.strip() for c in clauses if c.strip()]
    lines, buf = [], ""
    joiner = "" if lang == "zh" else " "
    for c in clauses:
        cand = (buf + joiner + c).strip() if buf else c
        if len(cand) <= max_chars:
            buf = cand
            continue
        if buf:
            lines.append(buf)
        buf = c
        while len(buf) > max_chars * 1.3:
            if lang == "zh":
                cut = max_chars
            else:
                cut = buf.rfind(" ", 0, max_chars)
                cut = cut if cut > max_chars * 0.4 else max_chars
            lines.append(buf[:cut].strip())
            buf = buf[cut:].strip()
    if buf:
        lines.append(buf)
    return lines


def split_into_n(text: str, n: int, lang: str) -> list[str]:
    """Cut text into exactly n pieces of roughly equal length, at spaces for
    non-Chinese text. Used to pair a second subtitle language with the first."""
    import re

    text = re.sub(r"\s+", " ", text).strip()
    if n <= 1:
        return [text]
    if lang == "zh":
        step = len(text) / n
        return [text[round(i * step) : round((i + 1) * step)].strip() for i in range(n)]
    words = text.split()
    step = len(words) / n
    return [" ".join(words[round(i * step) : round((i + 1) * step)]) for i in range(n)]


def _piece_times(pieces: list[str], t: dict) -> list[tuple[float, float]]:
    """Time each piece from word boundaries when present, else proportionally."""
    words = t.get("words") or []
    span = t["end"] - t["start"]
    if not words:
        total = sum(len(p) for p in pieces) or 1
        out, cursor = [], t["start"]
        for p in pieces:
            d = span * len(p) / total
            out.append((cursor, min(cursor + d, t["end"])))
            cursor += d
        return out
    # cumulative character count of the spoken words, punctuation excluded
    def clean(s: str) -> str:
        return "".join(ch for ch in s if ch.isalnum())
    ends, acc = [], 0
    for w in words:
        acc += len(clean(w["word"]))
        ends.append((acc, w["end"]))
    out, start, consumed = [], t["start"], 0
    for p in pieces:
        consumed += len(clean(p))
        end = next((we for c, we in ends if c >= consumed), words[-1]["end"])
        end = min(max(end, start + 0.3), t["end"])
        out.append((start, end))
        start = end
    return out


def write_srt(project: Project, lang: str, second: str | None = None) -> Path:
    """One subtitle entry per piece; timing from narration word boundaries."""
    seg = {u["id"]: u for u in project.read_json(project.segments_json)["units"]}
    timing = project.read_json(project.narration_timing(lang))["units"]
    max_chars = 18 if lang == "zh" else 42
    entries, n = [], 1
    for t in timing:
        text = seg[t["id"]]["text"][lang]
        pieces = split_lines(text, lang, max_chars)
        second_pieces = split_into_n(seg[t["id"]]["text"][second], len(pieces), second) if second else []
        for i, (p, (a, b)) in enumerate(zip(pieces, _piece_times(pieces, t))):
            line = p + ("\n" + second_pieces[i] if second_pieces else "")
            entries.append(f"{n}\n{_fmt(a)} --> {_fmt(b)}\n{line}\n")
            n += 1
    out = project.subtitles_srt(lang if not second else f"{lang}+{second}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(entries), encoding="utf-8")
    return out
