"""Stage 2: candidate shots per unit (embedding recall + model rerank) and external references."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from mococo import knowledge, prompts
from mococo.project import Project
from mococo.provider import embed, llm
from mococo.stages import images

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
    previous = project.read_json(project.candidates_json) if project.candidates_json.exists() else {"units": []}
    approved_images = {u["unit_id"]: [r for r in u.get("external", []) if r.get("approved")] for u in previous["units"]}
    s = project.load()
    seg = project.read_json(project.segments_json)
    shots = {sh["id"]: sh for sh in project.read_json(project.shots_json)}
    caps = project.read_json(project.captions_json)
    data = np.load(project.index_npz)
    ids, vecs = data["ids"], data["vecs"]
    keep = np.array([not is_text_card(caps[str(i)]) for i in ids])
    ids, vecs = ids[keep], vecs[keep]
    recall = recall or max(top * 3, 12)
    rerank_mode = os.getenv("MOCOCO_RERANK_MODE", "llm").strip().lower()
    if rerank_mode not in {"llm", "embedding"}:
        raise ValueError("MOCOCO_RERANK_MODE must be llm or embedding")

    def one(unit):
        query = f'{unit["visual_query_en"]} Mood: {unit["mood"]}. Keywords: {", ".join(unit["keywords"])}.'
        pool = _recall(query, ids, vecs, recall)
        if rerank_mode == "embedding":
            ranked = [
                {
                    "id": sid, "score": round(100 * max(0, sim), 1),
                    "why": "Visual similarity to the commentary unit",
                    "why_zh": "画面与解说段落的语义相近",
                }
                for sid, sim in pool
            ]
        else:
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
            ranked = [r for r in result["ranked"] if r["id"] in dict(pool)]
        sim_by_id = dict(pool)
        ranked.sort(key=lambda r: -r["score"])
        return {
            "unit_id": unit["id"],
            "shots": [
                {"shot_id": r["id"], "score": r["score"], "why": r["why"], "why_zh": r.get("why_zh", ""), "similarity": round(sim_by_id[r["id"]], 4)}
                for r in ranked[:top]
            ],
            "external": approved_images.get(unit["id"], []),
            "chosen": [r["id"] for r in ranked[:1]],
        }

    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(one, seg["units"]))

    if s.style == "analysis" or any(u["needs_context"] for u in seg["units"]):
        by_id = {r["unit_id"]: r for r in results}
        for unit in seg["units"]:
            if unit["needs_context"] and unit["context_query"]:
                matches = knowledge.search(project, unit["context_query"])
                by_id[unit["id"]]["knowledge"] = matches
                by_id[unit["id"]]["knowledge_status"] = "retrieved" if matches else "missing"
                project.log_event("knowledge_unit_retrieved", unit=unit["id"], count=len(matches))
                try:
                    images.search(project, unit["id"], unit["context_query"])
                except (RuntimeError, ValueError) as exc:
                    by_id[unit["id"]]["image_search_error"] = str(exc)
                    project.log_event("image_search_failed", unit=unit["id"], error=str(exc))

    project.write_json(project.candidates_json, {"units": results})
    project.log_event("stage_done", stage="retrieve", units=len(results))
    return project.candidates_json
