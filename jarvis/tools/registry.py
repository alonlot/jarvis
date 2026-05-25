"""Tool registry — auto-discovers @tool-decorated functions in plugins/."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any

from .base import Tool

log = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}
        self._assistant = None

        # Built-in tools always available.
        self._register_builtins()

    def discover_plugins(self, assistant) -> None:
        """Import every module under jarvis.tools.plugins and register tools."""
        self._assistant = assistant
        from . import plugins as plugins_pkg  # noqa: WPS433

        plugin_dir = Path(plugins_pkg.__file__).parent
        for mod_info in pkgutil.iter_modules([str(plugin_dir)]):
            if mod_info.name.startswith("_"):
                continue
            mod_name = f"{plugins_pkg.__name__}.{mod_info.name}"
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                log.exception("Failed to load plugin %s", mod_name)
                continue
            for attr in dir(mod):
                obj = getattr(mod, attr)
                t = getattr(obj, "_jarvis_tool", None)
                if isinstance(t, Tool):
                    self.register(t)
        log.info("Loaded %d tools: %s", len(self.tools), ", ".join(sorted(self.tools)))

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            log.warning("Tool %s already registered; overwriting", tool.name)
        self.tools[tool.name] = tool

    def call(self, name: str, args: dict[str, Any]) -> Any:
        if name not in self.tools:
            raise KeyError(f"unknown tool: {name}")
        return self.tools[name].call(self._assistant, args)

    def describe_for_prompt(self) -> str:
        return "\n".join(t.describe() for t in self.tools.values())

    # ------------------------------------------------------------------
    # Built-ins (always available; not in plugins/ because they need to
    # touch core internals like memory + config).
    # ------------------------------------------------------------------
    def _register_builtins(self) -> None:
        def remember(assistant, *, kind: str, key: str, value: str, pinned: bool = False):
            assistant.memory.remember(
                kind=kind, key=key, value=value, source="assistant", pinned=pinned,
            )
            return {"ok": True, "pinned": pinned}

        def pin_memory(assistant, *, kind: str, key: str, pinned: bool = True):
            ok = assistant.memory.pin(kind, key, pinned)
            return {"ok": ok}

        def forget(assistant, *, kind: str | None = None, key: str | None = None):
            n = assistant.memory.forget(kind=kind, key=key)
            return {"removed": n}

        def recall(assistant, *, query: str, limit: int = 8):
            return [
                {"kind": f.kind, "key": f.key, "value": f.value, "pinned": f.pinned}
                for f in assistant.memory.search_facts(query, limit=limit)
            ]

        def read_memory(assistant, *, kind: str | None = None, key: str | None = None):
            """Exact fetch. If only `kind` given, returns every fact of that kind.
            If both given, returns the single fact. If neither, returns the index."""
            if kind and key:
                f = assistant.memory.get_fact(kind, key)
                if not f:
                    return {"found": False, "kind": kind, "key": key}
                return {"found": True, "kind": f.kind, "key": f.key,
                        "value": f.value, "pinned": f.pinned}
            if kind:
                return [
                    {"key": f.key, "value": f.value, "pinned": f.pinned}
                    for f in assistant.memory.all_facts() if f.kind == kind
                ]
            # Neither — return the structural index.
            return {"index": assistant.memory.index_summary(),
                    "stats": assistant.memory.stats()}

        def set_config(assistant, *, key: str, value):
            assistant.config.set(key, value)
            assistant.config.save()
            return {"ok": True, "path": str(assistant.config.path)}

        def get_config(assistant, *, key: str):
            return {"value": assistant.config.get(key)}

        def add_routine(assistant, *, name: str, cron: str, prompt: str,
                        ask_before_acting: bool = True):
            routines = list(assistant.config.get("routines") or [])
            routines = [r for r in routines if r.get("name") != name]
            routines.append({
                "name": name, "cron": cron, "prompt": prompt,
                "ask_before_acting": ask_before_acting,
            })
            assistant.config.set("routines", routines)
            assistant.config.save()
            if assistant.scheduler:
                assistant.scheduler.reload()
            return {"ok": True}

        def remove_routine(assistant, *, name: str):
            routines = [r for r in (assistant.config.get("routines") or []) if r.get("name") != name]
            assistant.config.set("routines", routines)
            assistant.config.save()
            if assistant.scheduler:
                assistant.scheduler.reload()
            return {"ok": True}

        def list_routines(assistant):
            return assistant.config.get("routines") or []

        def spawn_agent(assistant, *, prompt: str, cwd: str | None = None):
            """Spawn a claude -p agent directly (skips confirmation)."""
            job = assistant.agents.spawn(prompt, cwd=cwd, on_done=assistant._on_agent_done)
            return {"id": job.id, "cwd": str(job.cwd), "status": job.status}

        def list_tools(assistant):
            return [
                {"name": t.name, "description": t.description, "args": t.args_schema}
                for t in self.tools.values()
            ]

        from .base import tool as _tool

        # Wrap each as a Tool by attaching .  _jarvis_tool then registering.
        decls = [
            (remember, "remember",
             "Store a long-term fact in memory. Set pinned=true ONLY for facts "
             "that should appear in every prompt (user's name, address style, "
             "always-on preferences). Everything else stays in the index and "
             "is fetched on demand via read_memory.",
             {"kind": {"type": "string",
                       "description": "Category: identity | preference | routine | project | note | ..."},
              "key": {"type": "string", "description": "Stable short slug, e.g. 'name', 'standup_time'."},
              "value": {"type": "string"},
              "pinned": {"type": "boolean", "default": False}}),
            (pin_memory, "pin_memory",
             "Pin or unpin an existing fact so it appears in every prompt.",
             {"kind": {"type": "string"}, "key": {"type": "string"},
              "pinned": {"type": "boolean", "default": True}}),
            (read_memory, "read_memory",
             "Fetch a specific fact by (kind, key), or all facts of a kind, "
             "or the structural index. Prefer this over assuming memory contents.",
             {"kind": {"type": "string", "default": None},
              "key": {"type": "string", "default": None}}),
            (forget, "forget", "Forget facts by kind and/or key (omit both to wipe all).",
             {"kind": {"type": "string", "default": None}, "key": {"type": "string", "default": None}}),
            (recall, "recall", "Fuzzy keyword search over long-term memory.",
             {"query": {"type": "string"}, "limit": {"type": "integer", "default": 8}}),
            (set_config, "set_config", "Set a config value by dotted key. Persists to disk.",
             {"key": {"type": "string"}, "value": {"type": "any"}}),
            (get_config, "get_config", "Read a config value by dotted key.",
             {"key": {"type": "string"}}),
            (add_routine, "add_routine", "Add or replace a scheduled routine.",
             {"name": {"type": "string"}, "cron": {"type": "string"},
              "prompt": {"type": "string"},
              "ask_before_acting": {"type": "boolean", "default": True}}),
            (remove_routine, "remove_routine", "Remove a scheduled routine by name.",
             {"name": {"type": "string"}}),
            (list_routines, "list_routines", "List all scheduled routines.", {}),
            (spawn_agent, "spawn_agent",
             "Spawn an autonomous claude -p agent to do work in a directory. "
             "Prefer `ask_user` first for anything that edits files.",
             {"prompt": {"type": "string"},
              "cwd": {"type": "string", "default": None,
                      "description": "Working directory for the agent."}}),
            (list_tools, "list_tools", "List every tool currently available.", {}),
        ]
        for fn, name, desc, schema in decls:
            self.register(Tool(name=name, description=desc, args_schema=schema, fn=fn, needs_assistant=True))
