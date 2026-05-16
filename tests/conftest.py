"""Shared fixtures for all test suites."""

import pytest


@pytest.fixture
def fake_credentials():
    """Stand-in Google OAuth credentials for tests that don't hit real Google."""
    # whatever you already have here — keep your current implementation
    ...


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect the database module to a per-test temp file. Auto-applied to every test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("database.DB_PATH", str(db_path))

    from database import init_db

    init_db()
    yield db_path
