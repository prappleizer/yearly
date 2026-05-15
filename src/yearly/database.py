"""
database.py – thin sqlite3 wrapper for YearView.

The DB file location is resolved at *runtime* (not relative to __file__) so
the package works correctly whether run from source or installed via pip.

Resolution order:
  1. YEARVIEW_DB environment variable (absolute or relative path)
  2. <cwd>/data/yearview.db
"""

import os
import sqlite3
from pathlib import Path
from typing import Any


def _db_path() -> Path:
    env = os.environ.get("YEARVIEW_DB")
    if env:
        return Path(env)
    return Path.cwd() / "data" / "yearview.db"


_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(path), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_db() -> None:
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            color      TEXT    NOT NULL DEFAULT '#6b7280',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT    NOT NULL,
            start_date     TEXT    NOT NULL,
            end_date       TEXT    NOT NULL,
            tag_id         INTEGER REFERENCES tags(id) ON DELETE SET NULL,
            is_travel      INTEGER NOT NULL DEFAULT 0,
            is_preliminary INTEGER NOT NULL DEFAULT 0,
            description    TEXT,
            created_at     TEXT    DEFAULT CURRENT_TIMESTAMP,
            updated_at     TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date);
        CREATE INDEX IF NOT EXISTS idx_events_tag   ON events(tag_id);
    """)
    conn.commit()

    # Seed default tags when the table is empty
    row = conn.execute("SELECT COUNT(*) FROM tags").fetchone()
    if row[0] == 0:
        conn.executemany(
            "INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)",
            [
                ("Vacation", "#10b981", 0),
                ("Conference", "#f59e0b", 1),
                ("Observing Run", "#6366f1", 2),
                ("Deadline", "#ef4444", 3),
            ],
        )
        conn.commit()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def query_all(sql: str, params: list[Any] | None = None) -> list[dict]:
    conn = _get_conn()
    cur = conn.execute(sql, params or [])
    return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: list[Any] | None = None) -> dict | None:
    rows = query_all(sql, params)
    return rows[0] if rows else None


def run(sql: str, params: list[Any] | None = None) -> tuple[int, int]:
    """Execute a write statement. Returns (lastrowid, rowcount)."""
    conn = _get_conn()
    cur = conn.execute(sql, params or [])
    conn.commit()
    return cur.lastrowid, cur.rowcount
