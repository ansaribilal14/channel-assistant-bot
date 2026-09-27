"""SQLite storage — zero-cost, zero-config, single file.

Two tables:
  leads       — captured from the DM lead flow (name / contact / question)
  unanswered  — questions the bot could not answer (fuels the owner alert)
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

_conn: Optional[sqlite3.Connection] = None


def _db_path(data_dir: str) -> str:
    return os.path.join(data_dir, "assistant.db")


def init(data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    global _conn
    _conn = sqlite3.connect(_db_path(data_dir), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT NOT NULL,
            chat_id     TEXT,
            username    TEXT,
            first_name  TEXT,
            source      TEXT,
            name        TEXT,
            contact     TEXT,
            question    TEXT,
            status      TEXT DEFAULT 'new'
        );
        CREATE TABLE IF NOT EXISTS unanswered (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT NOT NULL,
            chat_id     TEXT,
            username    TEXT,
            text        TEXT,
            status      TEXT DEFAULT 'open'
        );
        """
    )
    _conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _c() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("store.init() was not called")
    return _conn


# --------------------------------------------------------------------- leads
def add_lead(chat_id: str, username: str, first_name: str, source: str,
             name: str, contact: str, question: str) -> int:
    cur = _c().execute(
        "INSERT INTO leads (created_at, chat_id, username, first_name, source, name, contact, question)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (_now(), chat_id, username, first_name, source, name, contact, question),
    )
    _c().commit()
    return int(cur.lastrowid)


def list_leads(limit: int = 10) -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def mark_lead_done(lead_id: int) -> bool:
    cur = _c().execute("UPDATE leads SET status='done' WHERE id=?", (lead_id,))
    _c().commit()
    return cur.rowcount > 0


def export_leads_csv() -> io.BytesIO:
    buf = io.StringIO()
    writer = csv.writer(buf)
    rows = _c().execute("SELECT * FROM leads ORDER BY id ASC").fetchall()
    cols = ["id", "created_at", "chat_id", "username", "first_name", "source",
            "name", "contact", "question", "status"]
    writer.writerow(cols)
    for r in rows:
        writer.writerow([r[c] for c in cols])
    return io.BytesIO(buf.getvalue().encode("utf-8"))


# ---------------------------------------------------------------- unanswered
def add_unanswered(chat_id: str, username: str, text: str) -> int:
    cur = _c().execute(
        "INSERT INTO unanswered (created_at, chat_id, username, text) VALUES (?,?,?,?)",
        (_now(), chat_id, username, text),
    )
    _c().commit()
    return int(cur.lastrowid)


def list_unanswered(limit: int = 10) -> list[sqlite3.Row]:
    return _c().execute(
        "SELECT * FROM unanswered WHERE status='open' ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()


def mark_unanswered_done(u_id: int) -> bool:
    cur = _c().execute("UPDATE unanswered SET status='resolved' WHERE id=?", (u_id,))
    _c().commit()
    return cur.rowcount > 0
