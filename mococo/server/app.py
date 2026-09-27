"""Local HTTP API. The web UI is a thin client of this; nothing here holds state
beyond the projects folder and the in-memory job table."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mococo import styles
from mococo.media import ffmpeg
from mococo.project import Project, Settings, init_project
from mococo.server.jobs import Jobs

STAGES = ["ingest", "script.draft", "script.translate", "script.segment", "retrieve", "cut", "voice", "render", "run"]
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class NewProject(BaseModel):
    slug: str
    film: str
    title: str | None = None
    style: str = "recap"
    script_langs: list[str] = ["zh"]
    subtitle_langs: list[str] | None = None
    voice_langs: list[str] | None = None
    target_minutes: float = 5.0
    brief: str = ""


class StageRequest(BaseModel):
    force: bool = False
    lang: str | None = None
    top: int = 6
    whisper: str = "small"


def create_app(projects_root: Path, films_root: Path | None = None) -> FastAPI:
    projects_root.mkdir(parents=True, exist_ok=True)
    films_root = films_root or (projects_root.parent / "data" / "films")
    app = FastAPI(title="MoCoCo", version="0.1.0")
    jobs = Jobs()

    def proj(slug: str) -> Project:
        if not SLUG.match(slug):
            raise HTTPException(400, f"bad project slug {slug!r}")
        p = Project(projects_root / slug)
        if not p.settings_path.exists():
            raise HTTPException(404, f"no project {slug}")
        return p

    def status(p: Project) -> dict:
        s = p.load()
        return {
            "ingest": p.index_npz.exists(),
            "ingest_steps": {
                "shots": p.shots_json.exists(),
                "transcript": p.transcript_json.exists(),
                "captions": p.captions_json.exists(),
                "index": p.index_npz.exists(),
            },
            "script": {l: p.script_md(l).exists() for l in s.script_langs},
            "segments": p.segments_json.exists(),
            "retrieve": p.candidates_json.exists(),
            "cut": p.timeline_json.exists(),
            "voice": {l: p.narration_timing(l).exists() for l in s.voice_langs},
            "uploads": {l: p.uploaded_narration(l).exists() for l in s.voice_langs},
            "render": {l: p.output_mp4(l).exists() for l in s.voice_langs},
        }

    @app.exception_handler(Exception)
    async def _errors(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            raise exc
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # ---- catalogue ----
    @app.get("/api/films")
    def films():
        out = []
        for f in sorted(films_root.glob("*")):
            if f.suffix.lower() in (".mp4", ".mkv", ".mov", ".webm", ".avi"):
                out.append({"path": str(f.resolve()), "name": f.name, "size": f.stat().st_size})
        return out

    @app.get("/api/styles")
    def list_styles():
        return {k: {"label": v["label"], "guidance": v["guidance"]} for k, v in styles.STYLES.items()}

    @app.get("/api/voices")
    def voices(lang: str):
        from mococo.media import tts

        return tts.list_voices({"zh": "zh-CN", "en": "en-US"}.get(lang, lang))

    # ---- projects ----
    @app.get("/api/projects")
    def list_projects():
        out = []
        for d in sorted(projects_root.iterdir()):
            p = Project(d)
            if p.settings_path.exists():
                s = p.load()
                out.append({"slug": p.slug, "title": s.title, "style": s.style, "created": s.created, "status": status(p)})
        return out

    @app.post("/api/projects")
    def new_project(body: NewProject):
        if not SLUG.match(body.slug):
            raise HTTPException(400, "slug must be lowercase letters, digits, - or _")
        try:
            p = init_project(
                projects_root / body.slug,
                Path(body.film),
                title=body.title,
                style=body.style,
                script_langs=body.script_langs,
                subtitle_langs=body.subtitle_langs or body.script_langs,
                voice_langs=body.voice_langs or body.script_langs,
                target_minutes=body.target_minutes,
                brief=body.brief,
            )
        except (FileExistsError, FileNotFoundError) as e:
            raise HTTPException(400, str(e))
        p.log_event("project_created", via="ui")
        return {"slug": p.slug, "settings": p.load(), "status": status(p)}

    @app.get("/api/projects/{slug}")
    def get_project(slug: str):
        p = proj(slug)
        film = Path(p.load().film)
        return {
            "slug": slug,
            "settings": p.load(),
            "status": status(p),
            "film": ffmpeg.probe(film) if film.exists() else None,
            "jobs": [asdict(j) for j in jobs.for_project(slug)[:5]],
        }

    @app.put("/api/projects/{slug}/settings")
    def put_settings(slug: str, body: Settings):
        p = proj(slug)
        p.save(body)
        p.log_event("settings_changed", via="ui")
        return body

    @app.delete("/api/projects/{slug}")
    def delete_project(slug: str):
        p = proj(slug)
        shutil.rmtree(p.root)
        return {"deleted": slug}

    # ---- files: the editable artifacts ----
    def file_path(p: Project, name: str) -> Path:
        table = {
            "shots": p.shots_json,
            "transcript": p.transcript_json,
            "captions": p.captions_json,
            "segments": p.segments_json,
            "candidates": p.candidates_json,
            "timeline": p.timeline_json,
            "events": p.events_log,
        }
        if name in table:
            return table[name]
        m = re.match(r"^script\.(zh|en)$", name)
        if m:
            return p.script_md(m.group(1))
        m = re.match(r"^timing\.(zh|en)$", name)
        if m:
            return p.narration_timing(m.group(1))
        raise HTTPException(404, f"unknown file {name}")

    @app.get("/api/projects/{slug}/files/{name}")
    def get_file(slug: str, name: str):
        path = file_path(proj(slug), name)
        if not path.exists():
            raise HTTPException(404, f"{name} not produced yet")
        if path.suffix == ".md":
            return {"text": path.read_text(encoding="utf-8")}
        if path.suffix == ".jsonl":
            return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return json.loads(path.read_text(encoding="utf-8"))

    @app.put("/api/projects/{slug}/files/{name}")
    async def put_file(slug: str, name: str, request: Request):
        p = proj(slug)
        path = file_path(p, name)
        body = await request.json()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".md":
            path.write_text(body["text"], encoding="utf-8")
        else:
            p.write_json(path, body)
        p.log_event("file_edited", file=name, via="ui")
        return {"ok": True}

    # ---- stages ----
    @app.post("/api/projects/{slug}/stages/{stage}")
    def run_stage(slug: str, stage: str, body: StageRequest):
        p = proj(slug)
        if stage not in STAGES:
            raise HTTPException(400, f"unknown stage {stage}; one of {STAGES}")
        from mococo.stages import cut, ingest, render, retrieve, script, voice

        def fn():
            p.log_event("stage_started", stage=stage, via="ui", force=body.force)
            if stage == "ingest":
                return ingest.run(p, force=body.force, whisper_size=body.whisper)
            if stage == "script.draft":
                return [str(x) for x in script.draft(p, lang=body.lang, force=body.force)]
            if stage == "script.translate":
                langs = [body.lang] if body.lang else p.load().script_langs[1:]
                return [str(script.translate(p, l, force=True)) for l in langs]
            if stage == "script.segment":
                return str(script.segment(p, force=body.force))
            if stage == "retrieve":
                return str(retrieve.run(p, top=body.top, force=body.force))
            if stage == "cut":
                return str(cut.run(p, force=body.force))
            if stage == "voice":
                return [str(x) for x in voice.run(p, lang=body.lang, force=body.force)]
            if stage == "render":
                return [str(x) for x in render.run(p, lang=body.lang, force=body.force)]
            if stage == "run":
                ingest.run(p, force=body.force)
                script.draft(p, force=body.force)
                script.segment(p, force=body.force)
                retrieve.run(p, force=body.force)
                cut.run(p, force=body.force)
                voice.run(p, force=body.force)
                return [str(x) for x in render.run(p, force=body.force)]

        try:
            job = jobs.start(slug, stage, fn)
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        return asdict(job)

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        try:
            return asdict(jobs.get(job_id))
        except KeyError as e:
            raise HTTPException(404, str(e))

    # ---- interaction traces ----
    @app.post("/api/projects/{slug}/events")
    async def post_event(slug: str, request: Request):
        body = await request.json()
        kind = body.pop("kind", "ui")
        proj(slug).log_event(kind, via="ui", **body)
        return {"ok": True}

    # ---- media ----
    @app.get("/api/projects/{slug}/media/frame/{shot_id}")
    def frame(slug: str, shot_id: str):
        p = proj(slug)
        path = p.frames_dir / f"{shot_id}.jpg"
        if not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="image/jpeg")

    @app.get("/api/projects/{slug}/media/external/{name}")
    def external(slug: str, name: str):
        path = proj(slug).external_dir / name
        if not path.exists() or ".." in name:
            raise HTTPException(404)
        return FileResponse(path)

    @app.get("/api/projects/{slug}/media/film")
    def film(slug: str):
        path = Path(proj(slug).load().film)
        return FileResponse(path, media_type="video/mp4" if path.suffix == ".mp4" else "video/x-matroska")

    @app.get("/api/projects/{slug}/media/preview/{shot_id}")
    def preview(slug: str, shot_id: str):
        """Small mp4 of one shot, cut on first request and cached."""
        p = proj(slug)
        shots = {s["id"]: s for s in p.read_json(p.shots_json)}
        if shot_id not in shots:
            raise HTTPException(404)
        out = p.ingest / "previews" / f"{shot_id}.mp4"
        if not out.exists():
            sh = shots[shot_id]
            ffmpeg.cut_clip(Path(p.load().film), sh["start"], sh["end"], out, width=640)
        return FileResponse(out, media_type="video/mp4")

    @app.get("/api/projects/{slug}/media/narration/{lang}")
    def narration(slug: str, lang: str):
        path = proj(slug).narration_audio(lang)
        if not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="audio/mpeg")

    @app.get("/api/projects/{slug}/media/output/{lang}")
    def output(slug: str, lang: str):
        path = proj(slug).output_mp4(lang)
        if not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="video/mp4", filename=f"{slug}.{lang}.mp4")

    @app.post("/api/projects/{slug}/upload/narration/{lang}")
    async def upload_narration(slug: str, lang: str, file: UploadFile):
        p = proj(slug)
        raw = p.voice_dir / f"upload.{lang}.raw{Path(file.filename or '').suffix or '.bin'}"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(await file.read())
        ffmpeg.run(["-i", str(raw), "-ac", "1", "-ar", "16000", str(p.uploaded_narration(lang))])
        for stale in (p.narration_audio(lang), p.narration_timing(lang), p.output_mp4(lang)):
            stale.unlink(missing_ok=True)
        p.log_event("narration_uploaded", lang=lang, via="ui")
        return {"ok": True, "path": str(p.uploaded_narration(lang))}

    @app.delete("/api/projects/{slug}/upload/narration/{lang}")
    def delete_upload(slug: str, lang: str):
        p = proj(slug)
        p.uploaded_narration(lang).unlink(missing_ok=True)
        return {"ok": True}

    # ---- static web app (built into web/dist) ----
    dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            target = dist / path
            if path and target.is_file():
                return FileResponse(target)
            return FileResponse(dist / "index.html")
    else:

        @app.get("/")
        def no_ui():
            return Response("MoCoCo API is running. Build the web app (cd web && npm run build) for the UI.", media_type="text/plain")

    return app
