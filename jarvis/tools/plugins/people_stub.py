"""STUB plugin — replace with your real "search data on a person" API."""
from __future__ import annotations

from jarvis.tools.base import tool


@tool(
    name="search_person",
    description="Look up info about a person by name or identifier. REPLACE THIS STUB.",
    args={
        "query": {"type": "string", "description": "Name, email, or other identifier."},
    },
)
def search_person(assistant, *, query: str):
    return {
        "stub": True,
        "query": query,
        "note": "Replace jarvis/tools/plugins/people_stub.py with your real people API.",
        "example": {
            "name": query,
            "title": "Unknown",
            "team": "Unknown",
            "last_interaction": None,
        },
    }
