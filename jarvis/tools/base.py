"""Tool plugin base.

Write a plugin file in `jarvis/tools/plugins/` exposing one or more functions
decorated with `@tool(...)`. Discovery picks them up at startup. Each tool
gets its name, description, and a JSON-schema-like args spec; these are
inlined into the system prompt so the model knows how to call them.

Minimal example:

    from jarvis.tools.base import tool

    @tool(
        name="last_mails",
        description="Return the user's most recent emails.",
        args={"count": {"type": "integer", "default": 10}},
    )
    def last_mails(assistant, *, count: int = 10):
        # `assistant` gives you memory/config/agents if needed.
        return [{"from": "...", "subject": "...", "snippet": "..."}]
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    args_schema: dict[str, dict[str, Any]]
    fn: Callable[..., Any]
    needs_assistant: bool = True

    def call(self, assistant, args: dict[str, Any]) -> Any:
        kwargs = {k: v for k, v in (args or {}).items() if k in self.args_schema}
        if self.needs_assistant:
            return self.fn(assistant, **kwargs)
        return self.fn(**kwargs)

    def describe(self) -> str:
        lines = [f"- **{self.name}**: {self.description}"]
        if self.args_schema:
            arg_lines = []
            for k, spec in self.args_schema.items():
                t = spec.get("type", "any")
                d = spec.get("description", "")
                default = f", default={spec['default']!r}" if "default" in spec else ""
                req = "" if "default" in spec else ", required"
                arg_lines.append(f"    - `{k}` ({t}{req}{default}): {d}")
            lines.append("\n".join(arg_lines))
        return "\n".join(lines)


def tool(*, name: str, description: str, args: dict[str, dict[str, Any]] | None = None):
    """Decorator. The function's first positional arg should be `assistant`
    unless `pass_assistant=False` is set as a function attribute."""
    args = args or {}

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        needs_assistant = bool(params) and params[0].name == "assistant"
        fn._jarvis_tool = Tool(   # type: ignore[attr-defined]
            name=name,
            description=description,
            args_schema=args,
            fn=fn,
            needs_assistant=needs_assistant,
        )
        return fn

    return deco
