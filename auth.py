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
    role          TEXT    NOT NULL DEFAULT 'user',
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


# Keep an old DB without a `role` column upgradeable.
def _migrate_role_column() -> None:
    with db() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)")]
        if "role" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL "
                         "DEFAULT 'user'")
_migrate_role_column()


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
def create_user(username: str, password: str, email: str = "",
                role: str = "user"):
    """
    Register a new user.
    Returns (username, "") on success or (None, error_message) on failure.
    """
    username = username.strip()
    email = email.strip()
    role = role.strip().lower() or "user"
    if role not in ("user", "hr"):
        role = "user"

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
                """INSERT INTO users (username, email, password_hash, salt, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, email or None, pw_hash, salt, role),
            )
    except sqlite3.IntegrityError:
        return None, "That username or email is already registered. Try logging in!"

    return username, ""


def authenticate(username: str, password: str):
    """
    Verify credentials. Returns a dict {username, role} on success,
    else None. Uses constant-time comparison.
    """
    username = username.strip()
    with db() as conn:
        row = conn.execute(
            "SELECT password_hash, salt, role FROM users "
            "WHERE username = ?", (username,),
        ).fetchone()

    if row is None:
        return None
    attempt = _hash_password(password, row["salt"])
    if hmac.compare_digest(attempt, row["password_hash"]):
        return {"username": username, "role": row["role"] or "user"}
    return None


def seed_hr_account(username: str, password: str, email: str = ""):
    """
    Invite-only HR/recruiter account creation.
    Force-creates (or updates credentials of) an account with role='hr'.
    Returns the HR username string.
    """
    from sqlite3 import IntegrityError

    username = username.strip()
    salt = os.urandom(16).hex()
    pw_hash = _hash_password(password, salt)
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ?, role = 'hr' "
                "WHERE id = ?", (pw_hash, salt, existing["id"]))
        else:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, salt, role) "
                "VALUES (?, ?, ?, ?, 'hr')",
                (username, email.strip() or None, pw_hash, salt))
    return username


def user_exists(username: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    return row is not None


# Create tables on first import.
init_db()
