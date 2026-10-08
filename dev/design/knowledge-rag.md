# Knowledge-grounded analysis

The local editor now supports importing reference text, retrieving relevant
passages, generating cited commentary suggestions, inspecting the evidence and
approving or revoking suggestions. Approved, current-source suggestions inform
the next AI script draft. Existing scripts are not overwritten unless explicitly
regenerated; `script/evidence.json` records the supplied context. This file records
prompt provenance, not a sentence-by-sentence entailment audit of the final script.

## Proposal mapping

- DG3: project-scoped source corpus, passages with provenance, retrieval-augmented
  synthesis, and visible missing-evidence messages.
- DG4: inspect sources, accept or revoke suggestions, edit the final script.
- DG1/DG2: per-unit contextual passages accompany the existing shot candidates.
  These additions do not implement the proposal's complete multimodal coverage
  gap model or prove affective/temporal alignment.
- External images: Wikimedia Commons search, explicit license/author review,
  approved download and timeline insertion, revocation, and visible export credits.
  Automatic contextual searches propose candidates; they never approve images.
  Legacy images without approval metadata must be re-approved before rendering.

The initial retrieval method is BM25 using English tokens and Chinese bigrams.
It is lexical, not embedding-based or cross-language semantic retrieval. It only
searches imported source text, never silently browses the web. The public study
uses an explicitly labeled substring filter on its small prepared source set.
An empty result does not call a model. Cite IDs are checked against the retrieved
set; relevance, correctness and disagreements still require human judgment.

## Film and review

Use **Sintel (2010)**, directed by Colin Levy, Blender Foundation.

- [Official film download](https://download.blender.org/durian/movies/Sintel.2010.720p.mkv.zip)
- [Official rights statement](https://durian.blender.org/sharing)
- [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)
- [Shashwat Pant, “Sintel, the Movie: Open Source Goes to Hollywood” (2010-12-01)](https://www.opensourceforu.com/2010/12/sintel-the-movie-open-source-goes-to-hollywood/)

The review discusses the tragic reversal of care, expression and mood. The demo
uses short paraphrased notes, not the full article. It does not inherit the film's
license. The review's imprecise copyright description is not used as licensing
authority; use the official statement. Movie-derived stills carry
`© copyright Blender Foundation | www.sintel.org`, the license link and the change
notice. Re-sharing the complete film requires its full credits. This permission
must not be generalized to third-party logos or separately licensed soundtrack
albums.

A further research option is [Jeffrey Vance's Sherlock Jr. essay](https://www.loc.gov/static/programs/national-film-preservation-board/documents/Sherlock-Jr_Vance.pdf).
The [Commons film page](https://commons.wikimedia.org/wiki/File:Sherlock_Jr._(1924).webm)
identifies US public-domain status and country-specific terms. Sintel avoids
relying on that jurisdiction-specific assumption for the new demonstration.

## Local operation

After installing the project with `uv sync`, create an analysis project normally
or reuse a project with the Sintel film. In the editor, open **Script → Sources
and evidence**. Paste source metadata and text, retrieve passages, then generate
suggestions. Generation sends the question and retrieved passages to the existing
configured provider; it does not submit the entire source corpus.

CLI equivalent:

```bash
uv run mococo init projects/sintel-rag --film data/films/Sintel.2010.720p.mkv --title Sintel --style analysis
uv run mococo knowledge add projects/sintel-rag mococo/examples/sintel/review.json
uv run mococo knowledge add projects/sintel-rag mococo/examples/sintel/observations.json
uv run mococo knowledge add projects/sintel-rag mococo/examples/sintel/license.json
uv run mococo knowledge search projects/sintel-rag '悲剧 表情 小龙'
uv run mococo knowledge suggest projects/sintel-rag '如何比较照料小龙与悲剧结局的情绪作用？'
uv run mococo knowledge review projects/sintel-rag <answer-id> --accept
# Then use the normal ingest and script-draft workflow.
```

To revoke, run `knowledge review` without `--accept`. Source changes invalidate
previous approvals and cause drafting to fail with a repair message until those
approvals are reviewed. Source removal does not erase old answer snapshots; the
historical evidence remains in `knowledge/answers.json` for inspection.

## External image workflow

Open **Shots → Find and insert contextual images**, enter an English query such
as `Sintel concept art`, inspect the source page, author and license, then approve.
The image is downloaded into the project and inserted at the start of that unit;
if no cut exists, the next cut includes it. Adjust length/order in Cut or revoke
from Shots. Re-render after edits. Re-running retrieval preserves approved images.

The provider currently accepts attributed raster images with CC BY, CC0 or public
domain metadata. It excludes other licenses rather than guessing their terms.
Approval refreshes license metadata; export rejects images without an approved
record. Each used image adds an eight-second credit card plus Markdown/JSON credit
sidecars. This metadata check does not verify a Commons uploader's ownership or
prove the image's relevance; the creator still inspects the original file page.
Downloads are restricted to Wikimedia image hosts, with redirect and size checks.

```bash
uv run mococo images search projects/sintel-rag u001 'Sintel concept art'
uv run mococo images approve projects/sintel-rag u001 22488114
uv run mococo images revoke projects/sintel-rag u001 22488114
```

The demonstration uses [David Revoy's young Sintel concept portrait](https://commons.wikimedia.org/wiki/File:Character_Sintel-portrait-young.png),
credited to David Revoy / Blender Foundation, CC BY 3.0. It illustrates production
context, not an original movie shot or evidence of authorial intent.

## Public example

`#/examples/sintel-analysis` offers source filtering, a recorded real model run,
side-by-side film stills, prepared interpretation drafts, user selection/edit notes
an external-image insert plan, and a Markdown export including sources and attribution. It is not a live
model service or a finished new commentary video. Static user edits are not
persisted after navigation; the page explicitly tells users to export.

Rebuild assets from a local authorized film:

```bash
uv run python scripts/export_analysis_example.py --film data/films/Sintel.2010.720p.mkv --dest web/public/examples/sintel-analysis --evidence-project projects/sintel-rag
npm --prefix web run build:public
```

The optional `--evidence-project` exports a saved model response. Without it the
example includes only the prepared study. No private project paths or credentials
are included. The root research PDF duplicates `dev/materials/` and is untouched.

## Verification (2026-10-08)

- 25 Python tests passed, including 6 added checks covering scoped retrieval and
  character locations, Chinese queries, empty-evidence behavior, approval/stale
  sources, fabricated citations, draft context/provenance and API validation.
- One real model-backed run on the three public source notes produced four cited
  claims and explicit evidence gaps; it remains unapproved. This validates one
  provider execution, not general factual accuracy or research effectiveness.
- Three image checks cover approval/revocation, unknown images and license changes,
  and real ffmpeg rendering with an attribution card. A live Commons search and
  download also produced a 17.88-second Chinese TTS/subtitle image-insertion clip
  at `projects/sintel-rag/render/output.zh.mp4` (local verification artifact).
- Local and public TypeScript/Vite builds passed.
- Browser checks cover public filtering, evidence expansion, mobile width, export
  of selected claims/notes, retrieval/empty results in the actual local editor, and approved image timeline/credits.
  Three browser tests passed. The image browser case requires the prepared local
  `sintel-rag` project with an approved portrait, a cut and a completed render.

Run Python checks with `uv run pytest -q`. For browser checks, serve the local app
on 8766 with a `sintel-rag` project containing the sample sources and a saved
suggestion, and preview the public build on 8767:

```bash
uv run mococo serve --port 8766
# Separate terminals, from web/:
npx vite preview --mode public --host 127.0.0.1 --port 8767
npx playwright install chromium
npm run test:e2e
```
