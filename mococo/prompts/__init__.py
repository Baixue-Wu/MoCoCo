"""Prompt templates live as .md files next to this module. load(name).substitute(...)"""

from __future__ import annotations

from pathlib import Path
from string import Template

_DIR = Path(__file__).parent


def load(name: str) -> Template:
    path = _DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt {name} missing at {path}")
    return Template(path.read_text(encoding="utf-8"))


def render(name: str, **kw) -> str:
    return load(name).substitute(**kw)
