# MoCoCo architecture

Locked 2026-09-27 for v1. Change here first, code second.

## Shape

One Python package `mococo` (3.12, uv) exposing the same operations three ways:
a CLI (`mococo <stage> ...`), a local HTTP API (FastAPI), and a web UI (React)
that only talks to the API. The engine never knows the UI exists.

Every stage is a function `stage(project_dir, **params) -> output file(s)`:
files in, files out, resumable, re-runnable. A stage's output is the human-
editable artifact for that stage; editing the file by hand and re-running the
next stage IS co-creation at the CLI level. The UI is a nicer editor for the
same files.

## A project on disk

```
projects/<slug>/
  project.json            settings: film, title, style, languages, voice, brief
  ingest/
    shots.json            shot boundaries + keyframe paths
    frames/<shot_id>.jpg  one keyframe per shot (plus optional mid/end frames)
    transcript.json       whisper segments with language
    captions.json         per-shot: description, mood, characters, setting, tags
    index.npz             embeddings for shots (captions + transcript window)
  script/
    brief.md              user's one-paragraph brief (when AI-drafted)
    script.<lang>.md      commentary script, one paragraph per unit
    segments.json         units: text per lang, intent, mood, anchors, concepts
  retrieval/
    candidates.json       per unit: ranked shots (score, why) + external refs
    external/<id>.jpg     downloaded reference images (DG3)
  cut/
    timeline.json         ordered clips: unit_id, shot_id, in, out, duration
  voice/
    narration.<lang>.mp3  TTS or aligned upload
    timing.<lang>.json    per-unit start/end of narration
  render/
    subtitles.<lang>.srt
    output.<lang>.mp4
  events.jsonl            interaction traces (every accept/reject/edit/rerun)
```

`project.json` is the only place settings live. Language axes: `script_langs`,
`subtitle_langs`, `voice_langs` each a subset of {zh, en}; `ui_lang` lives in the
browser. Style: `recap | analysis`.

## Stages (proposal stage -> code)

| proposal | command            | reads                        | writes                       |
|----------|--------------------|------------------------------|------------------------------|
| pre      | `mococo ingest`    | film                         | ingest/*                     |
| 1        | `mococo script draft`   | brief, transcript, captions | script/script.<lang>.md |
| 1        | `mococo script segment` | script.<lang>.md            | script/segments.json     |
| 2        | `mococo retrieve`  | segments, index, captions    | retrieval/candidates.json    |
| 3        | `mococo cut`       | candidates, shots, segments  | cut/timeline.json            |
| 4        | `mococo voice`     | segments (+ upload)          | voice/*                      |
| 4        | `mococo render`    | timeline, voice, subtitles   | render/output.<lang>.mp4     |
| all      | `mococo run`       | everything in order          |                              |

## Single homes for the axes that change

- **Model provider**: `mococo/provider/llm.py`. One function `ask(...)` taking
  prompt, optional image paths, tier (`fast` | `smart`), and a JSON flag. v1
  backend shells to `claude -p` (fast=haiku, smart=sonnet). Nothing else in the
  codebase knows what Claude is.
- **Media tools**: `mococo/media/ffmpeg.py` (binary discovery, probe, cut,
  concat, mux), `mococo/media/shots.py` (PySceneDetect), `mococo/media/stt.py`
  (faster-whisper), `mococo/media/tts.py` (edge-tts).
- **Embeddings**: `mococo/provider/embed.py` (sentence-transformers, multilingual).
- **Prompts**: `mococo/prompts/*.md`, one file per LLM task, bilingual by
  parameter, never inline in code.
- **Style knowledge** (pacing, shot counts, tone per style): `mococo/styles.py`.

## Rules

- No environment variables for configuration. Paths and settings come from
  `project.json` or CLI flags.
- Library code raises; only `cli.py` exits.
- Subprocess errors surface verbatim with the command that failed.
- Media files never enter git; `scripts/fetch_film.py` downloads them.
- Every LLM call logs prompt name, tier, tokens and cost to `events.jsonl`.
- Cross-platform: pathlib everywhere, ffmpeg from `static-ffmpeg`/`imageio-ffmpeg`,
  no shell=True.

## Web UI (v1)

Wizard with one screen per stage: Setup -> Script -> Shots -> Cut -> Voice ->
Export. Each screen shows the stage's file, lets the user edit it (text, accept /
swap / reorder / trim), and offers "run this stage" / "run to end". The API is
`POST /projects/{slug}/stages/{name}` plus file reads/writes; the UI is a thin
client so a desktop shell can wrap it later.

## Knowledge retrieval addition (2026-10-08)

`mococo/knowledge.py` owns source records, deterministic chunks with character
locations, lexical retrieval, and cited synthesis. Project paths remain in
`project.py`: `knowledge/sources.json` and `knowledge/answers.json`. Both CLI and
HTTP endpoints use this module. Sources are supplied explicitly as text with
URL, author, kind and rights metadata; arbitrary URL fetching is not hidden in
model calls. Empty retrieval returns an explicit gap without invoking a model.
Model suggestions cite retrieved chunk IDs; creator acceptance is a separate
operation. Only accepted, current-source suggestions enter script drafting.
Public static pages demonstrate saved evidence and browser filtering, while
live synthesis requires the local API. `provider/images.py` owns Commons metadata and restricted downloads;
`stages/images.py` owns per-unit searches, approval, timeline insertion/revocation
and attribution artifacts. Render validates approved records and adds credit cards.
This does not implement the full proposal coverage-gap model.
