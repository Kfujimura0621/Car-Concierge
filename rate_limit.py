import os
import sqlite3
import time
import threading
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "rate_limit.db"

ACCOUNT_LIMIT = 5
ACCOUNT_WINDOW = 900

GLOBAL_LIMIT = 30
GLOBAL_WINDOW = 60

VERIFY_SLOTS = threading.BoundedSemaphore(2)


def reserve_attempt(username):
    now = time.time()
    account = username.casefold()

    with sqlite3.connect(DB, timeout=5) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                attempted_at REAL NOT NULL
            )
        """)

        conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            "DELETE FROM login_attempts WHERE attempted_at <= ?",
            (now - ACCOUNT_WINDOW,)
        )

        account_count = conn.execute("""
            SELECT COUNT(*) FROM login_attempts
            WHERE username = ? AND attempted_at > ?
        """, (account, now - ACCOUNT_WINDOW)).fetchone()[0]

        global_count = conn.execute("""
            SELECT COUNT(*) FROM login_attempts
            WHERE attempted_at > ?
        """, (now - GLOBAL_WINDOW,)).fetchone()[0]

        if account_count >= ACCOUNT_LIMIT:
            return False, "ACCOUNT_LIMIT"

        if global_count >= GLOBAL_LIMIT:
            return False, "GLOBAL_LIMIT"

        conn.execute("""
            INSERT INTO login_attempts
            (username, attempted_at)
            VALUES (?, ?)
        """, (account, now))

    os.chmod(DB, 0o600)
    return True, "OK"
