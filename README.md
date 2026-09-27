# MoCoCo · Movie Commentary Co-creation

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
once with `cd web && npm install && npm run build`).

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://docs.anthropic.com/claude-code) installed and logged in
  (`claude` on PATH). All language and vision model calls go through it.
- Network access for edge-tts voices and the first-time model downloads
  (whisper, bge-m3, about 3 GB; set `models_dir` in `~/.config/mococo/config.json`
  to put them on a big disk).
- No GPU needed. ffmpeg is bundled through imageio-ffmpeg.

See CLAUDE.md for the code map and dev/design/ for the design record.
