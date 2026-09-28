"""Stage 3: turn ranked candidates into a timeline.

Heuristic assembly (cinematographic pacing rules from styles.py), no model call:
- each unit gets clips from its top candidates in score order
- a shot is not reused across units unless a unit would otherwise be empty
- clip lengths follow the style's min/max and the unit's estimated narration time
- clips inside a unit are ordered by their time in the film
- when the candidates cannot cover the narration, the unit continues with the
  shots that follow its last clip in the film, so the picture keeps moving
The result stores per-unit clip proportions; render fits them to the real narration.
"""

from __future__ import annotations

from mococo import styles
from mococo.project import Project


IMAGE_SECONDS = 3.5


def estimated_seconds(text: str, lang: str, style: dict) -> float:
    cpm = style["chars_per_minute"][lang]
    return max(2.0, 60.0 * len(text) / cpm)


def narration_seconds(project: Project, unit_id: str, lang: str) -> float | None:
    """Real narration duration if the voice stage already ran for this language."""
    p = project.narration_timing(lang)
    if not p.exists():
        return None
    for u in project.read_json(p)["units"]:
        if u["id"] == unit_id:
            return u["end"] - u["start"]
    return None


def plan_unit(unit, cands, shots, used, style, need: float, order: list[str] | None = None, skip: set[str] | None = None) -> list[dict]:
    """order: all shot ids in film order; skip: shots never to use (title cards)."""
    lo, hi = style["min_clip"], style["max_clip"]
    clips: list[dict] = []
    total = 0.0
    fresh = [c for c in cands if c["shot_id"] not in used] or cands  # fall back to reuse
    for c in fresh:
        if total >= need:
            break
        sh = shots[c["shot_id"]]
        avail = sh["duration"]
        take = min(avail, hi, max(lo, need - total))
        if take < lo and avail >= lo:
            take = lo
        if take < min(lo, avail):
            continue
        # take from the start of the shot; a human can slide it in the UI
        clips.append(
            {
                "shot_id": c["shot_id"],
                "in": round(sh["start"], 3),
                "out": round(sh["start"] + take, 3),
                "seconds": round(take, 3),
                "why": c.get("why", ""),
            }
        )
        used.add(c["shot_id"])
        total += take
    clips.sort(key=lambda c: c["in"])
    # continuation: the shots right after the last clip, until the narration is covered
    if order and clips and total < need:
        i = order.index(clips[-1]["shot_id"]) + 1
        while total < need - 0.05 and i < len(order):
            sid = order[i]
            i += 1
            if sid in used or (skip and sid in skip):
                continue
            sh = shots[sid]
            take = min(sh["duration"], hi, need - total)
            if take < 0.4:
                continue
            clips.append({"shot_id": sid, "in": round(sh["start"], 3), "out": round(sh["start"] + take, 3), "seconds": round(take, 3), "why": "continues the previous shot"})
            used.add(sid)
            total += take
    return clips


def run(project: Project, *, force: bool = False):
    if project.timeline_json.exists() and not force:
        return project.timeline_json
    s = project.load()
    st = styles.get(s.style)
    seg = project.read_json(project.segments_json)
    cands = {c["unit_id"]: c for c in project.read_json(project.candidates_json)["units"]}
    shots = {sh["id"]: sh for sh in project.read_json(project.shots_json)}
    order = [sh["id"] for sh in sorted(shots.values(), key=lambda x: x["start"])]
    caps = project.read_json(project.captions_json) if project.captions_json.exists() else {}
    from mococo.stages.retrieve import is_text_card

    skip = {sid for sid, cap in caps.items() if is_text_card(cap)}
    lang = seg["primary_lang"]
    used: set[str] = set()
    units = []
    for unit in seg["units"]:
        need = narration_seconds(project, unit["id"], lang) or estimated_seconds(unit["text"][lang], lang, st)
        c = cands.get(unit["id"], {"shots": []})
        ordered = c["shots"]
        chosen = c.get("chosen") or []
        if chosen:  # a human pick goes first
            ordered = [x for x in ordered if x["shot_id"] in chosen] + [x for x in ordered if x["shot_id"] not in chosen]
        clips = plan_unit(unit, ordered, shots, used, st, need, order=order, skip=skip)
        if not clips:
            raise RuntimeError(f"no usable clips for unit {unit['id']}; rerun retrieve with a larger --top")
        # DG3: a unit that needed outside knowledge opens on its reference image
        for ref in c.get("external", [])[:1]:
            clips.insert(0, {"kind": "image", "file": ref["file"], "caption": ref.get("caption", ""), "seconds": IMAGE_SECONDS, "why": "external reference"})
        units.append({"id": unit["id"], "estimated_seconds": round(need, 2), "clips": clips})
    project.write_json(project.timeline_json, {"style": s.style, "units": units})
    project.log_event("stage_done", stage="cut", units=len(units), clips=sum(len(u["clips"]) for u in units))
    return project.timeline_json
