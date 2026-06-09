from __future__ import annotations
import asyncio
import logging
import os

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.auth.transport.requests import Request

from database import get_token, save_token

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080")
CLIENT_SECRETS_PATH = os.getenv("GOOGLE_CLIENT_SECRETS_PATH", "client_secrets.json")
REQUEST_TIMEOUT = 10  # seconds for Google OAuth network calls

# Store code verifiers in memory between auth URL generation and token exchange
_pending_verifiers: dict[str, str] = {}


def get_auth_url(discord_id: str) -> str:
    """Generate a Google OAuth authorization URL for the user."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=discord_id,
        prompt="consent",
    )
    # Store the code verifier so we can use it during token exchange
    if flow.code_verifier:
        _pending_verifiers[discord_id] = flow.code_verifier
    return auth_url


def exchange_code(discord_id: str, code: str) -> None:
    """Exchange an auth code for a token and save it to the database.

    Called from the OAuth callback server thread, so a hang here stalls the
    user's browser rather than the Discord loop -- but we still bound it with
    a timeout so the callback can't wait on Google indefinitely.
    """
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=discord_id,
    )
    # Restore the code verifier from when the auth URL was generated
    flow.code_verifier = _pending_verifiers.pop(discord_id, None)
    flow.fetch_token(code=code, timeout=REQUEST_TIMEOUT)
    token = flow.credentials
    assert isinstance(token, OAuth2Credentials)
    save_token(discord_id, _credentials_to_dict(token))


def get_credentials(discord_id: str) -> OAuth2Credentials | None:
    """Load a user's credentials from the DB, refreshing if expired.

    NOTE: this is synchronous and the refresh makes a blocking network call.
    Call it from async command handlers via get_credentials_async (below) so
    it never blocks the event loop.
    """
    token_data = get_token(discord_id)
    if token_data is None:
        return None

    creds = OAuth2Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            # Refresh token revoked/expired or a transport failure: treat as
            # "not authorized" so the caller can re-prompt instead of crashing.
            logger.warning("Token refresh failed for %s", discord_id, exc_info=True)
            return None
        save_token(discord_id, _credentials_to_dict(creds))

    return creds


async def get_credentials_async(discord_id: str) -> OAuth2Credentials | None:
    """Async wrapper: runs the blocking refresh off the event loop."""
    return await asyncio.to_thread(get_credentials, discord_id)


def _credentials_to_dict(creds: OAuth2Credentials) -> dict:
    """Convert a Credentials object to a dict for storage."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
