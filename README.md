# MoCoCo · Movie Commentary Co-creation

**Public web app:** [Open MoCoCo](https://Baixue-Wu.github.io/MoCoCo/). The original six-stage project interface includes a read-only *Sherlock Jr.* (1924) project. Open it to inspect the actual script units, candidate and selected frames, final clip order, narration timing, and exported video. Visitors can also import their own movie into a browser-local project. On this public version, the file stays in that browser's IndexedDB storage; AI processing and exporting are not yet connected to a public backend. The complete production workflow remains available in the Python-served app below. The example's original film is available from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Sherlock_Jr.(1924).webm).

Co-create a movie commentary video with an AI partner: bring a script (or ask
for a draft), let the system find matching shots and assemble a rough cut, then
revise the script, the shot choices, the timeline, and the narration until it
is yours. Bilingual (中文 / English) narration and subtitles.

## Quick start

```
uv sync                                      # Python 3.12 environment
uv run python scripts/fetch_film.py sintel   # a CC-BY short film to try on
uv run mococo init projects/sintel --film data/films/Sintel.2010.720p.mkv \
    --title Sintel --langs zh,en --minutes 3 --brief "A recap of Sintel."
uv run mococo run projects/sintel            # every stage, end to end
open projects/sintel/render/output.zh.mp4
```

Or one stage at a time, editing the stage's output file in between:

```
uv run mococo ingest projects/sintel          # shots, keyframes, transcript, captions, index
uv run mococo script draft projects/sintel    # or write projects/sintel/script/script.zh.md yourself
uv run mococo script segment projects/sintel
uv run mococo retrieve projects/sintel        # candidates per unit -> retrieval/candidates.json
uv run mococo cut projects/sintel             # timeline -> cut/timeline.json
uv run mococo voice projects/sintel           # TTS, or drop voice/upload.<lang>.wav first
uv run mococo render projects/sintel
```

Web app: `uv run mococo serve` then open http://127.0.0.1:8765 (build the UI
once with `cd web && npm install && npm run build`). In **New project**, each
visitor selects a movie from their own computer. The browser uploads it into
that project's `source/` folder; the visitor does not need access to a server
file path.

To rebuild the continuously hosted public version, run `npm run build:public`
inside `web/` and publish the resulting `docs/` folder through GitHub Pages.
This version uses the same React interface, with browser-local projects and a
read-only example. The local Python server build remains `npm run build`.

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- [Codex CLI](https://developers.openai.com/codex/cli/) installed and logged in
  for the default language and vision model backend, or Ollama for local inference.
- Network access for edge-tts voices and the first-time model downloads
  (whisper, bge-m3, about 3 GB; set `models_dir` in `~/.config/mococo/config.json`
  to put them on a big disk).
- No GPU needed. ffmpeg is bundled through imageio-ffmpeg.

See CLAUDE.md for the code map and dev/design/ for the design record.

The default `127.0.0.1` address is only reachable on the host computer. Before
making the app available to other people, deploy it on a reachable server and
add user authentication and per-user project access controls; the current
project list and files are shared by everyone who can reach the server.

## Run without Claude Code

MoCoCo uses Codex by default, including for keyframe images. Install the
[Codex CLI](https://developers.openai.com/codex/cli/), then run `codex login`
once with your ChatGPT account. The CLI sign-in is separate from the Codex
desktop app. Eligible ChatGPT plans can use their plan allowance; no API key is
needed. Film keyframes and prompts are sent to OpenAI. The optional search for
external reference images is skipped with this backend.
For longer films, MoCoCo detects all shots and captions up to 320 frames spread
across the running time to keep subscription usage manageable. Change this with
`mococo ingest <project> --max-captions N` before generating the index.

To use a fully local model instead, install [Ollama](https://ollama.com/download),
start its local server, and download a vision model once:

```
ollama serve
ollama pull qwen3-vl:4b-instruct
```

Set `MOCOCO_LLM_PROVIDER=ollama` before starting MoCoCo and keep Ollama
running. The model download is about 3.3 GB; inference stays on your computer
and requires no API key. Set `MOCOCO_OLLAMA_MODEL` to another installed vision
model if desired. The optional search for external reference images is skipped.

To use the original Claude Code backend instead, set
`MOCOCO_LLM_PROVIDER=claude` in the process environment.
