# MoCoCo web

React + Vite + TypeScript front end. A thin client of the FastAPI app in
`mococo/server/app.py`; it holds no state beyond what it fetches, and every
project file it edits (script, segments, candidates, timeline, settings) is
also a plain file you can edit by hand on the CLI side.

## Dev

Run the API server first (from the repo root):

```
uv run uvicorn mococo.server.app:create_app --factory --reload --port 8765
```

Then, in `web/`:

```
npm install
npm run dev
```

Vite proxies `/api/*` to `http://127.0.0.1:8765` (see `vite.config.ts`), so
the dev server can be opened on its own port with the API calls forwarded.

## Build

```
npm install
npm run build
```

Type-checks with `tsc -b` and outputs static files to `web/dist`, which
`mococo/server/app.py` serves at `/` (and `/api/...` for the API) when it
exists.

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
