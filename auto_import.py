from pathlib import Path
from datetime import datetime
import pandas as pd

BASE = Path("cars_12models_v2.csv")
NEW = Path("new_cars.csv")
OUTPUT = Path("cars_12models_updated.csv")

MODELS = [
    "ハスラー", "スペーシア", "ワゴンR",
    "アクア", "プリウス", "シエンタ",
    "ノート", "セレナ", "ルークス",
    "N-BOX", "N-WGN", "N-ONE"
]

REQUIRED = [
    "target_model", "model", "year_ce",
    "mileage_wan_km", "price_vehicle",
    "transmission"
]

def load_csv(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

def classify(value):
    value = str(value).upper().strip()
    if "CVT" in value or "AT" in value:
        return "AT"
    if "MT" in value:
        return "MT"
    return "不明"

def main():
    if not BASE.exists():
        raise SystemExit("基本データがありません")

    base = load_csv(BASE)
    new = load_csv(NEW)

    if base.empty:
        raise SystemExit("基本データが空です")

    if not new.empty:
        missing = [c for c in REQUIRED if c not in new.columns]
        if missing:
            raise SystemExit(f"必要な列がありません: {missing}")

        new = new[new["target_model"].isin(MODELS)].copy()

        for col in ["year_ce", "mileage_wan_km", "price_vehicle"]:
            new[col] = pd.to_numeric(new[col], errors="coerce")

        new = new.dropna(subset=[
            "year_ce", "mileage_wan_km", "price_vehicle"
        ])

        new = new[
            new["year_ce"].between(1990, datetime.now().year + 1)
            & new["mileage_wan_km"].between(0, 50)
            & new["price_vehicle"].between(0.1, 10000)
        ].copy()

        new["transmission_type"] = new["transmission"].apply(classify)

    # 元データの分類は保持する
    if "transmission_type" not in base.columns:
        base["transmission_type"] = base["transmission"].apply(classify)

    combined = pd.concat([base, new], ignore_index=True)

    # URLの表記を統一
    if "source_url" not in combined.columns:
        combined["source_url"] = pd.NA

    if "link" in combined.columns:
        combined["source_url"] = combined["source_url"].fillna(
            combined["link"]
        )

    combined["source_url"] = (
        combined["source_url"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    # URLのある車両はURLで重複排除
    has_url = combined["source_url"].notna()

    with_url = combined[has_url].drop_duplicates(
        subset=["source_url"], keep="last"
    )

    without_url = combined[~has_url]

    combined = pd.concat(
        [without_url, with_url],
        ignore_index=True
    )

    keys = [
        "target_model", "model", "year_ce",
        "mileage_wan_km", "price_vehicle",
        "transmission_type"
    ]

    combined = combined.drop_duplicates(
        subset=keys, keep="last"
    )

    tmp = OUTPUT.with_suffix(".tmp")
    combined.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(OUTPUT)

    print("\n=== インポート完了 ===")
    print("基本データ:", len(base), "台")
    print("追加候補:", len(new), "台")
    print("統合後:", len(combined), "台")
    print("保存先:", OUTPUT)

    print("\n=== 車種別台数 ===")
    print(
        combined["target_model"]
        .value_counts()
        .reindex(MODELS, fill_value=0)
        .to_string()
    )

if __name__ == "__main__":
    main()
