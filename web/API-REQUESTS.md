# API requests / observations

Notes from building the web UI against `mococo/server/app.py`. Nothing here
blocked the UI; these are minor gaps or things worked around, kept here per
instruction rather than editing `mococo/`.

- **No per-language job tracking.** `POST /projects/{slug}/stages/{stage}`
  keys the "already running" check purely on project + stage name (see
  `Jobs.start`), and `GET /jobs/{id}` doesn't include which `lang` a job was
  started with. For `script.translate` this is fine in practice (v1 only ever
  has one non-primary language, since script languages are a subset of
  {zh, en}), but if a third language were ever added, running translate for
  two languages at once would 409 against each other rather than running in
  parallel. Worked around by not needing that case.
- **No endpoint to list a project's events without loading the whole log
  as JSON.** `GET /files/events` returns the full `events.jsonl` parsed to an
  array; fine at demo scale, would want pagination for a long-running project.
  The Export screen's cost summary just sums client-side.
- **Settings PUT has no partial-update / PATCH.** Editing one setting field
  requires sending the whole `Settings` object back (which the UI does; the
  form always holds a full `Settings`). Not a real gap, just noting the shape.
- **No dedicated endpoint for "does this project have a script yet before
  drafting"** beyond `status.script[lang]`; the Script screen uses that plus a
  client-side confirm dialog before forcing `script.draft`.

Nothing here required leaving a feature unimplemented.
