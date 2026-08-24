"""
BeeFriendly — auth.py
Sign-up / login backed by SQLite with real security practices:
- PBKDF2-HMAC-SHA256 password hashing (200k iterations) with per-user salt
- Unique usernames (case-insensitive) and emails via DB constraints
- Constant-time hash comparison (hmac.compare_digest)
No plaintext passwords are ever stored.
"""

import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = "beefriendly_users.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT    UNIQUE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


@contextmanager
def db():
    """Transactional connection helper."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(_SCHEMA)


# ----------------------------------------------------------------------
# Password hashing helpers
# ----------------------------------------------------------------------
def _hash_password(password: str, salt_hex: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    )
    return digest.hex()


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def create_user(username: str, password: str, email: str = ""):
    """
    Register a new user.
    Returns (username, "") on success or (None, error_message) on failure.
    """
    username = username.strip()
    email = email.strip()

    if len(username) < 3:
        return None, "Username must be at least 3 characters."
    if not username.replace("_", "").isalnum():
        return None, "Username can only contain letters, numbers and underscore."
    if len(password) < 6:
        return None, "Password must be at least 6 characters."
    if email and "@" not in email:
        return None, "Please enter a valid email address."

    salt = os.urandom(16).hex()
    pw_hash = _hash_password(password, salt)

    try:
        with db() as conn:
            conn.execute(
                """INSERT INTO users (username, email, password_hash, salt)
                   VALUES (?, ?, ?, ?)""",
                (username, email or None, pw_hash, salt),
            )
    except sqlite3.IntegrityError:
        return None, "That username or email is already registered. Try logging in!"

    return username, ""


def authenticate(username: str, password: str):
    """
    Verify credentials. Returns the username on success, else None.
    Uses constant-time comparison so timing attacks are impractical.
    """
    username = username.strip()
    with db() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return None
    attempt = _hash_password(password, row["salt"])
    if hmac.compare_digest(attempt, row["password_hash"]):
        return username
    return None


def user_exists(username: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    return row is not None


# Create tables on first import.
init_db()
