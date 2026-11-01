"""Persistence queries for monitors and check history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from .probe import Probe


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_monitor(conn: sqlite3.Connection, name: str, url: str, interval_s: int) -> int:
    """Insert a monitor and return its new id."""
    cursor = conn.execute(
        "INSERT INTO monitors (name, url, interval_s, active, created_at)"
        " VALUES (?, ?, ?, 1, ?)",
        (name, url, interval_s, _now()),
    )
    return int(cursor.lastrowid)


def get_monitor(conn: sqlite3.Connection, monitor_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()


def list_monitors(conn: sqlite3.Connection, include_inactive: bool = True) -> list[sqlite3.Row]:
    sql = "SELECT * FROM monitors"
    if not include_inactive:
        sql += " WHERE active = 1"
    return list(conn.execute(sql + " ORDER BY id").fetchall())


def update_monitor(conn: sqlite3.Connection, monitor_id: int, fields: dict[str, Any]) -> bool:
    """Apply a partial update. Returns False when there is nothing to change."""
    allowed = {"name", "interval_s", "active"}
    assignments = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not assignments:
        return False
    clause = ", ".join(f"{key} = ?" for key in assignments)
    conn.execute(
        f"UPDATE monitors SET {clause} WHERE id = ?",
        list(assignments.values()) + [monitor_id],
    )
    return True


def delete_monitor(conn: sqlite3.Connection, monitor_id: int) -> bool:
    cursor = conn.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
    return cursor.rowcount > 0


def record_check(conn: sqlite3.Connection, monitor_id: int, result: Probe) -> int:
    """Persist a probe result and return the check id."""
    cursor = conn.execute(
        "INSERT INTO checks (monitor_id, ok, status_code, latency_ms, error, checked_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (monitor_id, int(result.ok), result.status_code, result.latency_ms, result.error, _now()),
    )
    return int(cursor.lastrowid)


def recent_checks(conn: sqlite3.Connection, monitor_id: int, limit: int = 50) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM checks WHERE monitor_id = ?"
            " ORDER BY checked_at DESC, id DESC LIMIT ?",
            (monitor_id, limit),
        ).fetchall()
    )


def last_check(conn: sqlite3.Connection, monitor_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM checks WHERE monitor_id = ? ORDER BY checked_at DESC, id DESC LIMIT 1",
        (monitor_id,),
    ).fetchone()


def health_summary(
    conn: sqlite3.Connection, monitor_id: int
) -> tuple[Optional[float], Optional[float]]:
    """Return (uptime percentage, mean latency) over all recorded checks."""
    row = conn.execute(
        "SELECT COUNT(*) AS total, SUM(ok) AS passed, AVG(latency_ms) AS avg_latency"
        " FROM checks WHERE monitor_id = ?",
        (monitor_id,),
    ).fetchone()
    if row is None or not row["total"]:
        return None, None
    uptime = round(100.0 * (row["passed"] or 0) / row["total"], 2)
    latency = round(row["avg_latency"], 2) if row["avg_latency"] is not None else None
    return uptime, latency


def status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Count monitors by their latest known state."""
    rows = conn.execute("SELECT id FROM monitors WHERE active = 1").fetchall()
    up = down = unknown = 0
    for row in rows:
        latest = last_check(conn, row["id"])
        if latest is None:
            unknown += 1
        elif latest["ok"]:
            up += 1
        else:
            down += 1
    return {"monitors": len(rows), "up": up, "down": down, "unknown": unknown}
