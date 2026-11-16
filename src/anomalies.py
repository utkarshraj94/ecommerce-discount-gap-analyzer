from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

CLEAN = Path("data/processed/clean_products.parquet")
FEATURES = Path("data/processed/features.parquet")
GROUPS = Path("data/processed/peer_groups.parquet")
OUT = Path("data/processed/anomaly_flags.parquet")

CONTAMINATION = 0.01
INPUT_COLS = ["discount_pct", "log_mrp", "rating_filled", "gap"]


def main():
    # 1. Join the clean data, the features and the peer groups by product_id
    clean = pd.read_parquet(CLEAN)
    feat = pd.read_parquet(FEATURES)[["product_id", "log_mrp", "rating_filled"]]
    groups = pd.read_parquet(GROUPS)[["product_id", "peer_group", "peer_group_name"]]
    df = clean.merge(feat, on="product_id").merge(groups, on="product_id")

    # 2. Gap from peers: the listing's discount minus its peer group's median discount
    df["peer_median"] = df.groupby(["segment", "peer_group"])["discount_pct"].transform("median")
    df["gap"] = df["discount_pct"] - df["peer_median"]

    # 3. Flag the most unusual 1% inside each segment
    df["anomaly_score"] = 0.0
    df["is_anomaly"] = False
    for seg, group in df.groupby("segment"):
        model = IsolationForest(contamination=CONTAMINATION, random_state=42)
        labels = model.fit_predict(group[INPUT_COLS])
        df.loc[group.index, "is_anomaly"] = labels == -1
        df.loc[group.index, "anomaly_score"] = model.score_samples(group[INPUT_COLS])

    # 4. Save only the flags, keyed by product_id
    flags = df[["product_id", "segment", "peer_group", "gap", "anomaly_score", "is_anomaly"]]
    flags.to_parquet(OUT, index=False)

    # 5. Quick checks
    print("Saved", OUT, flags.shape)
    print("Missing values:", int(flags.isna().sum().sum()))
    print(df.groupby("segment")["is_anomaly"].agg(["sum", "size"]).to_string())

    # 6. The 12 most unusual listings, to look at by hand
    show = ["name", "mrp", "discount_pct", "peer_median", "gap", "rating"]
    print(df[df["is_anomaly"]].sort_values("anomaly_score").head(12)[show].round(1).to_string())


if __name__ == "__main__":
    main()