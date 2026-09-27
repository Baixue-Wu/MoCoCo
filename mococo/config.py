"""Machine-level settings (not project settings): where downloaded models live.

Read from ~/.config/mococo/config.json when present. Nothing here is required;
defaults work on a fresh machine.
"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "mococo" / "config.json"


def _read() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def models_dir() -> Path:
    """Folder for whisper and embedding model weights. Override with
    {"models_dir": "/big/disk/mococo-models"} in ~/.config/mococo/config.json."""
    d = Path(_read().get("models_dir", Path.home() / ".cache" / "mococo" / "models")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d
