"""Memory store: SQLite-backed conversation history + long-term facts.

Two tables:
  - turns(id, ts, role, content, meta)         — rolling chat history
  - facts(id, ts, kind, key, value, source)    — structured long-term memory

Long-term retrieval is keyword-ranked. Swap for a vector store later if needed.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)


@dataclass
class Turn:
    role: str          # user | assistant | system | tool
    content: str
    meta: dict | None = None


@dataclass
class Fact:
    kind: str          # preference | identity | routine | note | ...
    key: str
    value: str
    source: str = "user"
    ts: float = 0.0


SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  meta TEXT
);
CREATE INDEX IF NOT EXISTS turns_ts ON turns(ts);

CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,
  key  TEXT NOT NULL,
  value TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'user'
);
CREATE INDEX IF NOT EXISTS facts_kind_key ON facts(kind, key);
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
  kind, key, value, content='facts', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, kind, key, value) VALUES (new.id, new.kind, new.key, new.value);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
  INSERT INTO facts_fts(facts_fts, rowid, kind, key, value)
  VALUES('delete', old.id, old.kind, old.key, old.value);
END;
CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
  INSERT INTO facts_fts(facts_fts, rowid, kind, key, value)
  VALUES('delete', old.id, old.kind, old.key, old.value);
  INSERT INTO facts_fts(rowid, kind, key, value)
  VALUES (new.id, new.kind, new.key, new.value);
END;
"""


class Memory:
    def __init__(self, db_path: Path, max_recent_turns: int = 40):
        self.db_path = db_path
        self.max_recent_turns = max_recent_turns
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- turns --------------------------------------------------------------
    def add_turn(self, role: str, content: str, meta: dict | None = None) -> None:
        self.conn.execute(
            "INSERT INTO turns(ts, role, content, meta) VALUES(?,?,?,?)",
            (time.time(), role, content, json.dumps(meta) if meta else None),
        )
        self.conn.commit()

    def recent_turns(self, limit: int | None = None) -> list[Turn]:
        n = limit or self.max_recent_turns
        rows = self.conn.execute(
            "SELECT role, content, meta FROM turns ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        out = [Turn(role=r, content=c, meta=json.loads(m) if m else None) for r, c, m in rows]
        out.reverse()
        return out

    def clear_turns(self) -> None:
        self.conn.execute("DELETE FROM turns")
        self.conn.commit()

    # --- facts --------------------------------------------------------------
    def remember(self, kind: str, key: str, value: str, source: str = "user") -> None:
        # Upsert-on-key within kind.
        self.conn.execute("DELETE FROM facts WHERE kind=? AND key=?", (kind, key))
        self.conn.execute(
            "INSERT INTO facts(ts, kind, key, value, source) VALUES(?,?,?,?,?)",
            (time.time(), kind, key, value, source),
        )
        self.conn.commit()
        log.info("Remembered %s/%s = %s", kind, key, value[:80])

    def forget(self, kind: str | None = None, key: str | None = None) -> int:
        if kind and key:
            cur = self.conn.execute("DELETE FROM facts WHERE kind=? AND key=?", (kind, key))
        elif kind:
            cur = self.conn.execute("DELETE FROM facts WHERE kind=?", (kind,))
        else:
            cur = self.conn.execute("DELETE FROM facts")
        self.conn.commit()
        return cur.rowcount

    def all_facts(self) -> list[Fact]:
        rows = self.conn.execute(
            "SELECT ts, kind, key, value, source FROM facts ORDER BY kind, key"
        ).fetchall()
        return [Fact(ts=ts, kind=k, key=key, value=v, source=s) for ts, k, key, v, s in rows]

    def search_facts(self, query: str, limit: int = 8) -> list[Fact]:
        try:
            rows = self.conn.execute(
                """SELECT f.ts, f.kind, f.key, f.value, f.source
                   FROM facts f JOIN facts_fts ON f.id = facts_fts.rowid
                   WHERE facts_fts MATCH ? LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS query syntax can choke on punctuation. Fall back to LIKE.
            like = f"%{query}%"
            rows = self.conn.execute(
                """SELECT ts, kind, key, value, source FROM facts
                   WHERE value LIKE ? OR key LIKE ? LIMIT ?""",
                (like, like, limit),
            ).fetchall()
        return [Fact(ts=ts, kind=k, key=key, value=v, source=s) for ts, k, key, v, s in rows]

    def facts_summary(self, max_chars: int = 1200) -> str:
        """Compact bullet list of facts, suitable for the system prompt."""
        out: list[str] = []
        total = 0
        for f in self.all_facts():
            line = f"- [{f.kind}] {f.key}: {f.value}"
            if total + len(line) > max_chars:
                break
            out.append(line)
            total += len(line) + 1
        return "\n".join(out)
