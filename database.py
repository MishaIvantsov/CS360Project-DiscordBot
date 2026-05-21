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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                message_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                event_id   TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                is_closed  INTEGER NOT NULL DEFAULT 0,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                message_id   TEXT NOT NULL,
                discord_id   TEXT NOT NULL,
                vote         TEXT NOT NULL,
                PRIMARY KEY  (message_id, discord_id),
                FOREIGN KEY  (message_id) REFERENCES polls(message_id)
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_emails (
                discord_id   TEXT PRIMARY KEY,
                email        TEXT NOT NULL
            )
            """)
        conn.execute("""
             CREATE TABLE IF NOT EXISTS poll_attendees (
                 message_id  TEXT NOT NULL,
                 discord_id  TEXT NOT NULL,
                 PRIMARY KEY (message_id, discord_id),
                 FOREIGN KEY (message_id) REFERENCES polls(message_id)
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


def save_poll(message_id: str, channel_id: str, event_id: str, creator_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO polls (message_id, channel_id, event_id, creator_id) VALUES (?, ?, ?, ?)",
            (message_id, channel_id, event_id, creator_id),
        )
        conn.commit()


def get_poll(message_id: str) -> dict | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM polls WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    return dict(row) if row else None


def get_poll_by_event(event_id: str) -> dict | None:
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM polls
            WHERE event_id = ? AND is_closed = 0
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (event_id,),
        ).fetchone()
    return dict(row) if row else None


def close_poll(message_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            "UPDATE polls SET is_closed = 1 WHERE message_id = ?",
            (message_id,),
        )
        conn.commit()


def save_vote(message_id: str, discord_id: str, vote: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO votes (message_id, discord_id, vote)
            VALUES (?, ?, ?)
            ON CONFLICT(message_id, discord_id) DO UPDATE SET
                vote = excluded.vote
            """,
            (message_id, discord_id, vote),
        )
        conn.commit()


def get_vote(message_id: str, discord_id: str) -> str | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT vote FROM votes WHERE message_id = ? AND discord_id = ?",
            (message_id, discord_id),
        ).fetchone()
    return row["vote"] if row else None


def delete_vote(message_id: str, discord_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM votes WHERE message_id = ? AND discord_id = ?",
            (message_id, discord_id),
        )
        conn.commit()


def get_all_votes(message_id: str) -> list[dict]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT discord_id, vote FROM votes WHERE message_id = ?",
            (message_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_going_votes(message_id: str) -> list[str]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT discord_id FROM votes WHERE message_id = ? AND vote = 'going'",
            (message_id,),
        ).fetchall()
        removed_ids = [row["discord_id"] for row in rows]
        conn.execute("DELETE FROM votes WHERE message_id = ?", (message_id,))
        conn.commit()
    return removed_ids


def save_email(discord_id: str, email: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_emails (discord_id, email)
            VALUES (?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET email = excluded.email
            """,
            (discord_id, email),
        )
        conn.commit()


def get_email(discord_id: str) -> str | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT email FROM user_emails WHERE discord_id = ?",
            (discord_id,),
        ).fetchone()
    return row["email"] if row else None


def add_poll_attendee(message_id: str, discord_id: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO poll_attendees (message_id, discord_id)
            VALUES (?, ?)
            """,
            (message_id, discord_id),
        )
        conn.commit()


def is_poll_attendee(message_id: str, discord_id: str) -> bool:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM poll_attendees WHERE message_id = ? AND discord_id = ?",
            (message_id, discord_id),
        ).fetchone()
    return row is not None
