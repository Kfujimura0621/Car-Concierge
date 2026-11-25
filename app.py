import numpy as np
import pandas as pd
import streamlit as st
from auth import require_login, logout

st.set_page_config(
    page_title="Car Concierge",
    page_icon="🚗",
    layout="wide"
)

ALL_MODELS = [
    "ハスラー", "スペーシア", "ワゴンR",
    "アクア", "プリウス", "シエンタ",
    "ノート", "セレナ", "ルークス",
    "N-BOX", "N-WGN", "N-ONE"
]

def classify_transmission(value):
    value = str(value).upper().strip()

    if "CVT" in value or "AT" in value:
        return "AT"
    if "MT" in value:
        return "MT"
    return "不明"


@st.cache_data
def load_data():
    df = pd.read_csv("cars_12models_updated.csv")
    for col in ["year_ce", "mileage_wan_km",
                "price_vehicle", "price_total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["transmission_type"] = (
        df["transmission"].apply(classify_transmission)
    )
    return df.dropna(
        subset=["target_model", "year_ce",
                "mileage_wan_km", "price_vehicle"]
    )

def estimate_price(df, model, year, mileage, transmission):
    cars = df[df["target_model"] == model].copy()
    if transmission != "指定なし":
        cars = cars[cars["transmission_type"] == transmission]

    if cars.empty:
        return None, None

    mileage_wan = mileage / 10000
    cars["distance"] = (
        abs(cars["year_ce"] - year) * 2
        + abs(cars["mileage_wan_km"] - mileage_wan)
    )
    similar = cars.nsmallest(5, "distance")
    weights = 1 / (similar["distance"] + 1)

    price = np.average(similar["price_vehicle"], weights=weights)
    return price, similar

current_user = require_login()

is_admin = current_user["role"] == "admin"

df = load_data()

st.sidebar.title("🚗 Car Concierge")

st.sidebar.write(f"ユーザー：{current_user['username']}")
st.sidebar.caption(
    "権限：管理者" if is_admin else "権限：一般ユーザー"
)

if st.sidebar.button("ログアウト"):
    logout()

st.sidebar.divider()
menus = [
    "販売価格推定",
    "価格分析",
    "車両データ管理"
]

if is_admin:
    menus.append("車両登録")

page = st.sidebar.radio(
    "メニュー",
    menus
)
st.sidebar.divider()
st.sidebar.metric("登録車両数", f"{len(df)}台")
st.sidebar.metric("データ保有車種", f"{df['target_model'].nunique()}車種")

if page == "販売価格推定":
    st.title("販売価格推定")
    st.write("車両情報から中古車の販売価格を推定します。")

    with st.form("estimate"):
        col1, col2, col3 = st.columns(3)
        with col1:
            model = st.selectbox("車種", ALL_MODELS)
        with col2:
            year = st.number_input(
                "年式", 1990, 2026, 2018
            )
        with col3:
            mileage = st.number_input(
                "走行距離（km）", 0, 500000, 3000, 1000
            )
        transmission = st.radio(
            "トランスミッション",
            ["指定なし", "AT", "MT"],
            horizontal=True
        )
        color = st.selectbox(
            "ボディカラー",
            [
                "指定なし",
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
        )

        submitted = st.form_submit_button(
            "販売価格を推定", type="primary"
        )

    if submitted:
        price, similar = estimate_price(
            df, model, year, mileage, transmission
        )
        if price is None:
            st.error("この車種のデータはまだありません。")
        else:
            st.metric(
                "推定車両本体販売価格",
                f"{price:.1f}万円"
            )
            st.caption(
                f"参考車両：{len(similar)}台 "
                "※実験用データによる推定値"
            )
            if len(df[df["target_model"] == model]) < 10:
                st.warning("データ数が少ないため推定精度に注意してください。")
            st.dataframe(
                similar[[
                    "model", "year_ce",
                    "mileage_wan_km", "price_vehicle"
                ]],
                hide_index=True,
                use_container_width=True
            )

elif page == "価格分析":
    st.title("価格分析")
    model = st.selectbox(
        "分析する車種",
        sorted(df["target_model"].unique())
    )
    cars = df[df["target_model"] == model]

    c1, c2, c3 = st.columns(3)
    c1.metric("登録台数", f"{len(cars)}台")
    c2.metric("平均車両本体価格", f"{cars['price_vehicle'].mean():.1f}万円")
    c3.metric("中央値", f"{cars['price_vehicle'].median():.1f}万円")

    st.subheader("年式別の平均販売価格")
    yearly = cars.groupby("year_ce")["price_vehicle"].mean()
    st.line_chart(yearly)

    st.subheader("走行距離と販売価格")
    st.scatter_chart(
        cars,
        x="mileage_wan_km",
        y="price_vehicle"
    )

elif page == "車両データ管理":
    st.title("車両データ管理")
    st.caption("現在はCSVの閲覧・検索機能です。データ編集・自動更新は未実装です。")

    selected = st.multiselect(
        "車種で絞り込み",
        sorted(df["target_model"].unique()),
        default=sorted(df["target_model"].unique())
    )

    filtered = df[df["target_model"].isin(selected)]

    keyword = st.text_input("車両情報を検索")
    if keyword:
        filtered = filtered[
            filtered["model"].astype(str).str.contains(
                keyword, case=False, regex=False, na=False
            )
        ]

    st.metric("検索結果", f"{len(filtered)}台")
    st.dataframe(
        filtered[[
            "target_model", "model", "year_ce",
            "mileage_wan_km", "price_vehicle",
            "price_total", "prefecture"
        ]],
        hide_index=True,
        use_container_width=True
    )

    if is_admin:
        st.download_button(
            "表示中のデータをCSVでダウンロード",
            filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name="car_concierge_export.csv",
            mime="text/csv"
        )


elif page == "車両登録":
    from admin_cars import render_registration
    render_registration()
