from pathlib import Path

import pandas as pd

FEATURES = Path("data/processed/features.parquet")
SELECTION = Path("data/processed/k_selection.csv")
OUT = Path("data/processed/chosen_k.csv")

# Rules for a usable k
MAX_LARGEST_SHARE = 0.40
MIN_GROUP_SIZE = 30


def main():
    # 1. Read the Step 1 results and the size of each segment
    results = pd.read_csv(SELECTION)
    feat = pd.read_parquet(FEATURES)
    seg_size = feat["segment"].value_counts()

    # 2. Share of the segment held by its largest group
    results["largest_share"] = results["largest_group"] / results["segment"].map(seg_size)

    # 3. Keep only the k values that pass both rules
    passes_share = results["largest_share"] <= MAX_LARGEST_SHARE
    passes_size = results["smallest_group"] >= MIN_GROUP_SIZE
    ok = results[passes_share & passes_size]

    # 4. Best silhouette first, within each segment
    ok = ok.sort_values(["segment", "silhouette"], ascending=[True, False])

    # 5. Keep the three best passing values of k per segment and save them
    candidates = ok.groupby("segment").head(3)
    candidates.to_csv(OUT, index=False)

    # 6. Show them
    columns = ["segment", "k", "silhouette", "smallest_group", "largest_share"]
    print(candidates[columns].round(3).to_string(index=False))


if __name__ == "__main__":
    main()