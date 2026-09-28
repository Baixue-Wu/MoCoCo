# Questions for Zhaoyang / Baixue

Things Claude could not settle alone. Newest first. Move an answered item into
design-decisions.md and delete it here.

## 2026-09-28 (overnight build)

- **Burned-in subtitles need libass in ffmpeg.** The Linux static build from
  imageio-ffmpeg has it; the macOS and Windows builds may not. Fallback options:
  ship subtitles as a soft track (player-dependent), or draw them with Pillow onto
  frames (portable, more work). Which matters more for the demo: identical output
  on every OS, or fastest path on Baixue's Mac? Default until told: try libass,
  fall back to soft subtitles with a warning.
- **Default voices.** I picked zh-CN-YunxiNeural (male, lively) and en-US-GuyNeural.
  Baixue may prefer a female narrator; the setting is per project in project.json.
- **Sintel's shot detector found 144 shots (adaptive threshold 3.0).** Feels
  slightly coarse; lowering to 2.0 gives more, smaller shots and more caption
  calls. Tune after seeing a full run.
- **The dev machine's root disk (/) is 100% full (1.1 GB free).** Not MoCoCo's
  doing; I moved model caches to /nvme-disk/zhaoyang/baixue/mococo-models via
  ~/.config/mococo/config.json. Claude Code's own temp dir also lives on /, so
  tool output can fail with ENOSPC. Worth clearing something on / when awake.
- **TODO (Zhaoyang): smoke-test on a Mac.** Points to check: `uv sync` (torch
  CPU wheel), imageio-ffmpeg's binary has libass for the `subtitles` filter,
  `claude` on PATH, edge-tts reachable. Also `scripts/fetch_film.py sintel`.
- **Voice quality ceiling.** edge-tts is free and keyless but sounds like TTS.
  Options if that matters for the user study: a local model (CosyVoice 2,
  Fish Speech, IndexTTS; needs a GPU or patience) or a paid API (MiniMax,
  ElevenLabs). The provider boundary (mococo/media/tts.py) is the only file
  that would change.
