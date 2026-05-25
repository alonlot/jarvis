"""The Jarvis brain.

Coordinates:
  - chat LLM (with tool-calling loop)
  - memory (recent turns + long-term facts)
  - tool registry (plugins)
  - agent spawner (claude -p for autonomous work)
  - scheduler (routines)
  - persona (Jarvis voice)

Public surface used by GUI / voice / scheduler:
  - chat(text) -> str
  - on_assistant_message: list of callbacks (used by overlay/voice for TTS)
  - on_question: callback for assistant-asked questions (so GUI can prompt)
  - confirm_pending(answer) — user reply to an outstanding agent confirmation
"""
from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass
from typing import Callable

from .agent_runner import AgentJob, AgentRunner
from .config import Config
from .llm import LLMBackend, Message, build_llm
from .memory import Memory

log = logging.getLogger(__name__)

TOOL_LOOP_MAX = 6   # safety cap on tool-call iterations per user turn


@dataclass
class PendingConfirmation:
    id: str
    question: str
    action: dict       # {"kind": "spawn_agent", "prompt": "...", "cwd": "..."} etc.


class Assistant:
    def __init__(self, config: Config):
        self.config = config
        self.memory = Memory(
            db_path=config.data_dir() / "memory.db",
            max_recent_turns=int(config.get("memory.max_recent_turns", 40)),
        )
        self.llm: LLMBackend = build_llm(config, "llm")
        self.agents = AgentRunner(config)

        # Lazy imports to keep startup fast.
        from ..tools.registry import ToolRegistry
        self.tools = ToolRegistry()
        self.tools.discover_plugins(self)   # passes self so plugins can use memory/config/agents

        self.scheduler = None      # set by start_background_services()
        self.voice = None          # set by GUI / headless wrapper if voice on
        self._pending: dict[str, PendingConfirmation] = {}

        # Hooks.
        self.on_assistant_message: list[Callable[[str], None]] = []
        self.on_question: list[Callable[[str, str], None]] = []   # (pending_id, question)
        self.on_agent_update: list[Callable[[AgentJob], None]] = []

    # -----------------------------------------------------------------------
    # System prompt
    # -----------------------------------------------------------------------
    def _system_prompt(self) -> str:
        persona = self.config.get("persona.style", "")
        addr = self.config.get("persona.address_user_as", "sir")
        pinned = self.memory.pinned_summary()
        index = self.memory.index_summary()
        stats = self.memory.stats()
        tools_doc = self.tools.describe_for_prompt()

        memory_section = self._render_memory_section(pinned, index, stats)
        return f"""{persona.strip()}

The user prefers to be addressed as "{addr}".

# Tools
You have access to a set of tools. To call one, emit EXACTLY this fenced block
(and nothing else when calling a tool — call ONE tool at a time, then wait):

<tool_call>{{"name": "<tool_name>", "args": {{ ... }}}}</tool_call>

If you need the user to confirm a side-effecting action (e.g. spawning an agent
to edit code), call the `ask_user` tool with a clear yes/no question and an
`action` object describing what would happen on yes. The runtime will surface
the question; do NOT proceed until the runtime tells you the answer.

When no tool is needed, just reply normally to the user.

## Available tools
{tools_doc}

{memory_section}
""".strip()

    @staticmethod
    def _render_memory_section(pinned: str, index: str, stats: dict) -> str:
        if not pinned and not index:
            return (
                "# Memory\n"
                "You have no long-term memory yet. When you learn something worth keeping "
                "(a preference, a name, a routine), call `remember(kind, key, value)`. "
                "Pin it (`pinned=true`) only if it should appear in every prompt — e.g. "
                "the user's name or how they like to be addressed."
            )
        parts = ["# Memory"]
        parts.append(
            f"You have {stats['total_facts']} long-term facts "
            f"({stats['pinned_facts']} pinned). The pinned ones are shown in full below. "
            f"For unpinned facts, the index lists keys grouped by kind — use "
            f"`read_memory(kind, key)` to fetch a specific value or `recall(query)` "
            f"for fuzzy search. DO NOT ask the user about something already in memory."
        )
        if pinned:
            parts.append("\n## Pinned (always available)")
            parts.append(pinned)
        if index:
            parts.append("\n## Index (fetch with `read_memory` when relevant)")
            parts.append(index)
        return "\n".join(parts)

    # -----------------------------------------------------------------------
    # Chat
    # -----------------------------------------------------------------------
    def chat(self, user_text: str, _internal: bool = False) -> str:
        """Process a user message and return the assistant's text reply.

        Runs a small tool-calling loop: model emits <tool_call>, we run the
        tool, append the result as a tool message, ask the model again.
        """
        if not _internal:
            self.memory.add_turn("user", user_text)

        messages = self._build_message_list()

        final_text = ""
        for _ in range(TOOL_LOOP_MAX):
            reply = self.llm.chat(messages)
            if not reply.tool_calls:
                final_text = reply.text
                break

            # Record the model's tool-calling turn in the working message list
            # (don't write tool_call noise into memory).
            messages.append(Message(role="assistant", content=reply.raw))

            stop_for_user = False
            for call in reply.tool_calls:
                name = call.get("name", "")
                args = call.get("args", {}) or {}
                if name == "ask_user":
                    pending_id = self._stash_pending(args)
                    final_text = args.get("question", "(question)")
                    stop_for_user = True
                    # Surface the question to the GUI / voice.
                    for cb in self.on_question:
                        try:
                            cb(pending_id, final_text)
                        except Exception:
                            log.exception("on_question callback failed")
                    break
                try:
                    result = self.tools.call(name, args)
                except Exception as e:                          # noqa: BLE001
                    result = f"ERROR: {e}"
                messages.append(Message(role="tool", name=name, content=str(result)[:8000]))

            if stop_for_user:
                break
        else:
            final_text = "(tool loop exceeded max iterations)"

        if final_text:
            self.memory.add_turn("assistant", final_text)
            for cb in self.on_assistant_message:
                try:
                    cb(final_text)
                except Exception:
                    log.exception("on_assistant_message callback failed")
        return final_text

    def _build_message_list(self) -> list[Message]:
        msgs: list[Message] = [Message(role="system", content=self._system_prompt())]
        for t in self.memory.recent_turns():
            role = t.role if t.role in {"user", "assistant", "system"} else "user"
            msgs.append(Message(role=role, content=t.content))
        return msgs

    # -----------------------------------------------------------------------
    # Pending confirmations (assistant-asked questions)
    # -----------------------------------------------------------------------
    def _stash_pending(self, args: dict) -> str:
        pid = uuid.uuid4().hex[:8]
        self._pending[pid] = PendingConfirmation(
            id=pid,
            question=args.get("question", ""),
            action=args.get("action") or {},
        )
        return pid

    def confirm_pending(self, pending_id: str, user_answer: str) -> str:
        """Called by GUI/voice when the user answers a pending question."""
        pc = self._pending.pop(pending_id, None)
        if not pc:
            return self.chat(user_answer)

        yes = bool(re.match(r"^\s*(y|yes|sure|do it|go ahead|please)\b", user_answer, re.I))
        if yes and pc.action.get("kind") == "spawn_agent":
            prompt = pc.action.get("prompt", "")
            cwd = pc.action.get("cwd")
            job = self.agents.spawn(prompt, cwd=cwd, on_done=self._on_agent_done)
            confirmation_msg = (
                f"Very good, sir. I've spawned agent {job.id} to work on that "
                f"in {job.cwd}. I'll report back when it finishes."
            )
            self.memory.add_turn("assistant", confirmation_msg)
            for cb in self.on_assistant_message:
                cb(confirmation_msg)
            return confirmation_msg

        # Either user said no, or it's a non-action question — feed the answer
        # back into the chat loop as a regular reply.
        self.memory.add_turn("user", user_answer)
        return self.chat(
            f"(previous question: {pc.question})\n(user answer: {user_answer})",
            _internal=True,
        )

    def _on_agent_done(self, job: AgentJob) -> None:
        for cb in self.on_agent_update:
            try:
                cb(job)
            except Exception:
                log.exception("on_agent_update callback failed")
        tail = (job.output or "")[-1200:]
        msg = (
            f"Agent {job.id} finished with status {job.status}. "
            f"Last output:\n{tail}" if tail else f"Agent {job.id} finished ({job.status})."
        )
        self.memory.add_turn("assistant", msg)
        for cb in self.on_assistant_message:
            cb(msg)

    # -----------------------------------------------------------------------
    # Routines
    # -----------------------------------------------------------------------
    def start_background_services(self) -> None:
        from ..scheduler.routines import RoutineScheduler
        self.scheduler = RoutineScheduler(self)
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler:
            self.scheduler.stop()

    def run_routine_by_name(self, name: str) -> str:
        for r in (self.config.get("routines") or []):
            if r.get("name") == name:
                return self.chat(r["prompt"])
        return f"Routine '{name}' not found."
