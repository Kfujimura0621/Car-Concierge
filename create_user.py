import os
import sqlite3
import getpass
from pathlib import Path
from argon2 import PasswordHasher

os.umask(0o077)

DB = Path(__file__).resolve().parent / "users.db"
ph = PasswordHasher()

with sqlite3.connect(DB) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
                CHECK(role IN ('admin', 'user')),
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    username = input("ユーザー名: ").strip()
    role = input("権限 (admin/user): ").strip()

    if not username:
        raise SystemExit("ユーザー名を入力してください")

    if role not in ("admin", "user"):
        raise SystemExit("権限の指定が正しくありません")

    password = getpass.getpass("パスワード: ")
    confirm = getpass.getpass("パスワード確認: ")

    if password != confirm:
        raise SystemExit("パスワードが一致しません")

    if len(password) < 12:
        raise SystemExit("12文字以上にしてください")

    try:
        conn.execute(
            """
            INSERT INTO users
            (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username, ph.hash(password), role)
        )
    except sqlite3.IntegrityError:
        raise SystemExit("ユーザー名が既に存在します")

print("ユーザーを作成しました！")
print("ユーザー名:", username)
print("権限:", role)
