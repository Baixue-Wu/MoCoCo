"""A project is a folder. project.json holds every setting; stages write files next to it.

This module is the only place that knows the folder layout.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["zh", "en"]
Style = Literal["recap", "analysis"]

LANG_NAMES = {"zh": "Chinese", "en": "English"}


class Voice(BaseModel):
    """Which TTS voice to use per language. Names are edge-tts short names."""

    zh: str = "zh-CN-YunxiNeural"
    en: str = "en-US-GuyNeural"
    rate: str = "+0%"


class Settings(BaseModel):
    title: str
    film: str  # absolute path to the film file
    style: Style = "recap"
    script_langs: list[Lang] = ["zh"]
    subtitle_langs: list[Lang] = ["zh"]
    subtitle_position: Literal["bottom", "top"] = "bottom"
    voice_langs: list[Lang] = ["zh"]
    target_minutes: float = 5.0
    brief: str = ""
    voice: Voice = Field(default_factory=Voice)
    created: float = Field(default_factory=time.time)

    @property
    def primary_lang(self) -> Lang:
        return self.script_langs[0]


class Project:
    """Folder handle. Attributes are paths; nothing here touches media."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    # ---- settings ----
    @property
    def settings_path(self) -> Path:
        return self.root / "project.json"

    def load(self) -> Settings:
        if not self.settings_path.exists():
            raise FileNotFoundError(
                f"no project at {self.root}; create one with: mococo init {self.root} --film <path>"
            )
        return Settings.model_validate_json(self.settings_path.read_text(encoding="utf-8"))

    def save(self, settings: Settings) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")

    @property
    def slug(self) -> str:
        return self.root.name

    # ---- stage folders and files ----
    @property
    def ingest(self) -> Path:
        return self.root / "ingest"

    @property
    def shots_json(self) -> Path:
        return self.ingest / "shots.json"

    @property
    def frames_dir(self) -> Path:
        return self.ingest / "frames"

    @property
    def transcript_json(self) -> Path:
        return self.ingest / "transcript.json"

    @property
    def captions_json(self) -> Path:
        return self.ingest / "captions.json"

    @property
    def index_npz(self) -> Path:
        return self.ingest / "index.npz"

    @property
    def script_dir(self) -> Path:
        return self.root / "script"

    def script_md(self, lang: str) -> Path:
        return self.script_dir / f"script.{lang}.md"

    @property
    def brief_md(self) -> Path:
        return self.script_dir / "brief.md"

    @property
    def segments_json(self) -> Path:
        return self.script_dir / "segments.json"

    @property
    def sources_json(self) -> Path:
        return self.root / "knowledge" / "sources.json"

    @property
    def knowledge_answers_json(self) -> Path:
        return self.root / "knowledge" / "answers.json"

    @property
    def script_evidence_json(self) -> Path:
        return self.script_dir / "evidence.json"

    @property
    def retrieval_dir(self) -> Path:
        return self.root / "retrieval"

    @property
    def candidates_json(self) -> Path:
        return self.retrieval_dir / "candidates.json"

    @property
    def image_search_json(self) -> Path:
        return self.retrieval_dir / "image-search.json"

    @property
    def image_credits_md(self) -> Path:
        return self.render_dir / "image-credits.md"

    @property
    def image_preview_dir(self) -> Path:
        return self.retrieval_dir / "previews"

    @property
    def external_dir(self) -> Path:
        return self.retrieval_dir / "external"

    @property
    def cut_dir(self) -> Path:
        return self.root / "cut"

    @property
    def timeline_json(self) -> Path:
        return self.cut_dir / "timeline.json"

    @property
    def voice_dir(self) -> Path:
        return self.root / "voice"

    def narration_audio(self, lang: str) -> Path:
        return self.voice_dir / f"narration.{lang}.mp3"

    def narration_timing(self, lang: str) -> Path:
        return self.voice_dir / f"timing.{lang}.json"

    def uploaded_narration(self, lang: str) -> Path:
        return self.voice_dir / f"upload.{lang}.wav"

    @property
    def render_dir(self) -> Path:
        return self.root / "render"

    def subtitles_srt(self, lang: str) -> Path:
        return self.render_dir / f"subtitles.{lang}.srt"

    def output_mp4(self, lang: str) -> Path:
        return self.render_dir / f"output.{lang}.mp4"

    @property
    def events_log(self) -> Path:
        return self.root / "events.jsonl"

    # ---- json helpers ----
    @staticmethod
    def read_json(path: Path):
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; run the stage that produces it first")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- interaction traces (E2) ----
    def log_event(self, kind: str, **fields) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        rec = {"t": time.time(), "kind": kind, **fields}
        with self.events_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def init_project(root: Path, film: Path, title: str | None = None, **overrides) -> Project:
    """Create project.json. Fails loudly if the film is missing or the project exists."""
    film = Path(film).resolve()
    if not film.exists():
        raise FileNotFoundError(f"film not found: {film}")
    project = Project(root)
    if project.settings_path.exists():
        raise FileExistsError(f"{project.settings_path} already exists; pick another folder")
    settings = Settings(title=title or film.stem, film=str(film), **overrides)
    project.save(settings)
    return project
