from pathlib import Path

import pandas as pd

CLEAN = Path("data/processed/clean_products.parquet")
GROUPS = Path("data/processed/peer_groups.parquet")
ANOMALIES = Path("data/processed/anomaly_flags.parquet")
OUT_STATS = Path("data/processed/peer_stats.parquet")
OUT_GAPS = Path("data/processed/gaps.parquet")

GROUP_COLS = ["segment", "peer_group", "peer_group_name"]


def main():
    # 1. Join each listing's discount to its peer group
    clean = pd.read_parquet(CLEAN)[["product_id", "segment", "discount_pct"]]
    groups = pd.read_parquet(GROUPS)[["product_id", "peer_group", "peer_group_name"]]
    df = clean.merge(groups, on="product_id")

    # 2. One row per peer group: listing count, 25th percentile, median, 75th percentile
    grouped = df.groupby(GROUP_COLS)["discount_pct"]
    stats = pd.DataFrame({
        "n_listings": grouped.size(),
        "peer_q25": grouped.quantile(0.25),
        "peer_median": grouped.median(),
        "peer_q75": grouped.quantile(0.75),
    }).reset_index()

    # 3. Gap: the listing's discount minus its peer group's median discount
    df = df.merge(stats[GROUP_COLS + ["peer_median"]], on=GROUP_COLS)
    df["gap"] = df["discount_pct"] - df["peer_median"]

    # 4. Save both tables
    stats.to_parquet(OUT_STATS, index=False)
    gaps = df[["product_id", "segment", "peer_group", "peer_median", "gap"]]
    gaps.to_parquet(OUT_GAPS, index=False)

    # 5. Checks: shapes, missing values, and the same gap as Phase 5
    print("Saved", OUT_STATS, stats.shape)
    print("Saved", OUT_GAPS, gaps.shape)
    print("Missing values:", int(gaps.isna().sum().sum()))
    old = pd.read_parquet(ANOMALIES)[["product_id", "gap"]]
    both = gaps.merge(old, on="product_id", suffixes=("", "_phase5"))
    print("Largest difference from the Phase 5 gap:", (both["gap"] - both["gap_phase5"]).abs().max())

    # 6. The peer groups, smallest first (names left out to keep it narrow)
    show = stats.drop(columns="peer_group_name").sort_values("n_listings")
    print(show.round(1).to_string(index=False))
    print(gaps["gap"].describe().round(1).to_string())


if __name__ == "__main__":
    main()