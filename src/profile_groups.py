import sys
from pathlib import Path

import pandas as pd

CLEAN = Path("data/processed/clean_products.parquet")
FEATURES = Path("data/processed/features.parquet")
GROUPS = Path("data/processed/peer_groups.parquet")


def main():
    # 1. The segment to look at comes from the command line
    segment = sys.argv[1]

    # 2. Join the clean data, the peer groups and the text flags by product_id
    clean = pd.read_parquet(CLEAN)
    groups = pd.read_parquet(GROUPS)[["product_id", "peer_group"]]
    feat = pd.read_parquet(FEATURES)
    flag_cols = [c for c in feat.columns if c.startswith("is_")]
    df = clean.merge(groups, on="product_id")
    df = df.merge(feat[["product_id"] + flag_cols], on="product_id")
    df = df[df["segment"] == segment]
    by_group = df.groupby("peer_group")

    # 3. One row per group: size, MRP range, ratings
    table = pd.DataFrame({
        "n": by_group.size(),
        "mrp_min": by_group["mrp"].min(),
        "mrp_med": by_group["mrp"].median(),
        "mrp_max": by_group["mrp"].max(),
        "rated%": by_group["has_rating"].mean() * 100,
        "rating": by_group["rating"].mean(),
        "cnt_med": by_group["rating_count"].median(),
    })
    print(segment)
    print(table.round(1).to_string())

    # 4. Share of each group whose name has each text flag (percent)
    shares = by_group[flag_cols].mean() * 100
    shares.columns = [c[3:7] for c in flag_cols]
    print(shares.round(0).astype(int).to_string())

    # 5. Five sample names from each group
    for number, group in by_group:
        print()
        print("Group", number)
        print(group["name"].sample(5, random_state=1).to_string(index=False))


if __name__ == "__main__":
    main()