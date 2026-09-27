# 2026-09-28 overnight build: where things stand

Written by Claude for Zhaoyang to read on waking. Status, not decisions.

## Done (PR #1, branch feat/engine-skeleton)
- Full pipeline runs on Sintel: `uv run mococo run projects/sintel` produced
  projects/sintel/render/output.zh.mp4 and output.en.mp4 (about 3 minutes each,
  bilingual burned-in subtitles, TTS narration, original audio ducked).
  31 model calls, about $1.9 of API-equivalent usage on the subscription.
- Web app at http://127.0.0.1:8765 after `uv run mococo serve`: six-step wizard,
  zh/en UI toggle, edits every stage file, runs stages as background jobs.
- Title cards and credits are flagged at caption time and never retrieved.
- Charade (1963, public domain) ingest started as the feature-length demo.

## Observed quality
- Retrieval picks chronologically sensible, mood-matched shots; the reranker's
  "why" text reads well in the UI.
- The Chinese draft is fluent; it called the dragon "斯通/Stone" (the film's
  transcript never names it; Blender calls it Scales). A creator would fix this
  in the Script step, which is exactly the co-creation moment the proposal wants.
- Subtitle line breaking now follows clauses; the second language is split into
  the same number of pieces by proportion, so pairs stay roughly aligned.

## Not done / next
- Charade end-to-end run and a look at quality on a real film.
- Analysis style has not been exercised (external-reference retrieval via web
  search is untested end to end).
- Upload-narration alignment is implemented but untested with a real recording.
- macOS / Windows smoke test (ffmpeg libass availability, paths).
- Tag v0.1 after PR #1 merges.
