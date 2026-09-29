"""Stage 1: commentary script. Draft (optional), check, translate, segment."""

from __future__ import annotations

import hashlib
from pathlib import Path

from mococo import prompts, styles
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


CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim": {"type": "string"},
                                "verdict": {"type": "string", "enum": ["supported", "contradicted", "unsupported"]},
                                "evidence": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "t": {"type": "number"},
                                            "kind": {"type": "string", "enum": ["says", "sees", "brief"]},
                                            "text": {"type": "string"},
                                        },
                                        "required": ["t", "kind", "text"],
                                    },
                                },
                                "note": {"type": "string"},
                            },
                            "required": ["claim", "verdict", "evidence", "note"],
                        },
                    },
                    "revised": {"type": "string"},
                },
                "required": ["index", "claims", "revised"],
            },
        }
    },
    "required": ["paragraphs"],
}


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]


def evidence_timeline(project: Project, max_chars: int = 400_000) -> str:
    """Every transcript line and every shot caption, merged in time order.
    Captions are shortened to their first sentence if the whole would not fit."""
    t = project.read_json(project.transcript_json)
    shots = project.read_json(project.shots_json)
    caps = project.read_json(project.captions_json)

    def build(short: bool) -> str:
        rows = [(s["start"], 1, f'[{s["start"]:.0f}s] says: {s["text"].strip()}') for s in t["segments"]]
        for sh in shots:
            c = caps.get(sh["id"])
            if not c or c.get("text_card"):
                continue
            desc = c["description_en"].split(". ")[0] if short else c["description_en"]
            who = ", ".join(c.get("characters", []))
            rows.append((sh["start"], 0, f'[{sh["start"]:.0f}s] sees: {desc}' + (f" | people: {who}" if who else "")))
        return "\n".join(r[2] for r in sorted(rows))

    text = build(short=False)
    if len(text) > max_chars:
        text = build(short=True)
    if len(text) > max_chars:
        raise RuntimeError(
            f"evidence timeline is {len(text)} characters, over the {max_chars} limit; "
            "this film is too long to check in one pass"
        )
    return text


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def check(project: Project, *, fix: bool = False) -> Path:
    """Fact-check the primary script against the whole film; write script/check.json.

    Contradicted claims get a minimal correction; unsupported ones are only
    flagged, since thin evidence (noisy transcript, one frame per shot) misses
    much that is true. With fix, corrected paragraphs replace the originals and
    are re-translated in the other script languages. Without fix nothing but
    check.json is written."""
    s = project.load()
    lang = s.primary_lang
    path = project.script_md(lang)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; write it or run `mococo script draft`")
    paras = paragraphs(path.read_text(encoding="utf-8"))
    prompt = prompts.render(
        "script_check",
        title=s.title,
        lang_name=LANG_NAMES[lang],
        timeline=evidence_timeline(project),
        brief=s.brief or "(none)",
        script="\n\n".join(f"[{i}] {p}" for i, p in enumerate(paras)),
    )
    result = llm.ask(prompt, tier="smart", schema=CHECK_SCHEMA, log=project.log_event, timeout=900)
    by_index = {p["index"]: p for p in result["paragraphs"]}
    missing = [i for i in range(len(paras)) if i not in by_index]
    if missing:
        raise RuntimeError(f"fact-check skipped paragraphs {missing}; re-run `mococo script check`")

    report = []
    changed = []
    for i, text in enumerate(paras):
        r = by_index[i]
        revised = " ".join(r["revised"].split("\n")).strip() or text
        wrong = any(c["verdict"] == "contradicted" for c in r["claims"])
        if wrong and revised != text:
            changed.append(i)
        report.append({"index": i, "text": text, "claims": r["claims"], "revised": revised if wrong else text})

    applied = False
    if fix and changed:
        new = [report[i]["revised"] if i in changed else p for i, p in enumerate(paras)]
        path.write_text("\n\n".join(new) + "\n", encoding="utf-8")
        for other in s.script_langs[1:]:
            if project.script_md(other).exists():
                retranslate(project, other, changed)
        applied = True

    counts = {v: sum(1 for p in report for c in p["claims"] if c["verdict"] == v) for v in ("supported", "contradicted", "unsupported")}
    checked_text = "\n\n".join(paras)
    project.write_json(
        project.check_json,
        {
            "lang": lang,
            "checked_sha": _sha(checked_text),
            "script_sha": _sha(path.read_text(encoding="utf-8").strip()),
            "applied": applied,
            "changed": changed,
            "counts": counts,
            "paragraphs": report,
        },
    )
    project.log_event("stage_done", stage="script.check", applied=applied, changed=changed, **counts)
    return project.check_json


def retranslate(project: Project, dst: str, indices: list[int]) -> Path:
    """Re-translate only the given paragraphs of the primary script into dst."""
    s = project.load()
    src_paras = paragraphs(project.script_md(s.primary_lang).read_text(encoding="utf-8"))
    target = project.script_md(dst)
    dst_paras = paragraphs(target.read_text(encoding="utf-8"))
    if len(dst_paras) != len(src_paras):
        return translate(project, dst, force=True)
    prompt = prompts.render(
        "script_translate",
        src_name=LANG_NAMES[s.primary_lang],
        dst_name=LANG_NAMES[dst],
        title=s.title,
        script="\n\n".join(src_paras[i] for i in indices),
    )
    new = paragraphs(llm.ask(prompt, tier="smart", log=project.log_event))
    if len(new) != len(indices):
        return translate(project, dst, force=True)
    for i, text in zip(indices, new):
        dst_paras[i] = text
    target.write_text("\n\n".join(dst_paras) + "\n", encoding="utf-8")
    project.log_event("stage_done", stage="script.retranslate", lang=dst, paragraphs=indices)
    return target


def draft(project: Project, *, lang: str | None = None, force: bool = False) -> list[Path]:
    """Write script.<primary>.md from the brief, then translate to the other languages."""
    s = project.load()
    st = styles.get(s.style)
    primary = s.primary_lang
    out: list[Path] = []

    target = project.script_md(primary)
    if force or not target.exists():
        chars = int(s.target_minutes * st["chars_per_minute"][primary])
        prompt = prompts.render(
            "script_draft",
            lang_name=LANG_NAMES[primary],
            style_label=st["label"]["en"],
            style_guidance=st["guidance"],
            title=s.title,
            target_minutes=s.target_minutes,
            target_chars=chars,
            brief=s.brief or "(none given)",
            timeline=evidence_timeline(project),
        )
        text = llm.ask(prompt, tier="smart", log=project.log_event)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n\n".join(paragraphs(text)) + "\n", encoding="utf-8")
        if s.brief:
            project.brief_md.write_text(s.brief + "\n", encoding="utf-8")
        project.log_event("stage_done", stage="script.draft", lang=primary, paragraphs=len(paragraphs(text)))
        # the model corrects its own draft; a human's text is only ever checked on request
        check(project, fix=True)
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
