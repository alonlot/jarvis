"""STUB plugin — replace with your real mail API.

The shape here is what the assistant will see in its system prompt. Keep the
decorator metadata accurate when you swap in real logic; the assistant uses
descriptions and arg schemas to decide when/how to call tools.
"""
from __future__ import annotations

from jarvis.tools.base import tool


@tool(
    name="last_mails",
    description="Return the user's most recent emails. REPLACE THIS STUB with a real impl.",
    args={
        "count": {"type": "integer", "default": 10,
                  "description": "Number of recent emails to return."},
        "folder": {"type": "string", "default": "INBOX",
                   "description": "Folder/label to read from."},
    },
)
def last_mails(assistant, *, count: int = 10, folder: str = "INBOX"):
    return {
        "stub": True,
        "folder": folder,
        "count": count,
        "note": "Replace jarvis/tools/plugins/mail_stub.py with your real mail integration.",
        "example": [
            {"from": "alice@example.com", "subject": "PR feedback",
             "snippet": "Left a couple of comments on your branch", "received": "2026-05-25T08:14:00Z"},
        ],
    }


@tool(
    name="send_mail",
    description="Send an email. STUB — replace with your real SMTP/API call.",
    args={
        "to": {"type": "string"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
)
def send_mail(assistant, *, to: str, subject: str, body: str):
    return {"stub": True, "to": to, "subject": subject,
            "note": "Replace with real send. Did NOT actually send."}
