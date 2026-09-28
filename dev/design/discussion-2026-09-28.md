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
- Charade (1963, public domain, 113 min) runs end to end: 1188 shots, 1674
  transcript lines, 8 narration units, 3.6-minute zh and en videos. 160 model
  calls, about $7.7 API-equivalent (captions dominate: 149 Haiku calls).
  The Chinese recap is plot-accurate; shots land on the right scenes.
- Analysis style verified on projects/sintel-analysis: a unit flagged
  needs_context fetched a Wikimedia reference image via Claude's web search and
  it appears as a 3.5 s letterboxed still at the start of that unit (DG3).

## Observed quality
- Retrieval picks chronologically sensible, mood-matched shots; the reranker's
  "why" text reads well in the UI.
- The Chinese draft is fluent; it called the dragon "斯通/Stone" (the film's
  transcript never names it; Blender calls it Scales). A creator would fix this
  in the Script step, which is exactly the co-creation moment the proposal wants.
- Subtitle line breaking now follows clauses; the second language is split into
  the same number of pieces by proportion, so pairs stay roughly aligned.

## Not done / next
- Drafts undershoot target length (Charade asked 6 min, got 3.6). Raise the
  target_chars emphasis in the draft prompt or iterate once on length.
- Caption cost scales with shot count; for long films consider captioning only
  every shot longer than 1.5 s, or a cheaper contact-sheet batch.
- Upload-narration alignment is implemented but untested with a real recording.
- macOS / Windows smoke test (ffmpeg libass availability, paths).
- Tag v0.1 after PR #1 merges.

## Street Angel (1937) trial, same day
- 601 shots, 844 transcript lines (whisper large-v3, recognised as zh),
  11 narration units, 3.2 min zh and 3.9 min en, no frozen frames.
  90 model calls, about $4.3 API-equivalent.
- Shots land on the right beats (the trumpeter, Boss Gu, Xiao Yun's death).
- The draft got two plot facts wrong: 老王 is the newspaper seller, not the
  huqin player (that is Xiao Hong's adoptive father), and Xiao Yun is stabbed
  by the adoptive father, not beaten by Gu's men. The draft only sees dialogue
  and captions, so off-screen causality is guessed. This is the case for a
  "fact check against the transcript" pass, or for making the Script step the
  place where the creator corrects the story.
- Bilingual subtitles take three lines when the English half wraps. Consider a
  smaller English font or a per-language line length.
