import sqlite3
import logging
import time
from pathlib import Path

import streamlit as st
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

BASE = Path(__file__).resolve().parent
DB = BASE / "users.db"

ph = PasswordHasher()
DUMMY_HASH = ph.hash("dummy-password-not-for-login")

logger = logging.getLogger("car_concierge.auth")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(BASE / "auth.log")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s"
    ))
    logger.addHandler(handler)

from rate_limit import reserve_attempt, VERIFY_SLOTS


def authenticate(username, password):
    if not VERIFY_SLOTS.acquire(blocking=False):
        logger.warning("LOGIN_BUSY")
        return None

    try:
        allowed, reason = reserve_attempt(username)

        if not allowed:
            logger.warning(
                "LOGIN_BLOCKED user=%r reason=%s",
                username, reason
            )
            return None

        return verify_credentials(username, password)

    except sqlite3.Error:
        logger.exception("LOGIN_DATABASE_ERROR")
        return None

    finally:
        VERIFY_SLOTS.release()


def verify_credentials(username, password):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row

        user = conn.execute(
            """
            SELECT id, username, password_hash, role, enabled
            FROM users WHERE username = ?
            """,
            (username,)
        ).fetchone()

    try:
        valid = ph.verify(
            user["password_hash"] if user else DUMMY_HASH,
            password
        )
    except (VerificationError, InvalidHashError):
        valid = False

    if not user or not user["enabled"] or not valid:
        logger.warning("LOGIN_FAILED user=%r", username)
        return None

    logger.info("LOGIN_SUCCESS user=%r", username)

    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"]
    }

def require_login():
    current = st.session_state.get("auth_user")

    if current:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, username, role, enabled
                FROM users WHERE id = ?
                """,
                (current["id"],)
            ).fetchone()

        if row and row["enabled"]:
            if time.time() - st.session_state.get(
                "login_time", 0
            ) < 28800:
                current = {
                    "id": row["id"],
                    "username": row["username"],
                    "role": row["role"]
                }
                st.session_state["auth_user"] = current
                return current

        st.session_state.pop("auth_user", None)

    st.title("🚗 Car Concierge")
    st.caption("中古車販売価格推定システム")

    _, center, _ = st.columns([1, 2, 1])

    with center:
        with st.form("login"):
            st.subheader("ログイン")

            username = st.text_input(
                "ユーザー名", max_chars=128
            )
            password = st.text_input(
                "パスワード",
                type="password",
                max_chars=256
            )

            submitted = st.form_submit_button(
                "ログイン", type="primary"
            )

        if submitted:
            if time.time() < st.session_state.get(
                "retry_after", 0
            ):
                st.error("少し時間をおいて再試行してください。")
                st.stop()

            user = authenticate(username.strip(), password)

            if user:
                st.session_state["auth_user"] = user
                st.session_state["login_time"] = time.time()
                st.session_state["retry_after"] = 0
                st.rerun()
            else:
                st.session_state["retry_after"] = time.time() + 3
                st.error("ユーザー名またはパスワードが違います。")

    st.stop()

def logout():
    user = st.session_state.get("auth_user")

    if user:
        logger.info("LOGOUT user=%r", user["username"])

    st.session_state.clear()
    st.rerun()

def require_admin(user):
    if user["role"] != "admin":
        st.error("管理者権限が必要です。")
        st.stop()
