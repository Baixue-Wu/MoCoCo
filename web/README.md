# MoCoCo web

React + Vite + TypeScript front end. A thin client of the FastAPI app in
`mococo/server/app.py`; it holds no state beyond what it fetches, and every
project file it edits (script, segments, candidates, timeline, settings) is
also a plain file you can edit by hand on the CLI side.

The public GitHub Pages build uses this same interface in a limited mode:
visitors can browse the *Sherlock Jr.* read-only project and import a film into their
own browser's IndexedDB storage. The film is never sent to GitHub or another
server. That public build does not run the AI pipeline or export new videos.
The example's actual project decisions are exported from the completed local
project by `python scripts/export_public_example.py` into `web/public/examples/`.
The export contains JSON, 37 keyframes, and narration audio, with no private
absolute paths or source movie in the Git tree.

## Dev

Run the API server first (from the repo root):

```
uv run mococo serve --projects projects
```

Then, in `web/`:

```
npm install
npm run dev
```

Vite proxies `/api/*` to `http://127.0.0.1:8765` (see `vite.config.ts`), so
the dev server can be opened on its own port with the API calls forwarded.
The new-project form uploads the visitor's selected movie with one multipart
request to `/api/projects/upload`, showing progress while it transfers. The API
stores the movie inside that project's `source/` folder and checks that it can
be read before creating `project.json`.

## Build

```
npm install
npm run build
```

Type-checks with `tsc -b` and outputs static files to `web/dist`, which
`mococo/server/app.py` serves at `/` (and `/api/...` for the API) when it
exists.

For the public version, run `npm run build:public`. It writes into `docs/`
for GitHub Pages at `/MoCoCo/`. This build uses hash-based routes so visitors
can reload an example or browser-local project directly. Existing showcase
media in `docs/assets/` is retained.

## Structure

```
src/
  api.ts              typed fetch wrapper, one function per endpoint
  App.tsx             header + router
  index.css           global styles (plain CSS, no framework)
  i18n/               t() over en.json / zh.json, persisted language toggle
  state/
    ProjectContext.tsx   per-project data + job polling, shared by all wizard steps
    steps.ts             which of the six steps count as "done"
  components/         shared bits: Toast, Spinner, Modal, StageBar, LangChecks, ProgressDots
  screens/
    Home.tsx           project list + "new project" modal
    NewProjectForm.tsx
    Project.tsx        wizard shell: sidebar + "run all remaining"
    steps/             Setup, Script, Shots, Cut, Voice, Export — one file each
```

Only three runtime dependencies: `react`, `react-dom`, `react-router-dom`.
i18n is a from-scratch `t(key, vars)` over two JSON dictionaries, no library.

See `API-REQUESTS.md` for notes on anything the API didn't quite have.
