from __future__ import annotations
import json
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path):
    """Use a temporary file database for each test."""
    db_path = str(tmp_path / "test.db")
    with patch("database.DB_PATH", db_path):
        import database

        database.DB_PATH = db_path
        database.init_db()
        yield


# Sample token data
SAMPLE_TOKEN = {
    "token": "ya29.fake_access_token",
    "refresh_token": "1//fake_refresh_token",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "fake_client_id",
    "client_secret": "fake_client_secret",
    "scopes": ["https://www.googleapis.com/auth/calendar"],
}

DISCORD_ID = "123456789"

# init_db()


def test_init_db_creates_table():
    import database

    with database._get_connection() as conn:
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_tokens'"
        ).fetchone()
    assert result is not None


def test_init_db_is_idempotent():
    import database

    database.init_db()
    database.init_db()


# save_token()


def test_save_token_stores_token():
    import database

    database.save_token(DISCORD_ID, SAMPLE_TOKEN)

    with database._get_connection() as conn:
        row = conn.execute(
            "SELECT token FROM user_tokens WHERE discord_id = ?", (DISCORD_ID,)
        ).fetchone()

    assert row is not None
    assert json.loads(row["token"]) == SAMPLE_TOKEN


def test_save_token_overwrites_existing():
    import database

    database.save_token(DISCORD_ID, SAMPLE_TOKEN)

    updated_token = {**SAMPLE_TOKEN, "token": "ya29.new_access_token"}
    database.save_token(DISCORD_ID, updated_token)

    result = database.get_token(DISCORD_ID)
    assert result is not None
    assert result["token"] == "ya29.new_access_token"


def test_save_token_multiple_users():
    import database

    database.save_token("user_1", SAMPLE_TOKEN)
    database.save_token("user_2", {**SAMPLE_TOKEN, "token": "ya29.user2_token"})

    token1 = database.get_token("user_1")
    token2 = database.get_token("user_2")

    assert token1 is not None
    assert token2 is not None
    assert token1["token"] == "ya29.fake_access_token"
    assert token2["token"] == "ya29.user2_token"


# get_token()


def test_get_token_returns_token():
    import database

    database.save_token(DISCORD_ID, SAMPLE_TOKEN)
    result = database.get_token(DISCORD_ID)
    assert result == SAMPLE_TOKEN


def test_get_token_returns_none_when_not_found():
    import database

    result = database.get_token("nonexistent_user")
    assert result is None


def test_get_token_returns_correct_user():
    import database

    database.save_token("user_1", SAMPLE_TOKEN)
    database.save_token("user_2", {**SAMPLE_TOKEN, "token": "ya29.user2_token"})

    result = database.get_token("user_1")
    assert result is not None
    assert result["token"] == "ya29.fake_access_token"


# delete_token()


def test_delete_token_returns_true_on_success():
    import database

    database.save_token(DISCORD_ID, SAMPLE_TOKEN)
    result = database.delete_token(DISCORD_ID)
    assert result is True


def test_delete_token_removes_token():
    import database

    database.save_token(DISCORD_ID, SAMPLE_TOKEN)
    database.delete_token(DISCORD_ID)
    assert database.get_token(DISCORD_ID) is None


def test_delete_token_returns_false_when_not_found():
    import database

    result = database.delete_token("nonexistent_user")
    assert result is False


def test_delete_token_only_deletes_correct_user():
    import database

    database.save_token("user_1", SAMPLE_TOKEN)
    database.save_token("user_2", {**SAMPLE_TOKEN, "token": "ya29.user2_token"})

    database.delete_token("user_1")

    assert database.get_token("user_1") is None
    assert database.get_token("user_2") is not None
