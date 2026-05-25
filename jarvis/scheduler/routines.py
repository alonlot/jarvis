"""Cron-style routines.

Each routine in config.yaml fires as if the user had typed `prompt` to Jarvis.
That means routines get the full tool/agent stack — a morning briefing can
genuinely list MRs, ask whether to fix CR comments, and spawn an agent.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from ..core.assistant import Assistant

log = logging.getLogger(__name__)


class RoutineScheduler:
    def __init__(self, assistant: "Assistant"):
        self.assistant = assistant
        self.scheduler = BackgroundScheduler()
        self._loaded: list[str] = []

    def start(self) -> None:
        self._load()
        self.scheduler.start()
        log.info("Scheduler started with %d routine(s)", len(self._loaded))

    def reload(self) -> None:
        for jid in self._loaded:
            try:
                self.scheduler.remove_job(jid)
            except Exception:                                  # noqa: BLE001
                pass
        self._loaded.clear()
        self._load()
        log.info("Routines reloaded (%d)", len(self._loaded))

    def stop(self) -> None:
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:                                      # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    def _load(self) -> None:
        for r in (self.assistant.config.get("routines") or []):
            name = r.get("name")
            cron = r.get("cron")
            prompt = r.get("prompt", "")
            if not (name and cron and prompt):
                log.warning("Skipping malformed routine: %s", r)
                continue
            try:
                trigger = CronTrigger.from_crontab(cron)
            except Exception:
                log.exception("Bad cron for %s: %r", name, cron)
                continue
            job_id = f"routine:{name}"
            self.scheduler.add_job(
                self._fire, trigger=trigger, id=job_id,
                args=[name, prompt], replace_existing=True,
            )
            self._loaded.append(job_id)

    def _fire(self, name: str, prompt: str) -> None:
        log.info("Routine fired: %s", name)
        try:
            self.assistant.chat(prompt)
        except Exception:
            log.exception("Routine %s failed", name)
