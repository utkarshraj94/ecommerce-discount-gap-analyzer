import sqlite3
from pathlib import Path

import pandas as pd

DB = Path("data/processed/app.db")
COLS = ["product_id", "discount_pct", "peer_median", "gap", "n_listings",
        "is_candidate", "low_confidence", "review_first"]


def main():
    # 1. Load the product table the app will read
    conn = sqlite3.connect(DB)
    products = pd.read_sql("SELECT * FROM app_products", conn)
    conn.close()

    # 2. Pick 10 listings that cover every case (random_state makes it repeatable)
    picks = pd.concat([
        products[products["is_candidate"] == 1].sample(3, random_state=7),
        products[(products["gap"] > 0) & (products["is_candidate"] == 0)].sample(2, random_state=7),
        products[products["gap"] <= 0].sample(1, random_state=7),
        products[products["low_confidence"] == 1].sample(2, random_state=7),
        products[products["review_first"] == 1].sample(2, random_state=7),
    ])

    # 3. The numbers to check by hand
    print(picks[COLS].round(2).to_string(index=False))

    # 4. Each listing's sentence, to check it says the same thing as the numbers
    for _, row in picks.iterrows():
        print(row["product_id"], "-", row["why_flagged"])


if __name__ == "__main__":
    main()