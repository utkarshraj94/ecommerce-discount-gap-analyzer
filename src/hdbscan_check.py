from pathlib import Path

import pandas as pd
from sklearn.cluster import HDBSCAN
from sklearn.metrics import adjusted_rand_score

from src.select_k import make_input

FEATURES = Path("data/processed/features.parquet")
GROUPS = Path("data/processed/peer_groups.parquet")
OUT = Path("data/processed/hdbscan_comparison.csv")

MIN_CLUSTER_SIZE = 30


def main():
    # 1. Read the features and the KMeans peer groups
    feat = pd.read_parquet(FEATURES)
    groups = pd.read_parquet(GROUPS)[["product_id", "peer_group"]]
    feat = feat.merge(groups, on="product_id")

    # 2. Run HDBSCAN on each full segment
    rows = []
    for seg, group in feat.groupby("segment"):
        X = make_input(group)
        model = HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, copy=True)
        labels = pd.Series(model.fit_predict(X), index=group.index)

        # 3. A label of -1 means noise: HDBSCAN put the listing in no cluster
        found = labels[labels >= 0]
        sizes = found.value_counts()
        agreement = adjusted_rand_score(group.loc[found.index, "peer_group"], found)

        rows.append({
            "segment": seg,
            "kmeans_groups": group["peer_group"].nunique(),
            "hdbscan_clusters": found.nunique(),
            "noise_pct": (labels == -1).mean() * 100,
            "largest_cluster": int(sizes.max()),
            "smallest_cluster": int(sizes.min()),
            "agreement": agreement,
        })

    # 4. Save and show
    results = pd.DataFrame(rows)
    results.to_csv(OUT, index=False)
    print(results.round(2).to_string(index=False))


if __name__ == "__main__":
    main()