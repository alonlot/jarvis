"""Merge / pull request tools — minimal real implementations.

Talks to GitHub and GitLab via REST. Tokens read from env vars configured in
`git.hosts[].token_env`. Returns merged list across hosts.

These are intentionally simple — extend to fetch CR comments per MR, etc.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

from jarvis.tools.base import tool

log = logging.getLogger(__name__)


def _hosts(assistant) -> list[dict]:
    return assistant.config.get("git.hosts") or []


def _gh_username(token: str) -> str | None:
    try:
        r = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.ok:
            return r.json().get("login")
    except Exception:                                        # noqa: BLE001
        log.exception("github user lookup failed")
    return None


def _github_prs(token: str) -> list[dict[str, Any]]:
    user = _gh_username(token)
    if not user:
        return []
    q = f"is:pr is:open author:{user}"
    r = requests.get(
        "https://api.github.com/search/issues",
        params={"q": q, "per_page": 50},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    if not r.ok:
        return []
    items = r.json().get("items", [])
    out = []
    for it in items:
        out.append({
            "host": "github",
            "url": it["html_url"],
            "title": it["title"],
            "repo": it["repository_url"].split("/repos/")[-1],
            "review_comments": it.get("comments", 0),
            "updated_at": it["updated_at"],
            "draft": it.get("draft", False),
        })
    return out


def _gitlab_mrs(base_url: str, token: str) -> list[dict[str, Any]]:
    if not token:
        return []
    base = base_url.rstrip("/")
    r = requests.get(
        f"{base}/api/v4/merge_requests",
        params={"state": "opened", "scope": "created_by_me", "per_page": 50},
        headers={"PRIVATE-TOKEN": token},
        timeout=15,
    )
    if not r.ok:
        return []
    out = []
    for it in r.json():
        out.append({
            "host": "gitlab",
            "url": it["web_url"],
            "title": it["title"],
            "repo": it.get("references", {}).get("full") or it.get("project_id"),
            "review_comments": it.get("user_notes_count", 0),
            "updated_at": it["updated_at"],
            "draft": it.get("draft", False) or it.get("work_in_progress", False),
        })
    return out


@tool(
    name="my_merge_requests",
    description="Return all of the user's open PRs/MRs across configured git hosts.",
    args={},
)
def my_merge_requests(assistant):
    out: list[dict] = []
    for host in _hosts(assistant):
        kind = host.get("kind")
        token_env = host.get("token_env") or ""
        token = os.environ.get(token_env, "") if token_env else ""
        if kind == "github" and token:
            out.extend(_github_prs(token))
        elif kind == "gitlab" and token:
            out.extend(_gitlab_mrs(host.get("base_url", "https://gitlab.com"), token))
    return out


@tool(
    name="mr_review_comments",
    description=(
        "STUB. Replace with your real implementation: fetch unresolved review "
        "comments for a single MR/PR URL and return them as a list of "
        "{file, line, body, author}."
    ),
    args={"url": {"type": "string"}},
)
def mr_review_comments(assistant, *, url: str):
    return {
        "stub": True,
        "url": url,
        "note": "Implement me in jarvis/tools/plugins/merge_requests.py",
    }
