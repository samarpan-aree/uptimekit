"""Tests for the repository layer, independent of HTTP."""

from __future__ import annotations

from app import repository as repo
from app.probe import Probe


def test_create_and_fetch_monitor(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    row = repo.get_monitor(conn, monitor_id)
    assert row is not None
    assert row["name"] == "Docs"
    assert row["interval_s"] == 60
    assert row["active"] == 1


def test_get_monitor_returns_none_when_absent(conn):
    assert repo.get_monitor(conn, 424242) is None


def test_update_monitor_applies_only_known_fields(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    assert repo.update_monitor(conn, monitor_id, {"name": "Docs v2", "bogus": "x"}) is True
    row = repo.get_monitor(conn, monitor_id)
    assert row["name"] == "Docs v2"
    assert row["interval_s"] == 60


def test_update_monitor_with_no_valid_fields_is_a_noop(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    assert repo.update_monitor(conn, monitor_id, {"bogus": "x"}) is False


def test_delete_monitor_reports_whether_it_existed(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    assert repo.delete_monitor(conn, monitor_id) is True
    assert repo.delete_monitor(conn, monitor_id) is False


def test_record_and_read_back_a_check(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    repo.record_check(conn, monitor_id, Probe(True, 200, 33.3, None))
    latest = repo.last_check(conn, monitor_id)
    assert latest is not None
    assert latest["ok"] == 1
    assert latest["status_code"] == 200
    assert latest["latency_ms"] == 33.3


def test_health_summary_is_none_without_history(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    assert repo.health_summary(conn, monitor_id) == (None, None)


def test_health_summary_aggregates_uptime_and_latency(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    repo.record_check(conn, monitor_id, Probe(True, 200, 10.0, None))
    repo.record_check(conn, monitor_id, Probe(True, 200, 20.0, None))
    repo.record_check(conn, monitor_id, Probe(False, 500, 30.0, "HTTP 500"))
    repo.record_check(conn, monitor_id, Probe(False, None, None, "timeout"))
    uptime, latency = repo.health_summary(conn, monitor_id)
    assert uptime == 50.0
    assert latency == 20.0


def test_recent_checks_respects_limit_and_order(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    for _ in range(4):
        repo.record_check(conn, monitor_id, Probe(True, 200, 1.0, None))
    assert len(repo.recent_checks(conn, monitor_id, limit=3)) == 3


def test_list_monitors_filters_inactive(conn):
    active = repo.create_monitor(conn, "A", "https://a.example.com", 60)
    paused = repo.create_monitor(conn, "B", "https://b.example.com", 60)
    repo.update_monitor(conn, paused, {"active": 0})
    assert len(repo.list_monitors(conn)) == 2
    assert [r["id"] for r in repo.list_monitors(conn, include_inactive=False)] == [active]


def test_status_counts_with_no_monitors(conn):
    assert repo.status_counts(conn) == {"monitors": 0, "up": 0, "down": 0, "unknown": 0}


def test_foreign_key_cascade_removes_checks(conn):
    monitor_id = repo.create_monitor(conn, "Docs", "https://docs.example.com", 60)
    repo.record_check(conn, monitor_id, Probe(True, 200, 1.0, None))
    repo.delete_monitor(conn, monitor_id)
    remaining = conn.execute("SELECT COUNT(*) AS n FROM checks").fetchone()["n"]
    assert remaining == 0
