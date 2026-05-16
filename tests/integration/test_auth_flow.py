from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials as OAuth2Credentials

import auth


@pytest.fixture
def fake_credentials():
    """Stand-in for google.oauth2.credentials.Credentials.

    spec=OAuth2Credentials makes isinstance() checks in auth.py pass.
    """
    creds = MagicMock(spec=OAuth2Credentials)
    creds.token = "fake-access"
    creds.refresh_token = "fake-refresh"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "fake-client-id"
    creds.client_secret = "fake-client-secret"
    creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    creds.expired = False
    return creds


def test_exchange_code_persists_token(fake_credentials, tmp_db):
    """exchange_code() stores the resulting token in the database."""
    discord_id = "123456789"

    # Pretend get_auth_url ran first and stashed a verifier
    auth._pending_verifiers[discord_id] = "fake-verifier"

    mock_flow = MagicMock()
    mock_flow.credentials = fake_credentials

    with patch.object(auth.Flow, "from_client_secrets_file", return_value=mock_flow):
        auth.exchange_code(discord_id=discord_id, code="abc123")

    # The flow was driven correctly
    mock_flow.fetch_token.assert_called_once_with(code="abc123")

    # And the token landed in the DB
    stored = auth.get_token(discord_id)
    assert stored["token"] == "fake-access"
    assert stored["refresh_token"] == "fake-refresh"
    assert stored["scopes"] == ["https://www.googleapis.com/auth/calendar"]


def test_get_credentials_refreshes_when_expired(fake_credentials, tmp_db):
    """An expired access token triggers a refresh and re-saves the new token."""
    discord_id = "123456789"
    fake_credentials.expired = True

    # Seed the DB with a token that will be 'expired'
    from database import save_token

    save_token(
        discord_id,
        {
            "token": "old-access",
            "refresh_token": "fake-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        },
    )

    with patch.object(auth, "OAuth2Credentials", return_value=fake_credentials):
        result = auth.get_credentials(discord_id)

    fake_credentials.refresh.assert_called_once()
    assert result is fake_credentials


def test_get_credentials_returns_none_for_unlinked_user(tmp_db):
    """No DB row → no credentials, no errors."""
    assert auth.get_credentials("never-linked-user") is None
