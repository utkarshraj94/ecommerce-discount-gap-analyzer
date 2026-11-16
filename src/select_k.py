from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

FEATURES = Path("data/processed/features.parquet")
OUT = Path("data/processed/k_selection.csv")

K_VALUES = range(3, 11)
Z_COLS = ["log_mrp_z", "rating_filled_z", "log_rating_count_z"]
CAP = 3


def make_input(group):
    # Columns used for clustering: capped scaled numbers, has_rating and the text flags
    flag_cols = [c for c in group.columns if c.startswith("is_")]
    X = group[Z_COLS + ["has_rating"] + flag_cols].copy()
    X[Z_COLS] = X[Z_COLS].clip(-CAP, CAP)
    return X


def main():
    # 1. Read the features
    feat = pd.read_parquet(FEATURES)

    # 2. Try every k in every segment
    rows = []
    for seg, group in feat.groupby("segment"):
        X = make_input(group)
        for k in K_VALUES:
            model = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = model.fit_predict(X)
            sizes = pd.Series(labels).value_counts()
            rows.append({
                "segment": seg,
                "k": k,
                "silhouette": silhouette_score(X, labels),
                "inertia": model.inertia_,
                "smallest_group": int(sizes.min()),
                "largest_group": int(sizes.max()),
            })

    # 3. Save the results
    results = pd.DataFrame(rows)
    results.to_csv(OUT, index=False)

    # 4. Show the results, one column per segment
    print("Saved", OUT, results.shape)
    print(results.pivot(index="k", columns="segment", values="silhouette").round(3).to_string())
    print(results.pivot(index="k", columns="segment", values="smallest_group").to_string())
    print(results.pivot(index="k", columns="segment", values="largest_group").to_string())


if __name__ == "__main__":
    main()