"""Shared fixtures: an isolated database and a pre-built test client."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def db_file(tmp_path, monkeypatch):
    """Point UPTIMEKIT_DB at a throwaway SQLite file for each test."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("UPTIMEKIT_DB", str(path))
    return path


@pytest.fixture()
def conn(db_file):
    """A connection to an initialised, empty database."""
    from app.db import init_db, session

    init_db()
    with session() as connection:
        yield connection


@pytest.fixture()
def client(db_file):
    """A TestClient bound to the throwaway database."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
