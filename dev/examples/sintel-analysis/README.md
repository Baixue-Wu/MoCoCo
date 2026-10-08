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

The analysis page leads with a video player, download link, chapter seeking and the
finished transcript. Source notes and the existing interactive study follow it.
The website plays a pre-rendered video; this does not turn GitHub Pages into a
live rendering or model service.
