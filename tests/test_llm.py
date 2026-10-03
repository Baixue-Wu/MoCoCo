"""Checks for the local language-model transport without downloading a model."""

import base64
import json
import subprocess
from pathlib import Path

import httpx
import pytest

from mococo.provider import llm


class _Reply:
    def __init__(self, content: str):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "message": {"content": self.content},
            "prompt_eval_count": 12,
            "eval_count": 5,
            "total_duration": 2_000_000,
        }


def test_ollama_sends_images_and_schema(tmp_path, monkeypatch):
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"example image")
    sent = []
    events = []

    def fake_post(url, **kwargs):
        sent.append((url, kwargs))
        return _Reply('{"shots": []}')

    monkeypatch.setenv("MOCOCO_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(httpx, "post", fake_post)
    schema = {"type": "object", "properties": {"shots": {"type": "array"}}}
    result = llm.ask("Describe frame 1", images=[image], schema=schema,
                     log=lambda *args, **kwargs: events.append((args, kwargs)))

    assert result == {"shots": []}
    url, kwargs = sent[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert kwargs["json"]["format"] == schema
    assert kwargs["json"]["messages"][-1]["images"] == [
        base64.b64encode(b"example image").decode("ascii")
    ]
    assert events[0][1]["cost_usd"] == 0


def test_ollama_requires_running_server(monkeypatch):
    monkeypatch.setenv("MOCOCO_LLM_PROVIDER", "ollama")

    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", offline)
    with pytest.raises(llm.LLMError, match="Start it with `ollama serve`"):
        llm.ask("Hello")


def test_local_mode_skips_optional_web_search(monkeypatch):
    monkeypatch.setenv("MOCOCO_LLM_PROVIDER", "ollama")
    with pytest.raises(llm.LLMError, match="unavailable"):
        llm.ask("Find images", tools=["WebSearch", "WebFetch"])


def test_codex_uses_image_and_strict_schema(tmp_path, monkeypatch):
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"image")
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["prompt"] = kwargs["input"]
        seen["schema"] = json.loads(Path(cmd[cmd.index("--output-schema") + 1]).read_text())
        Path(cmd[cmd.index("--output-last-message") + 1]).write_text('{"shots": []}')
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.delenv("MOCOCO_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(llm.shutil, "which", lambda name: "codex.exe")
    monkeypatch.setattr(llm.subprocess, "run", fake_run)
    schema = {"type": "object", "properties": {"shots": {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
              "required": ["shots"]}

    assert llm.ask("Describe it", images=[image], schema=schema) == {"shots": []}
    assert seen["cmd"][seen["cmd"].index("--image") + 1] == str(image)
    assert seen["schema"]["additionalProperties"] is False
    assert seen["schema"]["properties"]["shots"]["items"]["additionalProperties"] is False
    assert "Describe it" in seen["prompt"]
    assert "--ephemeral" in seen["cmd"]
