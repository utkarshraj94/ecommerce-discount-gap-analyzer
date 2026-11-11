import sqlite3
from pathlib import Path

import pandas as pd

PARQUET = Path("data/processed/clean_products.parquet")
SCHEMA = Path("sql/schema.sql")
DB = Path("data/processed/discount.db")


def main():
    # 1. Read the clean data
    df = pd.read_parquet(PARQUET)

    # 2. Brand table: one row per unique brand, ids start at 1
    brands = pd.DataFrame({"brand_name": sorted(df["brand"].unique())})
    brands["brand_id"] = range(1, len(brands) + 1)

    # 3. Category table: one row per unique segment
    cats = df[["segment", "product_type", "gender"]].drop_duplicates()
    cats = cats.sort_values("segment").reset_index(drop=True)
    cats["category_id"] = range(1, len(cats) + 1)

    # 4. Add the two ids onto every listing
    df = df.merge(brands, left_on="brand", right_on="brand_name")
    df = df.merge(cats, on=["segment", "product_type", "gender"])
    df["has_rating"] = df["has_rating"].astype(int)

    # 5. Keep only the columns the fact table needs
    fact = df[["product_id", "brand_id", "category_id", "name", "price", "mrp",
               "discount_pct", "rating", "rating_count", "has_rating", "url"]]

    # 6. Build a fresh database from the schema file
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text())

    # 7. Insert the three tables (dimensions first)
    brands[["brand_id", "brand_name"]].to_sql("dim_brand", con, if_exists="append", index=False)
    cats[["category_id", "segment", "product_type", "gender"]].to_sql("dim_category", con, if_exists="append", index=False)
    fact.to_sql("fact_listing", con, if_exists="append", index=False)
    con.commit()

    # 8. Print row counts as a quick check
    for table in ["dim_brand", "dim_category", "fact_listing"]:
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(table, n)
    con.close()


if __name__ == "__main__":
    main()