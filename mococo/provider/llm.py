"""Language-model backends used by all pipeline stages."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from threading import Semaphore
from typing import Literal

import httpx

Tier = Literal["fast", "smart"]

MODELS: dict[Tier, str] = {"fast": "haiku", "smart": "sonnet"}
_OLLAMA_CALLS = Semaphore(1)  # The pipeline has workers; one local model fits in memory.
_CODEX_CALLS = Semaphore(1)  # Keep subscription requests from the pipeline sequential.


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
    tools: list[str] | None = None,
    timeout: int = 600,
    log=None,
) -> str | dict:
    """Send one prompt, get text back (or a dict when schema is given).

    Codex uses the signed-in CLI and the user's ChatGPT plan by default.
    Set MOCOCO_LLM_PROVIDER=ollama or claude to choose another backend.
    log: optional callable(kind, **fields) for cost tracing.
    """
    images = [Path(p).resolve() for p in (images or [])]
    for p in images:
        if not p.exists():
            raise FileNotFoundError(f"image not found: {p}")

    provider = os.getenv("MOCOCO_LLM_PROVIDER", "codex").strip().lower()
    if provider == "codex":
        return _ask_codex(prompt, tier=tier, images=images, schema=schema,
                          system=system, tools=tools, timeout=timeout, log=log)
    if provider == "ollama":
        return _ask_ollama(prompt, tier=tier, images=images, schema=schema,
                           system=system, tools=tools, timeout=timeout, log=log)
    if provider == "claude":
        return _ask_claude(prompt, tier=tier, images=images, schema=schema,
                           system=system, tools=tools, timeout=timeout, log=log)
    raise LLMError(f"unknown MOCOCO_LLM_PROVIDER {provider!r}; use codex, ollama or claude")


def _strict_schema(schema: dict) -> dict:
    """Give Codex's structured output the strict object shape it requires."""
    result = {key: value for key, value in schema.items() if key not in {"properties", "items"}}
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        result["properties"] = {key: _strict_schema(value) for key, value in properties.items()}
        result["required"] = list(properties)
        result["additionalProperties"] = False
    if "items" in schema:
        result["items"] = _strict_schema(schema["items"])
    return result


def _ask_codex(
    prompt: str,
    *,
    tier: Tier,
    images: list[Path],
    schema: dict | None,
    system: str | None,
    tools: list[str] | None,
    timeout: int,
    log,
) -> str | dict:
    if tools:
        # The optional external-image lookup needs a verified web-search tool.
        raise LLMError("WebSearch/WebFetch are unavailable with the Codex backend")
    executable = shutil.which("codex")
    if not executable:
        raise LLMError("Codex CLI not found. Install Codex and run `codex login`.")

    full_prompt = "Answer the task below directly. Do not run commands or edit files.\n"
    if system:
        full_prompt += f"\nInstructions:\n{system}\n"
    full_prompt += f"\nTask:\n{prompt}"
    if schema:
        full_prompt += "\n\nReturn only JSON matching the requested output schema."

    with tempfile.TemporaryDirectory(prefix="mococo-codex-") as folder:
        output_file = Path(folder) / "reply.txt"
        cmd = [
            executable, "exec", "--ephemeral", "--skip-git-repo-check",
            "--ignore-user-config", "--sandbox", "read-only",
            "--output-last-message", str(output_file),
        ]
        model = os.getenv("MOCOCO_CODEX_MODEL", "").strip() or {
            "fast": "gpt-6-luna", "smart": "gpt-6.1-sol",
        }[tier]
        cmd += ["--model", model]
        if schema:
            schema_file = Path(folder) / "schema.json"
            schema_file.write_text(json.dumps(_strict_schema(schema)), encoding="utf-8")
            cmd += ["--output-schema", str(schema_file)]
        for path in images:
            cmd += ["--image", str(path)]
        cmd.append("-")
        start = time.monotonic()
        try:
            with _CODEX_CALLS:
                proc = subprocess.run(
                    cmd, input=full_prompt, capture_output=True, text=True,
                    encoding="utf-8", timeout=timeout, check=False,
                )
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"Codex timed out after {timeout}s") from e

        if proc.returncode != 0:
            error = (proc.stderr or proc.stdout).strip()[-1000:]
            if "Not logged in" in error or "login" in error.lower():
                raise LLMError("Codex CLI is not signed in. Run `codex login` once.")
            raise LLMError(f"Codex exited {proc.returncode}: {error}")
        if not output_file.exists():
            raise LLMError("Codex finished without an answer")
        content = output_file.read_text(encoding="utf-8").strip()

    if log:
        log("llm_call", tier=tier, model=model or "codex-default", images=len(images),
            input_tokens=0, output_tokens=0, cost_usd=0.0,
            duration_ms=int((time.monotonic() - start) * 1000))
    if schema:
        try:
            result = json.loads(_strip_fence(content))
        except json.JSONDecodeError as e:
            raise LLMError(f"Codex returned invalid JSON: {content[:500]}") from e
        if not isinstance(result, dict):
            raise LLMError("Codex returned JSON that is not an object")
        return result
    return content


def _ask_ollama(
    prompt: str,
    *,
    tier: Tier,
    images: list[Path],
    schema: dict | None,
    system: str | None,
    tools: list[str] | None,
    timeout: int,
    log,
) -> str | dict:
    if tools:
        # External reference images are optional; retrieve.external() catches this.
        raise LLMError("WebSearch/WebFetch are unavailable with local Ollama")

    model = os.getenv("MOCOCO_OLLAMA_MODEL", "qwen3-vl:4b-instruct")
    host = os.getenv("MOCOCO_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    user = {"role": "user", "content": prompt}
    if images:
        user["images"] = [base64.b64encode(path.read_bytes()).decode("ascii") for path in images]
    messages.append(user)
    request = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_ctx": 32768},
    }
    if schema:
        request["format"] = schema
    if images and schema:
        request["options"]["num_predict"] = int(
            os.getenv("MOCOCO_OLLAMA_MAX_TOKENS", str(max(800, len(images) * 300)))
        )

    try:
        with _OLLAMA_CALLS:
            response = httpx.post(
                f"{host}/api/chat", json=request,
                timeout=httpx.Timeout(timeout, connect=10), trust_env=False,
            )
        response.raise_for_status()
        payload = response.json()
    except httpx.ConnectError as e:
        raise LLMError("Cannot reach Ollama. Start it with `ollama serve`.") from e
    except httpx.HTTPStatusError as e:
        raise LLMError(f"Ollama error {e.response.status_code}: {e.response.text[:500]}") from e
    except (httpx.HTTPError, ValueError) as e:
        raise LLMError(f"Ollama request failed: {e}") from e

    if log:
        log(
            "llm_call", tier=tier, model=model, images=len(images),
            input_tokens=payload.get("prompt_eval_count", 0),
            output_tokens=payload.get("eval_count", 0),
            cost_usd=0.0,
            duration_ms=payload.get("total_duration", 0) // 1_000_000,
        )

    content = payload.get("message", {}).get("content", "")
    if schema:
        try:
            result = json.loads(_strip_fence(content))
        except json.JSONDecodeError as e:
            raise LLMError(f"Ollama returned invalid JSON: {content[:500]}") from e
        if not isinstance(result, dict):
            raise LLMError("Ollama returned JSON that is not an object")
        return result
    return content


def _ask_claude(
    prompt: str,
    *,
    tier: Tier,
    images: list[Path],
    schema: dict | None,
    system: str | None,
    tools: list[str] | None,
    timeout: int,
    log,
) -> str | dict:
    """Original Claude Code CLI backend."""

    cmd = [
        _claude_bin(),
        "-p",
        "--no-session-persistence",
        "--model",
        MODELS[tier],
        "--output-format",
        "json",
        "--tools",
        ",".join((["Read"] if images else []) + list(tools or [])),
    ]
    if images:
        cmd += ["--add-dir", str(images[0].parent)]
    if tools:
        # headless runs cannot answer permission prompts, so pre-approve exactly these
        cmd += ["--allowedTools", ",".join(tools), "--max-turns", "12"]
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
            check=False,
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
