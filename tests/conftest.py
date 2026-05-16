"""Shared fixtures for all test suites."""

import pytest


@pytest.fixture
def fake_credentials():
    """Stand-in Google OAuth credentials for tests that don't hit real Google."""
    # whatever you already have here — keep your current implementation
    ...


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolated database for each test. Reset between tests; never touches the real DB."""
    db_path = tmp_path / "test.db"

    # Point the database module at this temp file. Exact line depends on
    # how database.py resolves its path — see notes below.
    # monkeypatch.setattr("database.DB_PATH", str(db_path))

    from database import init_db

    init_db()
    yield db_path
