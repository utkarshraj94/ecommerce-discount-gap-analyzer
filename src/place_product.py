"""Place new products in their peer groups and work out their discount gap.

A product goes to the nearest peer-group centre, using the same inputs as the
clustering (src/features.py and src/select_k.py), so no model is refitted.
"""

import numpy as np
import pandas as pd

from src.business import MIN_GAP, MIN_GROUP_SIZE
from src.features import FLAGS, NUMERIC

CAP = 3  # the same cap on scaled numbers as in src/select_k.py
STATS_COLS = ["segment", "peer_group", "peer_group_name", "n_listings",
              "peer_q25", "peer_median", "peer_q75"]
RESULT_COLS = STATS_COLS[1:] + ["discount_pct", "gap", "flagged", "low_confidence", "review_first"]


# 1. Clustering inputs for new products, built exactly like the catalogue's
def make_features(products, scaling):
    df = products.reset_index(drop=True).merge(scaling, on="segment", how="left")
    values = {
        "log_mrp": np.log1p(df["mrp"]),
        "rating_filled": df["rating"].fillna(df["avg_rating"]),
        "log_rating_count": np.log1p(df["rating_count"].fillna(0)),
    }
    feat = pd.DataFrame(index=df.index)
    for col in NUMERIC:
        scaled = (values[col] - df[col + "_mean"]) / df[col + "_std"]
        feat[col + "_z"] = scaled.clip(-CAP, CAP)
    feat["has_rating"] = df["rating"].notna().astype(int)
    name = df["name"].str.lower()
    for col, word in FLAGS.items():
        feat[col] = name.str.contains(word, regex=False).astype(int)
    return feat


# 2. The nearest peer-group centre in the product's own segment
def nearest_group(feat, segments, centres):
    groups = pd.Series(0, index=feat.index)
    for segment, rows in feat.groupby(segments.to_numpy()):
        seg_centres = centres[centres["segment"] == segment]
        points = rows.to_numpy()[:, None, :]
        centre_points = seg_centres[feat.columns].to_numpy()[None, :, :]
        distances = ((points - centre_points) ** 2).sum(axis=2)
        groups[rows.index] = seg_centres["peer_group"].to_numpy()[distances.argmin(axis=1)]
    return groups.astype(int)


# 3. Discount, peer group, gap and flags, with the same rules as the catalogue
def place_products(products, scaling, centres, peer_groups, min_gap=MIN_GAP):
    df = products.reset_index(drop=True).drop(columns=RESULT_COLS, errors="ignore")
    df["discount_pct"] = (1 - df["price"] / df["mrp"]) * 100
    feat = make_features(df, scaling)
    df["peer_group"] = nearest_group(feat, df["segment"], centres)
    df = df.merge(peer_groups[STATS_COLS], on=["segment", "peer_group"], how="left")
    df["gap"] = (df["discount_pct"] - df["peer_median"]).round(1)
    df["flagged"] = (df["gap"] > 0) & (df["gap"] >= min_gap)
    df["low_confidence"] = (df["n_listings"] < MIN_GROUP_SIZE).astype(int)
    df["review_first"] = 0  # the unusual-listing check needs the whole catalogue
    return df
