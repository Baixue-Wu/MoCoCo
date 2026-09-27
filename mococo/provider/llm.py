"""The one place that knows which language model we use and how to call it.

v1 backend: the Claude Code CLI in headless mode (`claude -p`), which runs on the
developer's Claude subscription. Swap this file for an API-key backend later; the
rest of the codebase only calls ask().
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Literal

Tier = Literal["fast", "smart"]

MODELS: dict[Tier, str] = {"fast": "haiku", "smart": "sonnet"}


class LLMError(RuntimeError):
    pass


def _claude_bin() -> str:
    exe = shutil.which("claude")
    if not exe:
        raise LLMError(
            "claude CLI not found on PATH. Install Claude Code and log in: "
            "https://docs.anthropic.com/claude-code then run `claude` once."
        )
    return exe


def ask(
    prompt: str,
    *,
    tier: Tier = "fast",
    images: list[Path] | None = None,
    schema: dict | None = None,
    system: str | None = None,
    timeout: int = 600,
    log=None,
) -> str | dict:
    """Send one prompt, get text back (or a dict when schema is given).

    images: local files the model should look at; they are read through the CLI's
    Read tool, so paths must be absolute.
    log: optional callable(kind, **fields) for cost tracing.
    """
    images = [Path(p).resolve() for p in (images or [])]
    for p in images:
        if not p.exists():
            raise FileNotFoundError(f"image not found: {p}")

    cmd = [
        _claude_bin(),
        "-p",
        "--no-session-persistence",
        "--model",
        MODELS[tier],
        "--output-format",
        "json",
        "--tools",
        "Read" if images else "",
    ]
    if images:
        cmd += ["--add-dir", str(images[0].parent)]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    if system:
        cmd += ["--system-prompt", system]

    full_prompt = prompt
    if images:
        listing = "\n".join(str(p) for p in images)
        full_prompt = (
            "First, use the Read tool to look at every one of these image files, in order:\n"
            f"{listing}\n\nThen answer the task below.\n\n{prompt}"
        )

    try:
        proc = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise LLMError(f"claude timed out after {timeout}s: {' '.join(cmd)}") from e
    if proc.returncode != 0:
        raise LLMError(
            f"claude exited {proc.returncode}\ncmd: {' '.join(cmd)}\nstderr:\n{proc.stderr}\nstdout:\n{proc.stdout[:2000]}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"claude returned non-JSON output:\n{proc.stdout[:2000]}") from e

    if payload.get("is_error") or payload.get("subtype") not in (None, "success"):
        raise LLMError(f"claude reported an error: {json.dumps(payload)[:2000]}")

    if log:
        usage = payload.get("usage", {})
        log(
            "llm_call",
            tier=tier,
            model=MODELS[tier],
            images=len(images),
            input_tokens=usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cost_usd=payload.get("total_cost_usd", 0.0),
            duration_ms=payload.get("duration_api_ms", 0),
        )

    if schema:
        structured = payload.get("structured_output")
        if structured is None:
            # older CLI versions put the JSON in result text
            text = payload.get("result", "")
            try:
                structured = json.loads(_strip_fence(text))
            except json.JSONDecodeError as e:
                raise LLMError(f"expected JSON matching schema, got:\n{text[:2000]}") from e
        return structured
    return payload.get("result", "")


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()
