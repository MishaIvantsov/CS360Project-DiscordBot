from __future__ import annotations
import sqlite3
import json
import os

DB_PATH = os.getenv("DB_PATH", "tokens.db")


def _get_connection() -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the tokens table if it doesn't exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                discord_id TEXT PRIMARY KEY,
                token       TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()


def save_token(discord_id: str, token: dict) -> None:
    """Save or update a user's OAuth token."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_tokens (discord_id, token, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(discord_id) DO UPDATE SET
                token      = excluded.token,
                updated_at = CURRENT_TIMESTAMP
            """,
            (discord_id, json.dumps(token)),
        )
        conn.commit()


def get_token(discord_id: str) -> dict | None:
    """Retrieve a user's OAuth token, or None if not linked."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT token FROM user_tokens WHERE discord_id = ?",
            (discord_id,),
        ).fetchone()
    return json.loads(row["token"]) if row else None


def delete_token(discord_id: str) -> bool:
    """Delete a user's token. Returns True if deleted, False if not found."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM user_tokens WHERE discord_id = ?",
            (discord_id,),
        )
        conn.commit()
    return cursor.rowcount > 0
