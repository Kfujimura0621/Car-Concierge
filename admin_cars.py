import fcntl
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from auth import require_login, require_admin
from auto_import import main as run_import

BASE = Path(__file__).resolve().parent
CSV = BASE / "new_cars.csv"
LOCK = BASE / "cars_update.lock"

logger = logging.getLogger("car_concierge.auth")

MODELS = [
    "ハスラー", "スペーシア", "ワゴンR",
    "アクア", "プリウス", "シエンタ",
    "ノート", "セレナ", "ルークス",
    "N-BOX", "N-WGN", "N-ONE"
]

COLORS = [
    "不明",
    "ホワイト",
    "パールホワイト",
    "ブラック",
    "シルバー",
    "グレー",
    "ブルー",
    "レッド",
    "ブラウン",
    "グリーン",
    "イエロー",
    "その他"
]

def render_registration():
    user = require_login()
    require_admin(user)

    st.title("車両登録")
    st.caption("管理者専用の車両データ登録画面")

    if st.session_state.pop("registration_success", False):
        st.success("車両を登録し、査定データを更新しました！")

    with st.form("admin_register"):
        c1, c2, c3 = st.columns(3)

        with c1:
            model = st.selectbox("車種", MODELS)

            year = st.number_input(
                "年式", 1990, datetime.now().year + 1, 2022
            )

            mileage = st.number_input(
                "走行距離（km）",
                0, 500000, 30000, 1000
            )

        with c2:
            price = st.number_input(
                "車両本体価格（万円）",
                min_value=0.1,
                max_value=10000.0,
                value=100.0,
                step=1.0
            )

            transmission = st.selectbox(
                "トランスミッション",
                ["CVT", "AT", "MT", "不明"]
            )

            color = st.selectbox(
                "ボディカラー", COLORS
            )

        with c3:
            grade = st.text_input(
                "グレード", max_chars=100
            )

            repair = st.selectbox(
                "修復歴",
                ["なし", "あり", "不明"]
            )

            url = st.text_input(
                "掲載元URL", max_chars=2048
            )

        submitted = st.form_submit_button(
            "車両を登録", type="primary"
        )

    if submitted:
        user = require_login()
        require_admin(user)

        url = url.strip()
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            st.error("有効な掲載元URLを入力してください。")

        else:
            try:
                with LOCK.open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)

                    existing = (
                        pd.read_csv(CSV)
                        if CSV.exists()
                        else pd.DataFrame()
                    )

                    current = pd.read_csv(
                        BASE / "cars_12models_updated.csv"
                    )

                    urls = set()

                    for data in (existing, current):
                        for col in ("source_url", "link"):
                            if col in data.columns:
                                urls.update(
                                    data[col].dropna()
                                    .astype(str).str.strip()
                                )

                    if url in urls:
                        st.warning("この掲載URLは登録済みです。")

                    else:
                        row = pd.DataFrame([{
                            "target_model": model,
                            "model": f"{model} {grade}".strip(),
                            "year_ce": year,
                            "mileage_wan_km": mileage / 10000,
                            "price_vehicle": price,
                            "transmission": transmission,
                            "color": color,
                            "repair_history": repair,
                            "source_url": url,
                            "registered_at": datetime.now().isoformat()
                        }])

                        updated = pd.concat(
                            [existing, row],
                            ignore_index=True
                        )

                        tmp = CSV.with_suffix(".tmp")

                        updated.to_csv(
                            tmp,
                            index=False,
                            encoding="utf-8-sig"
                        )

                        tmp.replace(CSV)

                        logger.info(
                            "CAR_REGISTER user=%r model=%r",
                            user["username"], model
                        )

                        try:
                            run_import()
                        except (Exception, SystemExit):
                            logger.exception("IMPORT_FAILED")
                            st.warning(
                                "車両は保存されましたが、"
                                "査定データの更新に失敗しました。"
                            )
                        else:
                            st.cache_data.clear()
                            st.session_state[
                                "registration_success"
                            ] = True
                            st.rerun()

            except Exception:
                logger.exception("REGISTER_FAILED")
                st.error("登録処理に失敗しました。")

    st.divider()
    st.subheader("登録済みの追加車両")

    if CSV.exists():
        cars = pd.read_csv(CSV)

        st.metric("追加登録台数", len(cars))

        st.dataframe(
            cars,
            hide_index=True,
            use_container_width=True
        )

    else:
        st.info("追加登録された車両はありません。")
