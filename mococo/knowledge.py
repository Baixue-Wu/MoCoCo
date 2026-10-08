"""Project-scoped source retrieval and cited commentary suggestions."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from mococo import prompts
from mococo.project import Project
from mococo.provider import llm


class Source(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=2000)
    author: str = Field(min_length=1, max_length=300)
    kind: Literal['review', 'production', 'creator_note'] = 'review'
    rights: str = Field(min_length=1, max_length=1000)
    text: str = Field(min_length=20, max_length=100000)

    @field_validator('url')
    @classmethod
    def public_link(cls, value):
        parsed = urlparse(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username:
            raise ValueError('Source URL must be an http(s) link without credentials')
        return value


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def sources(project: Project) -> list[dict]:
    return project.read_json(project.sources_json) if project.sources_json.exists() else []


def answers(project: Project) -> list[dict]:
    return project.read_json(project.knowledge_answers_json) if project.knowledge_answers_json.exists() else []


def fingerprint(project: Project) -> str:
    return _hash(sources(project))


def add_source(project: Project, source: Source) -> dict:
    project.load()
    record = source.model_dump()
    record['id'] = 's-' + _hash(record)[:16]
    existing = sources(project)
    if any(s['id'] == record['id'] for s in existing):
        return next(s for s in existing if s['id'] == record['id'])
    if len(existing) >= 100:
        raise ValueError('Source limit reached; remove an unused source before importing more')
    record['added_at'] = datetime.now(timezone.utc).isoformat()
    project.write_json(project.sources_json, existing + [record])
    project.log_event('knowledge_source_added', source_id=record['id'], url=record['url'])
    return record


def remove_source(project: Project, source_id: str) -> None:
    existing = sources(project)
    if not any(s['id'] == source_id for s in existing):
        raise ValueError('Source not found; refresh the source list')
    project.write_json(project.sources_json, [s for s in existing if s['id'] != source_id])
    project.log_event('knowledge_source_removed', source_id=source_id)


def chunks(records: list[dict], size: int = 700, overlap: int = 100) -> list[dict]:
    if size <= overlap or overlap < 0:
        raise ValueError('Chunk size must exceed nonnegative overlap')
    result = []
    for source in records:
        text = source['text']
        for start in range(0, len(text), size - overlap):
            end = min(start + size, len(text))
            result.append({**{k: source[k] for k in ('id', 'title', 'url', 'author', 'kind', 'rights')},
                           'source_id': source['id'], 'id': f"{source['id']}:{start}:{end}",
                           'start': start, 'end': end, 'text': text[start:end]})
            if end == len(text):
                break
    return result


def _terms(text: str) -> list[str]:
    words = re.findall(r'[a-z0-9]+', text.lower())
    for phrase in re.findall(r'[\u3400-\u9fff]+', text):
        words.extend(phrase[i:i+2] for i in range(len(phrase)-1))
        if len(phrase) == 1:
            words.append(phrase)
    return words


def search(project: Project, query: str, limit: int = 5) -> list[dict]:
    """BM25 lexical retrieval, supporting English tokens and Chinese bigrams."""
    if not query.strip() or len(query) > 4000 or not 1 <= limit <= 10:
        raise ValueError('Use a question of 1-4000 characters and a result limit of 1-10')
    passages = chunks(sources(project))
    if not passages:
        return []
    docs = [Counter(_terms(p['text'])) for p in passages]
    lengths = [sum(doc.values()) for doc in docs]
    average = sum(lengths) / len(docs) or 1
    terms = set(_terms(query))
    frequency = {t: sum(t in doc for doc in docs) for t in terms}
    ranked = []
    for passage, doc, length in zip(passages, docs, lengths):
        score = 0.0
        for term in terms:
            f = doc[term]
            if f:
                idf = math.log(1 + (len(docs) - frequency[term] + .5) / (frequency[term] + .5))
                score += idf * f * 2.2 / (f + 1.2 * (.25 + .75 * length / average))
        if score > 0:
            ranked.append({**passage, 'score': round(score, 6)})
    return sorted(ranked, key=lambda p: (-p['score'], p['id']))[:limit]


ANSWER_SCHEMA = {'type': 'object', 'properties': {
    'claims': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'text': {'type': 'string'},
        'kind': {'type': 'string', 'enum': ['source_fact', 'interpretation']},
        'citations': {'type': 'array', 'items': {'type': 'string'}},
        'visual_query': {'type': 'string'},
    }, 'required': ['text', 'kind', 'citations', 'visual_query']}},
    'gaps': {'type': 'array', 'items': {'type': 'string'}},
}, 'required': ['claims', 'gaps']}


def suggest(project: Project, query: str, limit: int = 5) -> dict:
    retrieved = search(project, query, limit)
    revision = fingerprint(project)
    if retrieved:
        prompt = prompts.render('knowledge_answer', title=project.load().title,
                                question=query, evidence=json.dumps(retrieved, ensure_ascii=False))
        output = llm.ask(prompt, tier='smart', schema=ANSWER_SCHEMA, log=project.log_event)
        allowed = {c['id'] for c in retrieved}
        claims = output.get('claims')
        if not isinstance(claims, list) or not isinstance(output.get('gaps'), list):
            raise ValueError('Model returned an invalid evidence response; retry the question')
        for claim in claims:
            if (not isinstance(claim, dict) or not isinstance(claim.get('text'), str)
                    or not claim['text'].strip() or claim.get('kind') not in ('source_fact', 'interpretation')
                    or not isinstance(claim.get('visual_query'), str)
                    or not isinstance(claim.get('citations'), list) or not claim['citations']
                    or any(not isinstance(c, str) or c not in allowed for c in claim['citations'])):
                raise ValueError('Model used missing or unretrieved citations; nothing was accepted. Retry the question')
    else:
        output = {'claims': [], 'gaps': ['No matching source passage. Import relevant material or rephrase the query in the source language.']}
    result = {'id': 'a-' + _hash([query, revision, output])[:16], 'query': query,
              'source_revision': revision, 'retrieved': retrieved, 'claims': output['claims'],
              'gaps': output['gaps'], 'accepted': False,
              'created_at': datetime.now(timezone.utc).isoformat(), 'retrieval_method': 'bm25'}
    previous = [a for a in answers(project) if a['id'] != result['id']]
    project.write_json(project.knowledge_answers_json, previous + [result])
    project.log_event('knowledge_suggested', answer_id=result['id'], sources=len(retrieved))
    return result


def review(project: Project, answer_id: str, accepted: bool) -> dict:
    records = answers(project)
    record = next((a for a in records if a['id'] == answer_id), None)
    if record is None:
        raise ValueError('Suggestion not found; refresh the suggestions')
    if accepted and (not record['claims'] or record['source_revision'] != fingerprint(project)):
        raise ValueError('Missing evidence or changed sources; retrieve a new suggestion before accepting')
    record['accepted'] = accepted
    project.write_json(project.knowledge_answers_json, records)
    project.log_event('knowledge_reviewed', answer_id=answer_id, accepted=accepted)
    return record


def accepted_context(project: Project) -> str:
    records = [a for a in answers(project) if a['accepted']]
    if any(a['source_revision'] != fingerprint(project) for a in records):
        raise ValueError('Sources changed after approval. Review knowledge suggestions before drafting')
    return json.dumps(records, ensure_ascii=False) if records else '(No approved external evidence; do not invent production facts or director intent.)'
