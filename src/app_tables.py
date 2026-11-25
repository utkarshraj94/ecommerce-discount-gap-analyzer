import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.business import MIN_GAP, MIN_GROUP_SIZE
from src.features import NUMERIC
from src.select_k import make_input

CLEAN = Path("data/processed/clean_products.parquet")
FEATURES = Path("data/processed/features.parquet")
GROUPS = Path("data/processed/peer_groups.parquet")
STATS = Path("data/processed/peer_stats.parquet")
CANDIDATES = Path("data/processed/candidates.parquet")
QUALITY = Path("data/processed/data_quality.json")
OUT = Path("data/processed/app.db")


def main():
    # 1. Products: one row per listing with its peer group, gap, flags and sentence
    clean = pd.read_parquet(CLEAN).drop(columns="file_discount")
    groups = pd.read_parquet(GROUPS)[["product_id", "peer_group", "peer_group_name"]]
    stats = pd.read_parquet(STATS)
    cands = pd.read_parquet(CANDIDATES)
    products = clean.merge(groups, on="product_id")
    products = products.merge(stats, on=["segment", "peer_group", "peer_group_name"])
    products = products.merge(cands, on="product_id")

    # 2. Peer groups: the group figures plus candidate count and low-confidence mark
    counts = products.groupby(["segment", "peer_group"])["is_candidate"].sum().reset_index(name="n_candidates")
    peer = stats.merge(counts, on=["segment", "peer_group"])
    peer["low_confidence"] = peer["n_listings"] < MIN_GROUP_SIZE

    # 3. Segments and brands: summaries for the overview and brand tabs
    segments = products.groupby("segment").agg(
        n_listings=("product_id", "size"),
        n_peer_groups=("peer_group", "nunique"),
        median_discount=("discount_pct", "median"),
        n_candidates=("is_candidate", "sum"),
    ).reset_index()
    brands = products.groupby("brand").agg(
        n_listings=("product_id", "size"),
        median_discount=("discount_pct", "median"),
        median_gap=("gap", "median"),
        n_candidates=("is_candidate", "sum"),
    ).reset_index()
    brands["candidate_share"] = brands["n_candidates"] / brands["n_listings"] * 100

    # 4. Data quality: the Phase 2 cleaning steps, and the Phase 6 counts
    with open(QUALITY) as f:
        quality = json.load(f)
    steps = pd.DataFrame(quality["steps"])
    checks = pd.DataFrame([
        {"check": "Listings kept", "value": len(products)},
        {"check": "Unrated listings", "value": quality["unrated_products"]},
        {"check": "Peer groups", "value": len(peer)},
        {"check": f"Peer groups under {MIN_GROUP_SIZE} listings", "value": int(peer["low_confidence"].sum())},
        {"check": f"Test candidates (gap of {MIN_GAP}+ points)", "value": int(products["is_candidate"].sum())},
        {"check": "Candidates to review first", "value": int((products["is_candidate"] & products["review_first"]).sum())},
    ])

    # 5. For placing a new product: each segment's scaling numbers and average rating,
    #    and each peer group's centre (the mean of its listings' clustering inputs)
    feat = pd.read_parquet(FEATURES).merge(groups[["product_id", "peer_group"]], on="product_id")
    scaling = feat.groupby("segment")[NUMERIC].agg(["mean", "std"])
    scaling.columns = [f"{col}_{stat}" for col, stat in scaling.columns]
    scaling["avg_rating"] = clean.groupby("segment")["rating"].mean()
    scaling = scaling.reset_index()
    centres = []
    for seg, group in feat.groupby("segment"):
        centre = make_input(group).groupby(group["peer_group"]).mean().reset_index()
        centre.insert(0, "segment", seg)
        centres.append(centre)
    centres = pd.concat(centres, ignore_index=True)

    # 6. Write every table to SQLite, replacing old versions
    tables = {
        "app_products": products,
        "app_peer_groups": peer,
        "app_segments": segments,
        "app_brands": brands,
        "app_data_quality": steps,
        "app_checks": checks,
        "app_scaling": scaling,
        "app_centres": centres,
    }
    conn = sqlite3.connect(OUT)
    for name, table in tables.items():
        table.to_sql(name, conn, if_exists="replace", index=False)

    # 7. Read the row counts back from the file, then close it
    for name in tables:
        n = pd.read_sql(f"SELECT COUNT(*) AS n FROM {name}", conn)["n"][0]
        print(name, n)
    conn.close()

    # 8. Checks: file size, missing values per column, and two tables to look at
    print("Saved", OUT, round(OUT.stat().st_size / 1e6, 1), "MB")
    missing = products.isna().sum()
    print("Columns with missing values:", missing[missing > 0].to_dict())
    print(segments.round(1).to_string(index=False))
    print(checks.to_string(index=False))


if __name__ == "__main__":
    main()