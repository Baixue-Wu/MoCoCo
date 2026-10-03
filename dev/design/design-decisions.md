# MoCoCo design decisions

Finalized decisions only, one rationale each. Open threads live in discussion-*.md.

## 2026-10-03 (public showcase)

- **Use the original React app as the public website, with a browser-local
  upload preview and a built-in *Sherlock Jr.* case study.** Rationale: the
  user wants a continuously reachable version of the actual product UI and
  chose browser-local movie storage while public AI processing is deferred.
  The GitHub Pages build has no shared user files or backend credentials;
  `npm run build` still serves the full local Python workflow.

- **The first static showcase was replaced by a public build of the product UI.**
  GitHub Pages can host the same React screens and browser-local film imports;
  rendering still requires a Python server and per-user access controls before
  it can serve visitors online.
- **Use *Sherlock Jr.* (1924) for the public example and keep unlicensed films
  out of GitHub.** Rationale: the film is in the US public domain, appears in
  IMDb's Top 250, and has a Wikimedia Commons copy. The original copy has no
  audio; a silent audio track is added locally for pipeline compatibility.

## 2026-09-27

- **Target is research prototype AND usable demo tool, with a GUI eventually.**
  Rationale: the engine must run E1/E2 for Baixue's paper, and Baixue must be able
  to show it to outsiders; neither alone is enough.
- **Zhaoyang vibe-codes the skeleton, then hands off to Baixue; both work with AI.**
  Rationale: handoff-ability is a hard requirement, so every unit is self-contained
  with --help, and CLAUDE.md + design-decisions.md are the memory across people.
- **Engine first, GUI later. Engine = "script-to-rough-cut" CLI; each stage emits a
  human-editable file.** Rationale: stages 2-3 are the novel core; editing files is
  the first form of human-in-the-loop and needs no UI.
- **Films come from public-domain / CC sources; commentary scripts are LLM-written
  from a Whisper transcript.** Rationale: no source material exists, and a demo
  meant for outsiders cannot rest on pirated footage.
- **Language is per-axis, not global: script, subtitles, voiceover, UI each take
  zh | en | both.** Rationale: users choose; "both" means bilingual subtitles and
  two voice tracks.
- **Compute is API-based, not local.** Rationale: the dev machine has no GPU
  (checked 2026-09-27); ffmpeg to be installed as a static binary.
- **Two-week target is a demoable product; the paper follows later.** Rationale:
  Zhaoyang's priority order; E1/E2 hooks stay in the design but are not v1 work.
- **Models: Claude only, via the Claude Code subscription in headless mode
  (`claude -p`), Haiku for bulk labeling, Sonnet for judgment calls.** Rationale: no
  API keys, no GPU. Provider lives in one swappable module so an API-key backend
  can replace it later. Consequence: v1 runs on Baixue's own machine with her own
  login; it is not distributable to strangers.
- **Speech-to-text: local CPU faster-whisper. Voiceover: edge-tts. Embeddings:
  local CPU multilingual model.** Rationale: keyless, bilingual, good enough.
- **All four stages including external-knowledge retrieval (DG3) exist in v1, rough
  first, refined by iteration.** Rationale: Zhaoyang's call; external knowledge via
  Claude's built-in web search.
- **GUI is a local web app, not a desktop app.** Rationale: timeline UI is easiest in
  the browser, one codebase, remote demo works; Tauri wrap later if wanted.
- **Dev film: Blender's Sintel (CC-BY, 15 min). Demo feature: a US public-domain
  film, Charade (1963) by default.** Rationale: legal to show outsiders.
- **Commits in this repo are authored as Baixue Wu (project-level exception to the
  Zhaoyang-only-author rule).** Rationale: repo lives under her GitHub account.
- **Distribution to outsiders is explicitly out of scope for now.** Rationale:
  Zhaoyang: Claude subscription is for building and testing; adapting for external
  users happens later. Keep the provider module swappable, stop worrying beyond that.
- **Web first, but built as a thin client over a clean local HTTP API.** Rationale:
  a desktop (Tauri/Electron) or mobile shell can later consume the same API without
  touching the engine.
- **Cross-platform: macOS, Linux, Windows all supported.** Rationale: Baixue's and
  demo machines vary; no OS-specific paths, ffmpeg fetched per-platform.
- **Git author in this repo: Baixue Wu <baixuewu0@gmail.com>.** Rationale: matches
  her GitHub account; local config typo fixed 2026-09-27.
- **AI-drafted commentary script is a product feature, not just a dev trick.**
  Rationale: demo audiences bring no script; user gives a brief, AI drafts from the
  film's transcript and frames, user edits.
- **Two commentary styles, chosen per project: "recap" (plot rundown, fast, many
  shots) and "analysis" (motifs, foreshadowing, director intent, slower, uses
  external knowledge).** Rationale: covers both proposal genres; style is a parameter
  feeding pacing heuristics and script drafting tone.
- **v1 editing depth: per-segment review, swap/re-retrieve shots, trim, reorder. No
  frame-level timeline scrubbing editor.** Rationale: two-week budget; a full NLE
  would starve the other stages.
- **Voiceover: TTS (edge-tts) plus optional upload of the creator's own narration,
  aligned to script segments with whisper.** Rationale: Zhaoyang wants real voice
  supported from v1; costs 2-3 days.
- **GitHub access: fine-grained PAT stored at ~/.config/gh/mococo-token (600),
  injected per call as GH_TOKEN inside this repo only.** Rationale: Zhaoyang's own gh
  login stays untouched; token to be revoked after handoff.

## 2026-09-28 (overnight build)

- **Multi-language scripts: draft in the primary language, translate paragraph by
  paragraph into the others; segments carry text per language.** Rationale: units
  must line up one to one across languages so subtitles, timing, and shot choices
  are shared. Paragraph-count mismatch is a loud error with a fix command.
- **Narration drives timing: voice runs before cut when possible; render fits each
  unit's clips to that language's actual narration span.** Rationale: the cut
  cannot know durations until speech exists; different languages differ in length,
  so the timeline stores proportions and render scales them.
- **Cut assembly is a heuristic (styles.py pacing rules), not a model call.**
  Rationale: deterministic, free, and the proposal itself calls for
  "cinematographic pacing heuristics"; a model planner can be added later.
- **Machine-level settings (model cache dir) live in ~/.config/mococo/config.json,
  not env vars.** Rationale: the dev box's root disk is full; the rule against env
  vars stands, and a config file is discoverable.
- **Subtitles are timed from edge-tts word boundaries; uploaded narration is
  aligned with whisper word timestamps + difflib.** Rationale: keyless and precise
  enough for v1.
- **Web UI is delegated to a React + Vite + TS app under web/, thin client of the
  FastAPI routes in mococo/server/app.py; jobs run in server threads and are
  polled.** Rationale: no websockets needed for a single local user.
