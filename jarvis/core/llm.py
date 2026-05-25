"""LLM backends.

Two backends:
  - ClaudeCLIBackend: shells out to `claude -p`. No API key, uses your CC login.
  - OpenAICompatBackend: any OpenAI-compatible /v1/chat/completions endpoint
    (OpenAI, OpenRouter, Ollama, vLLM, LM Studio, etc).

Both expose the same `chat(messages, tools=None) -> Reply` interface. Tool calling
uses a simple text protocol we parse ourselves, so it works on ANY backend without
relying on provider-specific tool-use APIs.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

import requests

from .config import Config

log = logging.getLogger(__name__)

# Protocol: model emits a fenced block to call a tool. Designed to be obvious
# in system prompts and easy to detect with a single regex.
TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


@dataclass
class Reply:
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    raw: str = ""


@dataclass
class Message:
    role: str           # system | user | assistant | tool
    content: str
    name: str | None = None   # for role=tool, the tool name


def messages_to_prompt(messages: list[Message]) -> str:
    """Flatten message list into a single prompt string for CLI backends."""
    parts = []
    for m in messages:
        tag = m.role.upper()
        if m.name:
            tag = f"{tag}({m.name})"
        parts.append(f"[{tag}]\n{m.content}")
    parts.append("[ASSISTANT]\n")
    return "\n\n".join(parts)


def parse_tool_calls(text: str) -> tuple[str, list[dict]]:
    """Strip tool_call blocks from `text`, return (clean_text, calls)."""
    calls: list[dict] = []
    for m in TOOL_CALL_RE.finditer(text):
        try:
            calls.append(json.loads(m.group(1)))
        except json.JSONDecodeError as e:
            log.warning("Failed to parse tool_call JSON: %s", e)
    clean = TOOL_CALL_RE.sub("", text).strip()
    return clean, calls


class LLMBackend:
    def chat(self, messages: list[Message]) -> Reply:
        raise NotImplementedError


class ClaudeCLIBackend(LLMBackend):
    def __init__(self, binary: str = "claude", extra_args: list[str] | None = None, timeout: int = 600):
        self.binary = binary
        self.extra_args = list(extra_args or [])
        self.timeout = timeout

    def chat(self, messages: list[Message]) -> Reply:
        prompt = messages_to_prompt(messages)
        cmd = [self.binary, "-p", "--output-format", "text", *self.extra_args]
        log.debug("Running %s", cmd)
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Could not find Claude CLI ('{self.binary}'). Install it or switch llm.backend to openai_compat."
            ) from e
        if proc.returncode != 0:
            raise RuntimeError(f"claude -p failed ({proc.returncode}): {proc.stderr.strip()}")
        raw = proc.stdout
        clean, calls = parse_tool_calls(raw)
        return Reply(text=clean, tool_calls=calls, raw=raw)


class OpenAICompatBackend(LLMBackend):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.4, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def chat(self, messages: list[Message]) -> Reply:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": m.role if m.role != "tool" else "user",
                 "content": (f"[TOOL RESULT {m.name}]\n{m.content}" if m.role == "tool" else m.content)}
                for m in messages
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        url = f"{self.base_url}/chat/completions"
        log.debug("POST %s model=%s", url, self.model)
        r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        raw = data["choices"][0]["message"]["content"]
        clean, calls = parse_tool_calls(raw)
        return Reply(text=clean, tool_calls=calls, raw=raw)


def build_llm(cfg: Config, section: str = "llm") -> LLMBackend:
    backend = cfg.get(f"{section}.backend", "claude_cli")
    if backend == "claude_cli":
        sub = cfg.get(f"{section}.claude_cli", {}) or {}
        return ClaudeCLIBackend(
            binary=sub.get("binary", "claude"),
            extra_args=sub.get("extra_args", []),
            timeout=int(sub.get("timeout_seconds", 600)),
        )
    if backend == "openai_compat":
        sub = cfg.get(f"{section}.openai_compat", {}) or {}
        key = cfg.resolve_secret(f"{section}.openai_compat.api_key", f"{section}.openai_compat.api_key_env")
        return OpenAICompatBackend(
            base_url=sub.get("base_url", "https://api.openai.com/v1"),
            api_key=key,
            model=sub.get("model", "gpt-4o-mini"),
            temperature=float(sub.get("temperature", 0.4)),
        )
    raise ValueError(f"Unknown {section}.backend: {backend}")
