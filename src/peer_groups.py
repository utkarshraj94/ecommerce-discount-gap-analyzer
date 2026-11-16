from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans

from src.select_k import make_input

FEATURES = Path("data/processed/features.parquet")
CLEAN = Path("data/processed/clean_products.parquet")
FINAL = Path("data/processed/final_k.csv")
NAMES = Path("data/processed/peer_group_names.csv")
OUT = Path("data/processed/peer_groups.parquet")


def main():
    # 1. Read the features, the MRP and the chosen k for each segment
    feat = pd.read_parquet(FEATURES)
    mrp = pd.read_parquet(CLEAN)[["product_id", "mrp"]]
    feat = feat.merge(mrp, on="product_id")
    final_k = pd.read_csv(FINAL)

    # 2. Cluster each segment with its chosen k
    parts = []
    for _, row in final_k.iterrows():
        seg = row["segment"]
        k = int(row["k"])
        group = feat[feat["segment"] == seg].copy()
        X = make_input(group)
        group["raw"] = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)

        # 3. Number the groups 1, 2, 3... from the lowest to the highest median MRP
        median_mrp = group.groupby("raw")["mrp"].median()
        order = median_mrp.rank(method="first").astype(int)
        group["peer_group"] = group["raw"].map(order)
        parts.append(group[["product_id", "segment", "peer_group"]])

    # 4. Put the segments together
    result = pd.concat(parts, ignore_index=True)

    # 5. Add the hand-written name of each group
    names = pd.read_csv(NAMES)
    result = result.merge(names, on=["segment", "peer_group"], how="left")

    # 6. Save
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUT, index=False)

    # 7. Quick checks
    print("Saved", OUT, result.shape)
    print("Missing values:", int(result.isna().sum().sum()))
    print("Duplicate product_ids:", int(result["product_id"].duplicated().sum()))
    print("Groups:", result.groupby(["segment", "peer_group"]).ngroups)
    print("Names in the file:", len(names))
    print(result.groupby("segment")["peer_group_name"].nunique())


if __name__ == "__main__":
    main()