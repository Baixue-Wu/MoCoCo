# MoCoCo (Movie Commentary Co-creation)

Human-AI co-creation of movie commentary videos. A creator brings (or asks for)
a commentary script; the system finds matching shots in the film, assembles a
rough cut, adds narration and subtitles, and lets the creator revise at every
stage. Grows out of Baixue Wu's research proposal (dev/materials/), which
describes the concept system "Movie-Explain-RAG" and its four design guidelines
(semantic/affective alignment, narrative temporal structure, knowledge-augmented
commentary, human-AI iterative co-creation). Both a research prototype for a
later paper (E1 alignment study, E2 user study) and a demoable tool.

Read `dev/design/architecture.md` before touching code and
`dev/design/design-decisions.md` before re-opening any settled question.

## Layout

```
mococo/            the package (Python 3.12, uv, `uv sync` then `uv run mococo --help`)
  cli.py           only file that exits; every command maps to a stage
  project.py       project.json schema and the on-disk layout of a project
  knowledge.py     source import, BM25 retrieval, cited suggestions and approval
  examples/sintel/  short source notes and license provenance for the analysis study
  styles.py        everything about the two commentary styles (recap | analysis)
  prompts/*.md     one template per model task, $var substitution
  provider/llm.py  the ONLY place that knows we use Claude (`claude -p` headless)
  provider/embed.py  bge-m3 sentence embeddings on CPU
  media/           ffmpeg (imageio-ffmpeg binary), shot detection, whisper, edge-tts
  stages/          ingest, script, retrieve, cut, voice, render: files in, files out
  server/          FastAPI app; the web UI in web/ is a thin client of it
web/               React + Vite front end
scripts/           fetch_film.py and other helpers
projects/          user projects (gitignored); one folder per project
data/              downloaded films and test scraps (gitignored)
dev/materials/     the proposal PDF
dev/design/        architecture, design decisions, dated discussions, open questions
```

## Working here

- Run a project end to end: `uv run mococo init projects/x --film <file>` then
  `uv run mococo run projects/x`, or one stage at a time (`ingest`, `script draft`,
  `script segment`, `retrieve`, `cut`, `voice`, `render`). Every stage is
  resumable and re-runnable with `--force`.
- Edit the stage output file by hand and rerun the next stage: that is the
  command-line form of co-creation. The web app edits the same files.
- Models: Claude only, through the developer's Claude Code login. `fast` tier is
  Haiku (bulk labelling), `smart` tier is Sonnet (judgement). Costs are logged to
  each project's events.jsonl. Nothing else in the code may name a model.
- No environment variables for configuration; no shell=True; pathlib everywhere;
  library code raises, cli.py exits.
- Media never enters git. Films come from public-domain or CC sources only
  (Sintel from Blender, Charade 1963 from archive.org) because demos are shown
  to outsiders.
- Commits in this repo are authored as Baixue Wu <baixuewu0@gmail.com>. No
  Claude co-author trailers. Branch, PR, merge, even for solo work.
- Design decisions go to dev/design/design-decisions.md the turn they are made;
  unsettled threads to dev/design/discussion-YYYY-MM-DD.md; things only Zhaoyang
  or Baixue can answer to dev/design/questions.md.

## Tags

`v<x.y>` for milestones, `release/<name>` for versions shown outside,
`submit/<venue>` when a paper goes out.

## Knowledge-grounded analysis

Read dev/design/knowledge-rag.md for the working text-RAG and image-insertion flow, sources and test commands.
Use the existing provider module for synthesis; provider selection has evolved beyond
the initial Claude-only design (see README). Do not assume WebSearch/WebFetch exists.
Public examples are read-only project workflows sharing ExampleWorkflow.tsx; live source import and synthesis require the local
API. Never describe keyword filtering on the public page as live RAG generation.

External images use provider/images.py and stages/images.py. Search is automatic
for contextual units, but insertion requires explicit creator approval. Keep author,
source, license and change notices through timeline editing and render credits.
