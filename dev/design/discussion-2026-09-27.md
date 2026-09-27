# Discussion 2026-09-27: from proposal to a thing

Status: open. Nothing locked yet.

## Context
Proposal (dev/materials/BaixueWu_Research_Proposal.pdf) describes Movie-Explain-RAG,
a 4-stage human-AI pipeline for movie commentary videos. Zhaoyang wants to vibe code
it into something real; form (product vs research prototype vs demo) undecided.

## Claude's assessment
- The novel and hard core is stages 2-3: script -> retrieve matching shots -> coherent
  rough cut. Stage 1 (segment + tag) is one LLM prompt; stage 4 (subtitles, TTS,
  music) is commodity. Engine = "script-to-rough-cut"; everything else is shell.
- Three candidate targets: (1) research prototype serving E1/E2, (2) creator tool /
  product, (3) one-click full-auto demo (conflicts with DG4).
- Recommendation: build (1), shaped like (2). Local CLI engine first; each stage is a
  standalone command whose output is a human-editable file (segmented script .md,
  candidate shots .json, timeline .json); ffmpeg renders. Editing the files IS the
  human-in-the-loop; UI (thin review/replace-shot layer) comes after the engine works.
- Borrow everything: PySceneDetect, VLM shot captions, embeddings for retrieval,
  LLM for segmentation/ordering, ffmpeg for assembly.
- First milestone: one film + one 5-min script -> one rough cut, eyeball whether
  shots match. No evaluation or product talk before that.

## Open questions for Zhaoyang
- First user: Baixue (paper, E1/E2 output formats) or Zhaoyang (hobby)?
- Does Baixue write code?
- Do we have a film file and a script now?
- Language of scripts / audience (zh vs en)?

## Answers from Zhaoyang (same day)
- Wants (1) research prototype + (2) usable tool, GUI eventually; Baixue continues
  after handoff; everyone vibe-codes with AI. No film or script exists. Bilingual
  zh/en, user-selectable. -> promoted to design-decisions.md.

## Still open
1. Baixue's venue / deadline.
2. Which API keys and budget (no GPU on this machine; env check was blocked).
3. Repo ownership: Zhaoyang's GitHub + Baixue as collaborator, or hers?
4. Voiceover from v1? (Claude leans yes.) TTS vendor preference?
5. External-knowledge RAG (DG3) in v1 or later? (Claude leans later; film-only first.)
6. GUI as local web app (Claude's default unless objected).
7. Chinese-language public-domain film: verify copyright status of 1930s-40s
   Shanghai films before using one.

## Round 2 answers -> promoted to design-decisions.md (2 weeks, Claude-only, voice
## yes, all 4 stages in v1, local web app).

## Still open
- Git email: resolved, baixuewu0@gmail.com.
- gh access: resolved via PAT file.
- Chinese-language PD film for a later version (verify copyright first).
- OS: all three supported.
