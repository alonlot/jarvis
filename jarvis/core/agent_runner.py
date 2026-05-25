"""Spawn long-running 'do-work' agents via `claude -p`.

Used when Jarvis decides (or the user confirms) that a task needs an autonomous
agent to actually edit files / make commits / etc. The chat LLM is for talking;
the agent backend is for doing.
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import Config

log = logging.getLogger(__name__)


@dataclass
class AgentJob:
    id: str
    prompt: str
    cwd: Path | None = None
    extra_args: list[str] = field(default_factory=list)
    status: str = "pending"     # pending | running | done | error
    output: str = ""
    error: str = ""


class AgentRunner:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.jobs: dict[str, AgentJob] = {}
        self._lock = threading.Lock()

    def _binary_and_args(self) -> tuple[str, list[str]]:
        backend = self.cfg.get("agents.backend", "claude_cli")
        if backend != "claude_cli":
            raise NotImplementedError("Only claude_cli agent backend is implemented")
        sub = self.cfg.get("agents.claude_cli", {}) or {}
        return sub.get("binary", "claude"), list(sub.get("extra_args", []))

    def spawn(self, prompt: str, cwd: str | Path | None = None,
              on_done: Callable[[AgentJob], None] | None = None) -> AgentJob:
        binary, extra_args = self._binary_and_args()
        timeout = int(self.cfg.get("agents.claude_cli.timeout_seconds", 1800))
        if cwd is None:
            cwd = self.cfg.get("agents.default_cwd") or os.getcwd()
        cwd_path = Path(os.path.expanduser(str(cwd)))

        job_id = f"agent-{len(self.jobs) + 1:04d}"
        job = AgentJob(id=job_id, prompt=prompt, cwd=cwd_path, extra_args=extra_args)
        with self._lock:
            self.jobs[job_id] = job

        def run() -> None:
            job.status = "running"
            try:
                cmd = [binary, "-p", *extra_args]
                log.info("[%s] spawn cwd=%s cmd=%s", job_id, cwd_path, cmd)
                proc = subprocess.run(
                    cmd, input=prompt, text=True, capture_output=True,
                    cwd=str(cwd_path), timeout=timeout, check=False,
                )
                job.output = proc.stdout
                job.error = proc.stderr
                job.status = "done" if proc.returncode == 0 else "error"
            except Exception as e:                              # noqa: BLE001
                job.error = str(e)
                job.status = "error"
            finally:
                if on_done:
                    try:
                        on_done(job)
                    except Exception:                           # noqa: BLE001
                        log.exception("agent on_done callback failed")

        threading.Thread(target=run, daemon=True, name=f"agent-{job_id}").start()
        return job

    def list_jobs(self) -> list[AgentJob]:
        with self._lock:
            return list(self.jobs.values())

    def get(self, job_id: str) -> AgentJob | None:
        return self.jobs.get(job_id)
