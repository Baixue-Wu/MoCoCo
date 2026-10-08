"""Stage 1: commentary script. Draft (optional), translate, segment."""

from __future__ import annotations

from pathlib import Path

from mococo import knowledge, prompts, styles
from mococo.project import LANG_NAMES, Project
from mococo.provider import llm

SEGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "units": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "intent": {"type": "string"},
                    "mood": {"type": "string"},
                    "visual_query_en": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "needs_context": {"type": "boolean"},
                    "context_query": {"type": "string"},
                },
                "required": ["id", "text", "intent", "mood", "visual_query_en", "keywords", "needs_context", "context_query"],
            },
        }
    },
    "required": ["units"],
}


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]


def _sample_lines(lines: list[str], max_chars: int) -> str:
    """Fit a long transcript while retaining dialogue from beginning to end."""
    whole = "\n".join(lines)
    if len(whole) <= max_chars:
        return whole
    if len(lines) < 2:
        return whole[:max_chars]
    low, high, best = 2, len(lines), ""
    while low <= high:
        count = (low + high) // 2
        indexes = sorted({round(i * (len(lines) - 1) / (count - 1)) for i in range(count)})
        sample = "\n".join(lines[i] for i in indexes)
        if len(sample) <= max_chars:
            best = sample
            low = count + 1
        else:
            high = count - 1
    return best + "\n[... transcript sampled across the full film ...]"


def _transcript_text(project: Project, max_chars: int = 60000) -> str:
    t = project.read_json(project.transcript_json)
    lines = [f'[{s["start"]:.0f}s] {s["text"]}' for s in t["segments"]]
    return _sample_lines(lines, max_chars)


def _shot_summaries(project: Project, max_lines: int = 150) -> str:
    shots = project.read_json(project.shots_json)
    caps = project.read_json(project.captions_json)
    captioned = [shot for shot in shots if shot["id"] in caps]
    step = max(1, len(captioned) // max_lines)
    lines = []
    for sh in captioned[::step]:
        c = caps.get(sh["id"])
        if c:
            lines.append(f'[{sh["start"]:.0f}s] {c["description_en"]} ({c["mood"]})')
    return "\n".join(lines)


def draft(project: Project, *, lang: str | None = None, force: bool = False) -> list[Path]:
    """Write script.<primary>.md from the brief, then translate to the other languages."""
    s = project.load()
    st = styles.get(s.style)
    primary = s.primary_lang
    out: list[Path] = []

    target = project.script_md(primary)
    if force or not target.exists():
        chars = int(s.target_minutes * st["chars_per_minute"][primary])
        evidence = knowledge.accepted_context(project)
        prompt = prompts.render(
            "script_draft",
            knowledge=evidence,
            lang_name=LANG_NAMES[primary],
            style_label=st["label"]["en"],
            style_guidance=st["guidance"],
            title=s.title,
            target_minutes=s.target_minutes,
            target_chars=chars,
            brief=s.brief or "(none given)",
            transcript=_transcript_text(project),
            shot_summaries=_shot_summaries(project),
        )
        text = llm.ask(prompt, tier="smart", log=project.log_event)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n\n".join(paragraphs(text)) + "\n", encoding="utf-8")
        project.write_json(project.script_evidence_json, {"source_revision": knowledge.fingerprint(project), "context": evidence})
        if s.brief:
            project.brief_md.write_text(s.brief + "\n", encoding="utf-8")
        project.log_event("stage_done", stage="script.draft", lang=primary, paragraphs=len(paragraphs(text)))
    out.append(target)

    for other in s.script_langs[1:]:
        if lang and other != lang:
            continue
        out.append(translate(project, other, force=force))
    return out


def translate(project: Project, dst: str, *, force: bool = False) -> Path:
    """Translate the primary script into dst, paragraph for paragraph."""
    s = project.load()
    src = s.primary_lang
    target = project.script_md(dst)
    if target.exists() and not force:
        return target
    source_text = project.script_md(src).read_text(encoding="utf-8")
    src_paras = paragraphs(source_text)
    for attempt in range(3):
        prompt = prompts.render(
            "script_translate",
            src_name=LANG_NAMES[src],
            dst_name=LANG_NAMES[dst],
            title=s.title,
            script="\n\n".join(src_paras),
        )
        text = llm.ask(prompt, tier="smart", log=project.log_event)
        dst_paras = paragraphs(text)
        if len(dst_paras) == len(src_paras):
            break
    else:
        raise RuntimeError(
            f"translation to {dst} produced {len(dst_paras)} paragraphs, source has {len(src_paras)}; "
            f"edit {target} by hand or re-run `mococo script draft --force`"
        )
    target.write_text("\n\n".join(dst_paras) + "\n", encoding="utf-8")
    project.log_event("stage_done", stage="script.translate", lang=dst, paragraphs=len(dst_paras))
    return target


def segment(project: Project, *, force: bool = False) -> Path:
    """segments.json: units with text per language plus retrieval hints."""
    s = project.load()
    if project.segments_json.exists() and not force:
        return project.segments_json
    primary = s.primary_lang
    if not project.script_md(primary).exists():
        raise FileNotFoundError(
            f"{project.script_md(primary)} missing; write it or run `mococo script draft`"
        )
    texts = {l: paragraphs(project.script_md(l).read_text(encoding="utf-8")) for l in s.script_langs if project.script_md(l).exists()}
    n = len(texts[primary])
    for l, ps in texts.items():
        if len(ps) != n:
            raise RuntimeError(
                f"script.{l}.md has {len(ps)} paragraphs but script.{primary}.md has {n}; "
                f"they must match one to one. Fix by hand or run `mococo script translate {l} --force`"
            )
    prompt = prompts.render(
        "script_segment", title=s.title, lang_name=LANG_NAMES[primary], script="\n\n".join(texts[primary])
    )
    result = llm.ask(prompt, tier="smart", schema=SEGMENT_SCHEMA, log=project.log_event)
    units = result["units"]
    if len(units) != n:
        raise RuntimeError(f"segmenter returned {len(units)} units for {n} paragraphs; re-run")
    for i, u in enumerate(units):
        u["id"] = f"u{i + 1:03d}"
        u["text"] = {l: texts[l][i] for l in texts}
    project.write_json(project.segments_json, {"primary_lang": primary, "units": units})
    project.log_event("stage_done", stage="script.segment", units=n)
    return project.segments_json
