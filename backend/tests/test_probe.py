"""Unit tests for the HTTP probe wrapper."""

from __future__ import annotations

import httpx
import pytest

from app import probe as probe_module
from app.probe import Probe, probe


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_probe_marks_2xx_healthy(monkeypatch):
    monkeypatch.setattr(probe_module.httpx, "get", lambda *a, **k: _FakeResponse(200))
    result = probe("https://example.com")
    assert result.ok is True
    assert result.status_code == 200
    assert result.error is None
    assert result.latency_ms is not None and result.latency_ms >= 0


def test_probe_marks_3xx_healthy(monkeypatch):
    monkeypatch.setattr(probe_module.httpx, "get", lambda *a, **k: _FakeResponse(301))
    result = probe("https://example.com")
    assert result.ok is True
    assert result.status_code == 301


@pytest.mark.parametrize("code", [400, 404, 500, 503])
def test_probe_marks_4xx_5xx_unhealthy(monkeypatch, code):
    monkeypatch.setattr(probe_module.httpx, "get", lambda *a, **k: _FakeResponse(code))
    result = probe("https://example.com")
    assert result.ok is False
    assert result.status_code == code
    assert result.error == f"HTTP {code}"


def test_probe_reports_timeout_without_raising(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.TimeoutException("too slow")

    monkeypatch.setattr(probe_module.httpx, "get", boom)
    result = probe("https://example.com", timeout=2.5)
    assert result.ok is False
    assert result.status_code is None
    assert "timeout after 2.5s" in result.error


def test_probe_reports_transport_error_without_raising(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("dns failure")

    monkeypatch.setattr(probe_module.httpx, "get", boom)
    result = probe("https://nope.invalid")
    assert result.ok is False
    assert result.error is not None
    assert "ConnectError" in result.error


def test_probe_follows_redirects(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return _FakeResponse(200)

    monkeypatch.setattr(probe_module.httpx, "get", fake_get)
    probe("https://example.com")
    assert captured["follow_redirects"] is True


def test_probe_dataclass_is_immutable():
    result = Probe(True, 200, 12.5, None)
    with pytest.raises(Exception):
        result.ok = False  # type: ignore[misc]
