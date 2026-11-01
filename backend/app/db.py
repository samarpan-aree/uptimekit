"""Database layer: connection handling and schema bootstrap."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_PATH = Path("uptimekit.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS monitors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    url         TEXT    NOT NULL,
    interval_s  INTEGER NOT NULL DEFAULT 300,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS checks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id   INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    ok           INTEGER NOT NULL,
    status_code  INTEGER,
    latency_ms   REAL,
    error        TEXT,
    checked_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checks_monitor
    ON checks (monitor_id, checked_at DESC);
"""


def db_path() -> Path:
    """Resolve the database path from the environment at call time."""
    return Path(os.environ.get("UPTIMEKIT_DB", DEFAULT_PATH))


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with row access by name and FK enforcement."""
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Transactional connection: commits on success, rolls back on error."""
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: Path | None = None) -> None:
    """Create tables and indexes if they do not exist."""
    with session(path) as conn:
        conn.executescript(SCHEMA)
