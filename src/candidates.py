from pathlib import Path

import pandas as pd

from src.business import MIN_GAP, MIN_GROUP_SIZE

CLEAN = Path("data/processed/clean_products.parquet")
GAPS = Path("data/processed/gaps.parquet")
STATS = Path("data/processed/peer_stats.parquet")
ANOMALIES = Path("data/processed/anomaly_flags.parquet")
OUT = Path("data/processed/candidates.parquet")


# One plain sentence per listing, built from the same values as the flags
def why_flagged(row):
    discount = f"{row['discount_pct']:.0f}% off"
    median = f"{row['peer_median']:.0f}%"
    if row["is_candidate"]:
        text = (f"{discount} is {row['gap']:.1f} points above the {median} median of "
                f"{row['n_listings']} similar listings; the middle half of them give "
                f"{row['peer_q25']:.0f}% to {row['peer_q75']:.0f}% off.")
    elif row["gap"] > 0:
        text = (f"Not flagged: {discount} is {row['gap']:.1f} points above the {median} "
                f"peer median, under the {MIN_GAP}-point minimum.")
    else:
        text = f"Not flagged: {discount} is at or below the {median} peer median."
    if row["low_confidence"]:
        text += f" Low confidence: only {row['n_listings']} listings in this peer group."
    if row["review_first"]:
        text += " Review first: Phase 5 marked this listing as unusual."
    return text


def main():
    # 1. Join discount, gap, group figures and the Phase 5 flag by product_id
    clean = pd.read_parquet(CLEAN)[["product_id", "discount_pct"]]
    gaps = pd.read_parquet(GAPS)
    stats = pd.read_parquet(STATS)[["segment", "peer_group", "n_listings", "peer_q25", "peer_q75"]]
    flags = pd.read_parquet(ANOMALIES)[["product_id", "is_anomaly"]]
    df = clean.merge(gaps, on="product_id")
    df = df.merge(stats, on=["segment", "peer_group"])
    df = df.merge(flags, on="product_id")

    # 2. Round the gap to 1 decimal so the sentence and the flag always agree
    df["gap"] = df["gap"].round(1)

    # 3. The three flags
    df["is_candidate"] = (df["gap"] > 0) & (df["gap"] >= MIN_GAP)
    df["low_confidence"] = df["n_listings"] < MIN_GROUP_SIZE
    df["review_first"] = df["is_anomaly"]

    # 4. The sentence, then save
    df["why_flagged"] = df.apply(why_flagged, axis=1)
    out = df[["product_id", "gap", "is_candidate", "low_confidence", "review_first", "why_flagged"]]
    out.to_parquet(OUT, index=False)

    # 5. Checks: shape, missing values, flag counts and how they overlap
    print("Saved", OUT, out.shape)
    print("Missing values:", int(out.isna().sum().sum()))
    print(out[["is_candidate", "low_confidence", "review_first"]].sum().to_string())
    print(pd.crosstab(out["is_candidate"], out["low_confidence"]).to_string())
    print(pd.crosstab(out["is_candidate"], out["review_first"]).to_string())

    # 6. Five sentences to read
    for text in out.sample(5, random_state=1)["why_flagged"]:
        print("-", text)


if __name__ == "__main__":
    main()