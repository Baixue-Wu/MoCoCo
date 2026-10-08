# Sintel: finished Chinese analysis film

The deliverable is a complete movie-analysis video, not a source-notes page or an
image-insertion test. The argument follows the reversal from care to harm, the
film's changing visual relationships, and the delayed recognition of time.

`plan.json` is the editorial source of truth: Chinese narration, chapter headings,
selected time ranges in the official 720p MKV, source-note keys and the concept-art
insert. This is an AI-assisted editorial example built with MoCoCo, not an assertion
that automatic shot retrieval or a user study produced these choices. Old generated
shot captions contain mistakes and are not used as factual evidence.

The named review contributes the care/destruction contrast and a judgment about
facial expression. Claims about shot order, gesture and color are interpretations
of inspected footage, not quotations or claims about the director's intentions.
The concept portrait is production context and is identified as such in narration.

## Rebuild

First approve Commons image `22488114` in an image project using the documented
image search workflow. Supply that project to the builder. The output project must
be new, or have the same plan; use `--force` explicitly to rebuild after plan edits.

```sh
uv run python scripts/build_analysis_film.py \
  --film data/films/Sintel.2010.720p.mkv \
  --plan dev/examples/sintel-analysis/plan.json \
  --project projects/sintel-commentary \
  --source-dir mococo/examples/sintel \
  --image-project projects/sintel-rag \
  --font /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
```

Use a locally installed Chinese font path on other operating systems. The builder
calls the existing narration, rendering and image-attribution stages. It emits a
finished MP4, narration, subtitles, reviewed timeline, per-unit evidence records,
and a manifest with actual duration, chapter times and SHA-256. Film clips and
video output stay outside Git and are distributed through GitHub Releases.

The film preserves the source attribution `© copyright Blender Foundation |
www.sintel.org`, CC BY 3.0 and the adaptation notice; the concept-art card credits
David Revoy / Blender Foundation and links its Commons page. The review's full
article is not republished. On-screen commentary authorship is Baixue Wu; the
credits identify AI assistance and synthetic narration.

## Public presentation

The analysis example shares the recap example’s workflow shell. Its seven steps
are preprocessing, RAG sources, final script, shots/images, rendered timeline,
voice/subtitles and output. Each view contains the actual finished-project artifacts.
The output step offers playback, downloading and chapter seeking.
The website plays a pre-rendered video; this does not turn GitHub Pages into a
live rendering or model service.

## Published artifact and verification

The finished video is 300.18 seconds, 1280×544 at 25 fps, with audio and burned-in
Chinese subtitles. It is published under `release/sintel-analysis` on GitHub.
The manifest's SHA-256 matches the uploaded video asset digest. Full-video decoding
passed; selected frames, chapter overlays, concept-art insertion and credits were
visually inspected. A browser check loaded the real release video and sought to
the concept-art chapter. All four browser checks and 26 Python checks passed. Workflow checks cover both
examples, frame enlargement, evidence per unit, narration/subtitles, rendered timing,
mobile layouts and refreshing a step URL.

Refresh the public study after a completed build:

```sh
uv run python scripts/export_analysis_example.py \
  --film data/films/Sintel.2010.720p.mkv \
  --dest web/public/examples/sintel-analysis \
  --evidence-project projects/sintel-rag \
  --film-manifest projects/sintel-commentary/render/film-manifest.json \
  --finished-project projects/sintel-commentary \
  --narration-url https://github.com/Baixue-Wu/MoCoCo/releases/download/release/sintel-analysis/narration.zh.mp3 \
  --video-url https://github.com/Baixue-Wu/MoCoCo/releases/download/release/sintel-analysis/sintel-analysis.zh.mp4
npm --prefix web run build:public
```
