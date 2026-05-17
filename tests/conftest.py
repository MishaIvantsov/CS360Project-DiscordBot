import pytest

import database


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_tokens.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    database.init_db()
    return db_path
