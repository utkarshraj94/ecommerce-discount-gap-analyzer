import sqlite3
from pathlib import Path

import pandas as pd

DB = Path("data/processed/discount.db")
SQL = Path("sql/metrics.sql")
PARQUET = Path("data/processed/clean_products.parquet")

# Part 1: run each saved query and print the result
con = sqlite3.connect(DB)
for q in SQL.read_text().split(";"):
    if "SELECT" in q:
        print(pd.read_sql(q, con))
        print()
con.close()

# Part 2: the same numbers from pandas
df = pd.read_parquet(PARQUET)
df["is_full_price"] = df["discount_pct"] == 0
df["is_unrated"] = ~df["has_rating"]
check = df.groupby("segment").agg(
    listings=("product_id", "count"),
    avg_price=("price", "mean"),
    avg_discount=("discount_pct", "mean"),
    pct_full_price=("is_full_price", "mean"),
    pct_unrated=("is_unrated", "mean"),
)
check["pct_full_price"] = check["pct_full_price"] * 100
check["pct_unrated"] = check["pct_unrated"] * 100
print(check.round(1).to_string())