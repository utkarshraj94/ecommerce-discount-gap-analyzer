from pathlib import Path

import numpy as np
import pandas as pd

CLEAN = Path("data/processed/clean_products.parquet")
OUT = Path("data/processed/features.parquet")

# Column name -> word to look for in the product name
FLAGS = {
    "is_cotton": "cotton",
    "is_silk": "silk",
    "is_georgette": "georgette",
    "is_printed": "printed",
    "is_embroidered": "embroidered",
    "is_solid": "solid",
    "is_striped": "striped",
    "is_casual": "casual",
    "is_formal": "formal",
    "is_pack": "pack of",
}

# The number columns that get a scaled copy
NUMERIC = ["log_mrp", "rating_filled", "log_rating_count"]


def main():
    # 1. Read the clean data
    df = pd.read_parquet(CLEAN)

    # 2. Start the features table with the two key columns
    feat = df[["product_id", "segment"]].copy()

    # 3. Price tier: log of the MRP
    feat["log_mrp"] = np.log1p(df["mrp"])

    # 4. Rating: 1 if rated, otherwise 0
    feat["has_rating"] = df["has_rating"].astype(int)

    # 5. Rating with gaps filled by the segment's average rating
    seg_avg = df.groupby("segment")["rating"].mean()
    fill_values = df["segment"].map(seg_avg)
    feat["rating_filled"] = df["rating"].fillna(fill_values)

    # 6. How established the listing is: log of the rating count
    feat["log_rating_count"] = np.log1p(df["rating_count"])

    # 7. Text flags: 1 if the product name contains the word
    name = df["name"].str.lower()
    for col, word in FLAGS.items():
        feat[col] = name.str.contains(word, regex=False).astype(int)

    # 8. Scaled copies: (value - segment average) / segment spread
    for col in NUMERIC:
        group = feat.groupby("segment")[col]
        feat[col + "_z"] = (feat[col] - group.transform("mean")) / group.transform("std")

    # 9. Save the features file
    OUT.parent.mkdir(parents=True, exist_ok=True)
    feat.to_parquet(OUT, index=False)

    # 10. Quick checks
    print("Saved", OUT, feat.shape)
    print(list(feat.columns))
    print("Missing values:", int(feat.isna().sum().sum()))
    print("Duplicate product_ids:", int(feat["product_id"].duplicated().sum()))
    z_cols = [col + "_z" for col in NUMERIC]
    print(feat.groupby("segment")[z_cols].mean().round(2))
    print(feat.groupby("segment")[z_cols].std().round(2))


if __name__ == "__main__":
    main()