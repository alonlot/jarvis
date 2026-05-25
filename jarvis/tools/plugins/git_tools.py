"""Git workspace tools — these are REAL (not stubs). Scan configured roots
for git repos and surface branches / status / recent activity.

Configure roots in config.yaml under `git.scan_roots`.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from jarvis.tools.base import tool


def _expand_roots(assistant) -> list[Path]:
    roots = assistant.config.get("git.scan_roots") or []
    return [Path(os.path.expanduser(r)) for r in roots]


def _is_git_repo(p: Path) -> bool:
    return (p / ".git").exists()


def _find_repos(roots: list[Path], max_depth: int = 4) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if _is_git_repo(root):
            found.append(root)
            continue
        for dirpath, dirnames, _ in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth > max_depth:
                dirnames[:] = []
                continue
            if ".git" in dirnames:
                found.append(Path(dirpath))
                dirnames[:] = []   # don't descend into a repo
    return found


def _git(repo: Path, *args: str, timeout: int = 10) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        return out.stdout.strip()
    except Exception as e:                                    # noqa: BLE001
        return f"(git error: {e})"


@tool(
    name="list_repos",
    description="List every git repository under the configured scan roots.",
    args={},
)
def list_repos(assistant):
    repos = _find_repos(_expand_roots(assistant))
    return [{"path": str(r), "name": r.name} for r in repos]


@tool(
    name="repo_status",
    description="Show branch, dirty status, and last commit for a repo.",
    args={"path": {"type": "string", "description": "Absolute path to the repo."}},
)
def repo_status(assistant, *, path: str):
    p = Path(os.path.expanduser(path))
    if not _is_git_repo(p):
        return {"error": f"{p} is not a git repo"}
    return {
        "path": str(p),
        "branch": _git(p, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(_git(p, "status", "--porcelain")),
        "last_commit": _git(p, "log", "-1", "--pretty=%h %s (%cr)"),
        "upstream": _git(p, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") or None,
    }


@tool(
    name="recent_activity",
    description="Cross-repo summary of recent commits authored by the user.",
    args={
        "days": {"type": "integer", "default": 7,
                 "description": "Window in days to summarise."},
        "author": {"type": "string", "default": "",
                   "description": "Override git author filter; defaults to local user.email."},
    },
)
def recent_activity(assistant, *, days: int = 7, author: str = ""):
    out = []
    for repo in _find_repos(_expand_roots(assistant)):
        a = author or _git(repo, "config", "user.email")
        log = _git(
            repo, "log", f"--since={days}.days.ago", f"--author={a}",
            "--pretty=%h|%cs|%s", "--no-merges",
        )
        if not log or log.startswith("(git error"):
            continue
        commits = []
        for line in log.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
        if commits:
            out.append({"repo": str(repo), "commits": commits})
    return out


@tool(
    name="list_branches",
    description="List local branches across all repos, marking which are ahead of upstream.",
    args={},
)
def list_branches(assistant):
    out = []
    for repo in _find_repos(_expand_roots(assistant)):
        raw = _git(repo, "for-each-ref", "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
                   "refs/heads/")
        branches = []
        for line in raw.splitlines():
            parts = line.split("|")
            while len(parts) < 3:
                parts.append("")
            branches.append({"name": parts[0], "upstream": parts[1], "track": parts[2]})
        if branches:
            out.append({"repo": str(repo), "branches": branches})
    return out
