"""STUB plugin — replace with your real calendar API."""
from __future__ import annotations

from datetime import date

from jarvis.tools.base import tool


@tool(
    name="schedule_today",
    description="Return today's calendar events. REPLACE THIS STUB.",
    args={},
)
def schedule_today(assistant):
    return {
        "stub": True,
        "date": date.today().isoformat(),
        "note": "Replace jarvis/tools/plugins/calendar_stub.py with your real calendar API.",
        "example": [
            {"start": "09:30", "end": "10:00", "title": "Standup"},
            {"start": "14:00", "end": "15:00", "title": "Design review"},
        ],
    }


@tool(
    name="schedule_for",
    description="Return calendar events for a given ISO date. STUB.",
    args={"date": {"type": "string", "description": "ISO date e.g. 2026-05-25"}},
)
def schedule_for(assistant, *, date: str):
    return {"stub": True, "date": date,
            "note": "Replace with real calendar lookup."}
