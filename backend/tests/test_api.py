"""API contract tests against a throwaway SQLite database."""

from __future__ import annotations

import pytest

from app import main as main_module
from app.probe import Probe


def _create(client, name="API", url="https://example.com", interval=300):
    response = client.post(
        "/api/monitors", json={"name": name, "url": url, "interval_s": interval}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health_endpoint(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["version"] == main_module.API_VERSION


def test_create_monitor_returns_full_object(client):
    body = _create(client)
    assert body["id"] >= 1
    assert body["name"] == "API"
    assert body["url"].startswith("https://example.com")
    assert body["active"] is True
    assert body["uptime_pct"] is None
    assert body["last_check"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "url": "https://example.com"},
        {"name": "x", "url": "not-a-url"},
        {"name": "x", "url": "https://example.com", "interval_s": 5},
        {"name": "x", "url": "https://example.com", "interval_s": 999999},
    ],
)
def test_create_monitor_rejects_invalid_payloads(client, payload):
    assert client.post("/api/monitors", json=payload).status_code == 422


def test_create_monitor_trims_whitespace_name(client):
    assert _create(client, name="  Padded  ")["name"] == "Padded"


def test_list_monitors_is_ordered_by_id(client):
    for name in ("one", "two", "three"):
        _create(client, name=name)
    names = [m["name"] for m in client.get("/api/monitors").json()]
    assert names == ["one", "two", "three"]


def test_list_monitors_can_exclude_inactive(client):
    monitor = _create(client, name="live")
    _create(client, name="paused")
    client.patch(f"/api/monitors/{monitor['id']}", json={"active": False})
    visible = client.get("/api/monitors", params={"include_inactive": False}).json()
    assert [m["name"] for m in visible] == ["paused"]


def test_get_single_monitor(client):
    created = _create(client)
    fetched = client.get(f"/api/monitors/{created['id']}").json()
    assert fetched["id"] == created["id"]


def test_get_missing_monitor_returns_404(client):
    assert client.get("/api/monitors/9999").status_code == 404


def test_patch_updates_only_supplied_fields(client):
    created = _create(client, name="orig", interval=300)
    updated = client.patch(
        f"/api/monitors/{created['id']}", json={"name": "renamed"}
    ).json()
    assert updated["name"] == "renamed"
    assert updated["interval_s"] == 300


def test_patch_missing_monitor_returns_404(client):
    assert client.patch("/api/monitors/9999", json={"name": "x"}).status_code == 404


def test_delete_monitor(client):
    created = _create(client)
    assert client.delete(f"/api/monitors/{created['id']}").status_code == 204
    assert client.get(f"/api/monitors/{created['id']}").status_code == 404


def test_delete_missing_monitor_returns_404(client):
    assert client.delete("/api/monitors/9999").status_code == 404


def test_run_check_records_a_successful_probe(client, monkeypatch):
    created = _create(client)
    monkeypatch.setattr(
        main_module, "probe", lambda url: Probe(True, 200, 42.5, None)
    )
    body = client.post(f"/api/monitors/{created['id']}/check").json()
    assert body["ok"] is True
    assert body["status_code"] == 200
    assert body["latency_ms"] == 42.5


def test_run_check_records_a_failed_probe(client, monkeypatch):
    created = _create(client)
    monkeypatch.setattr(
        main_module, "probe", lambda url: Probe(False, 503, 11.0, "HTTP 503")
    )
    body = client.post(f"/api/monitors/{created['id']}/check").json()
    assert body["ok"] is False
    assert body["error"] == "HTTP 503"


def test_run_check_on_missing_monitor_returns_404(client, monkeypatch):
    monkeypatch.setattr(main_module, "probe", lambda url: Probe(True, 200, 1.0, None))
    assert client.post("/api/monitors/9999/check").status_code == 404


def test_uptime_computed_from_check_history(client, monkeypatch):
    created = _create(client)
    results = [
        Probe(True, 200, 20.0, None),
        Probe(True, 200, 30.0, None),
        Probe(False, 500, 10.0, "HTTP 500"),
    ]
    for result in results:
        monkeypatch.setattr(main_module, "probe", lambda url, r=result: r)
        client.post(f"/api/monitors/{created['id']}/check")

    body = client.get(f"/api/monitors/{created['id']}").json()
    assert body["uptime_pct"] == pytest.approx(66.67, abs=0.01)
    assert body["avg_latency_ms"] == pytest.approx(20.0, abs=0.01)
    assert body["last_check"]["ok"] is False


def test_check_history_respects_limit(client, monkeypatch):
    created = _create(client)
    for _ in range(5):
        monkeypatch.setattr(main_module, "probe", lambda url: Probe(True, 200, 5.0, None))
        client.post(f"/api/monitors/{created['id']}/check")
    history = client.get(
        f"/api/monitors/{created['id']}/checks", params={"limit": 2}
    ).json()
    assert len(history) == 2


def test_check_history_on_missing_monitor_returns_404(client):
    assert client.get("/api/monitors/9999/checks").status_code == 404


def test_status_counts_reflect_latest_result(client, monkeypatch):
    healthy = _create(client, name="healthy")
    broken = _create(client, name="broken")
    _create(client, name="nobody-checked")

    monkeypatch.setattr(main_module, "probe", lambda url: Probe(True, 200, 8.0, None))
    client.post(f"/api/monitors/{healthy['id']}/check")

    monkeypatch.setattr(main_module, "probe", lambda url: Probe(False, 500, 8.0, "HTTP 500"))
    client.post(f"/api/monitors/{broken['id']}/check")

    body = client.get("/api/status").json()
    assert body == {"monitors": 3, "up": 1, "down": 1, "unknown": 1}


def test_badge_reports_unknown_before_any_check(client):
    created = _create(client)
    assert client.get(f"/api/monitors/{created['id']}/badge").text == "unknown"


def test_badge_reports_uptime_after_checks(client, monkeypatch):
    created = _create(client)
    monkeypatch.setattr(main_module, "probe", lambda url: Probe(True, 200, 3.0, None))
    client.post(f"/api/monitors/{created['id']}/check")
    badge = client.get(f"/api/monitors/{created['id']}/badge").text
    assert badge == "100.0%25%20uptime-brightgreen"


def test_badge_on_missing_monitor_returns_404(client):
    assert client.get("/api/monitors/9999/badge").status_code == 404


def test_deleting_monitor_cascades_checks(client, monkeypatch):
    created = _create(client)
    monkeypatch.setattr(main_module, "probe", lambda url: Probe(True, 200, 3.0, None))
    client.post(f"/api/monitors/{created['id']}/check")
    client.delete(f"/api/monitors/{created['id']}")
    assert client.get(f"/api/monitors/{created['id']}/checks").status_code == 404
