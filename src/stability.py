from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

from src.select_k import make_input

FEATURES = Path("data/processed/features.parquet")
CANDIDATES = Path("data/processed/chosen_k.csv")
OUT = Path("data/processed/stability.csv")
FINAL = Path("data/processed/final_k.csv")

SEEDS = [1, 2, 3, 4, 5]
MIN_STABILITY = 0.8


def main():
    # 1. Read the features and the candidate values of k
    feat = pd.read_parquet(FEATURES)
    candidates = pd.read_csv(CANDIDATES)

    # 2. Refit each candidate with 5 seeds and compare the labels
    rows = []
    for _, row in candidates.iterrows():
        seg = row["segment"]
        k = int(row["k"])
        X = make_input(feat[feat["segment"] == seg])

        all_labels = []
        for seed in SEEDS:
            model = KMeans(n_clusters=k, random_state=seed, n_init=10)
            all_labels.append(model.fit_predict(X))

        scores = []
        for other in all_labels[1:]:
            scores.append(adjusted_rand_score(all_labels[0], other))

        rows.append({
            "segment": seg,
            "k": k,
            "silhouette": row["silhouette"],
            "mean_ari": sum(scores) / len(scores),
            "min_ari": min(scores),
        })

    # 3. Save the stability results
    results = pd.DataFrame(rows)
    results.to_csv(OUT, index=False)
    print(results.round(3).to_string(index=False))

    # 4. Final k: stable enough, then the best silhouette, in each segment
    stable = results[results["min_ari"] >= MIN_STABILITY]
    stable = stable.sort_values(["segment", "silhouette"], ascending=[True, False])
    final = stable.groupby("segment").head(1)
    final.to_csv(FINAL, index=False)
    print()
    print("Final k per segment:")
    print(final.round(3).to_string(index=False))


if __name__ == "__main__":
    main()