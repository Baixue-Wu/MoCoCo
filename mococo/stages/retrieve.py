"""Stage 2: candidate shots per unit (embedding recall + model rerank) and external references."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np

from mococo import prompts
from mococo.project import Project
from mococo.provider import embed, llm

RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranked": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "score": {"type": "number"}, "why": {"type": "string"}, "why_zh": {"type": "string"}},
                "required": ["id", "score", "why", "why_zh"],
            },
        }
    },
    "required": ["ranked"],
}

EXTERNAL_SCHEMA = {
    "type": "object",
    "properties": {
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string"},
                    "source_url": {"type": "string"},
                    "caption": {"type": "string"},
                },
                "required": ["image_url", "source_url", "caption"],
            },
        }
    },
    "required": ["references"],
}


def is_text_card(cap: dict) -> bool:
    """Title cards, credits, logos, blank frames: never footage."""
    if "text_card" in cap:
        return bool(cap["text_card"])
    blob = (cap.get("description_en", "") + " " + " ".join(cap.get("tags", []))).lower()
    return any(k in blob for k in ("title card", "credits", "opening title", "logo", "black screen", "intertitle"))


def _recall(query: str, ids: np.ndarray, vecs: np.ndarray, k: int) -> list[tuple[str, float]]:
    q = embed.embed([query])[0]
    sims = vecs @ q
    order = np.argsort(-sims)[:k]
    return [(str(ids[i]), float(sims[i])) for i in order]


def run(project: Project, *, top: int = 6, recall: int | None = None, workers: int = 4, force: bool = False):
    if project.candidates_json.exists() and not force:
        return project.candidates_json
    s = project.load()
    seg = project.read_json(project.segments_json)
    shots = {sh["id"]: sh for sh in project.read_json(project.shots_json)}
    caps = project.read_json(project.captions_json)
    data = np.load(project.index_npz)
    ids, vecs = data["ids"], data["vecs"]
    keep = np.array([not is_text_card(caps[str(i)]) for i in ids])
    ids, vecs = ids[keep], vecs[keep]
    recall = recall or max(top * 3, 12)

    def one(unit):
        query = f'{unit["visual_query_en"]} Mood: {unit["mood"]}. Keywords: {", ".join(unit["keywords"])}.'
        pool = _recall(query, ids, vecs, recall)
        lines = []
        for sid, sim in pool:
            sh, c = shots[sid], caps[sid]
            lines.append(
                f'- id={sid} time={sh["start"]:.1f}-{sh["end"]:.1f}s ({sh["duration"]:.1f}s) '
                f'desc="{c["description_en"]}" mood="{c["mood"]}" dialogue="{c.get("dialogue", "")[:160]}"'
            )
        prompt = prompts.render(
            "retrieve_rerank",
            title=s.title,
            text=unit["text"][seg["primary_lang"]],
            mood=unit["mood"],
            visual_query=unit["visual_query_en"],
            candidates="\n".join(lines),
        )
        result = llm.ask(prompt, tier="smart", schema=RERANK_SCHEMA, log=project.log_event)
        sim_by_id = dict(pool)
        ranked = [r for r in result["ranked"] if r["id"] in sim_by_id]
        ranked.sort(key=lambda r: -r["score"])
        return {
            "unit_id": unit["id"],
            "shots": [
                {"shot_id": r["id"], "score": r["score"], "why": r["why"], "why_zh": r.get("why_zh", ""), "similarity": round(sim_by_id[r["id"]], 4)}
                for r in ranked[:top]
            ],
            "external": [],
            "chosen": [r["id"] for r in ranked[:1]],
        }

    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(one, seg["units"]))

    if s.style == "analysis" or any(u["needs_context"] for u in seg["units"]):
        by_id = {r["unit_id"]: r for r in results}
        for unit in seg["units"]:
            if unit["needs_context"] and unit["context_query"]:
                by_id[unit["id"]]["external"] = external(project, unit)

    project.write_json(project.candidates_json, {"units": results})
    project.log_event("stage_done", stage="retrieve", units=len(results))
    return project.candidates_json


def external(project: Project, unit: dict, max_refs: int = 2) -> list[dict]:
    """Best effort: web search for reference images. Never raises; returns [] on failure."""
    import httpx

    s = project.load()
    prompt = (
        f'Find up to {max_refs} publicly viewable reference images for this claim in a commentary about the film "{s.title}":\n'
        f'"{unit["text"][project.load().primary_lang]}"\n'
        f"Search query to start from: {unit['context_query']}\n"
        "Use WebSearch to find pages, then WebFetch to confirm a direct image URL on them. Prefer Wikipedia / "
        "Wikimedia Commons or official sources. For each, give the direct image URL (ending in .jpg/.png), "
        "the page it came from, and a one-sentence caption in English. Return an empty list if nothing solid is found."
    )
    try:
        result = llm.ask(prompt, tier="fast", schema=EXTERNAL_SCHEMA, tools=["WebSearch", "WebFetch"], log=project.log_event, timeout=300)
    except llm.LLMError as e:
        project.log_event("external_failed", unit=unit["id"], error=str(e)[:500])
        return []
    refs = []
    project.external_dir.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(result.get("references", [])[:max_refs]):
        path = project.external_dir / f'{unit["id"]}_{i + 1}.jpg'
        try:
            resp = httpx.get(r["image_url"], follow_redirects=True, timeout=30, headers={"User-Agent": "MoCoCo/0.1"})
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                path.write_bytes(resp.content)
                refs.append({**r, "file": f"external/{path.name}"})
        except Exception as e:  # noqa: BLE001
            project.log_event("external_download_failed", unit=unit["id"], url=r["image_url"], error=str(e)[:300])
    return refs
