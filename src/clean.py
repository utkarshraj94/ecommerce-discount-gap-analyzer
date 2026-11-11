"""Clean the raw Myntra catalogue and count every row removed."""

import json
from pathlib import Path

import pandas as pd
import numpy as np

# ---------- Settings ----------
ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "myntra202305041052.csv"
OUT_DIR = ROOT / "data" / "processed"
CLEAN_PATH = OUT_DIR / "clean_products.parquet"
QUALITY_PATH = OUT_DIR / "data_quality.json"

USECOLS = ["name", "price", "mrp", "rating", "ratingTotal", "discount", "seller", "purl"]
CHUNK_ROWS = 500_000
MAX_DISCOUNT = 95  # a calculated discount above this % is treated as a data error

# Product link category word -> (label, word the name must contain, or None)
PRODUCT_TYPES = {
    "shirts": ("Shirts", None),
    "kurtas": ("Kurtas", None),
    "casual-shoes": ("Sneakers", "sneaker"),
}

# The segments products are compared within: (gender, product type)
SEGMENTS = [
    ("Men", "Shirts"),
    ("Women", "Shirts"),
    ("Men", "Kurtas"),
    ("Women", "Kurtas"),
    ("Women", "Sneakers"),
]
MIN_SEGMENT_SIZE = 30


# ---------- Step 2: read in chunks and filter ----------
def clean_chunk(chunk, seen_ids, counts):
    """Apply the removal steps, in order, to one chunk and count each one."""
    counts["rows_loaded"] += len(chunk)

     # 1. Duplicate products.    

    product_id = pd.to_numeric(chunk["purl"].str.split("/").str[-2], errors="coerce")
    is_dup = product_id.notna() & (product_id.duplicated() | product_id.isin(seen_ids))
    seen_ids.update(product_id.dropna().astype("int64"))
    counts["duplicate_ids"] += int(is_dup.sum())
    chunk = chunk.assign(product_id=product_id)[~is_dup]

    # 2. Invalid prices
    bad_price = (
        chunk["price"].isna() | chunk["mrp"].isna()
        | (chunk["price"] <= 0) | (chunk["mrp"] <= 0)
        | (chunk["price"] > chunk["mrp"])
    )
    counts["invalid_prices"] += int(bad_price.sum())
    chunk = chunk[~bad_price].copy()

    # 3. Extreme discounts (calculated, not the file's discount column)
    chunk["discount_pct"] = (1 - chunk["price"] / chunk["mrp"]) * 100
    extreme = chunk["discount_pct"] > MAX_DISCOUNT
    counts["extreme_discounts"] += int(extreme.sum())
    chunk = chunk[~extreme].copy()

    # 4. Outside the project's categories
    chunk["category"] = chunk["purl"].str.split("/").str[3]
    labels = {word: label for word, (label, _) in PRODUCT_TYPES.items()}
    chunk["product_type"] = chunk["category"].map(labels)
    keep = chunk["product_type"].notna()
    name_lower = chunk["name"].str.lower()
    for word, (_, must_contain) in PRODUCT_TYPES.items():
        if must_contain:
            lacks_word = ~name_lower.str.contains(must_contain, regex=False, na=False)
            keep &= ~((chunk["category"] == word) & lacks_word)
    counts["outside_categories"] += int((~keep).sum())
    return chunk[keep]


def load_in_scope():
    """Read the raw CSV chunk by chunk, keeping only in-scope rows in memory."""
    counts = {
        "rows_loaded": 0,
        "duplicate_ids": 0,
        "invalid_prices": 0,
        "extreme_discounts": 0,
        "outside_categories": 0,
    }
    seen_ids = set()
    parts = []
    for chunk in pd.read_csv(RAW_PATH, usecols=USECOLS, chunksize=CHUNK_ROWS, low_memory=False):
        parts.append(clean_chunk(chunk, seen_ids, counts))
    return pd.concat(parts, ignore_index=True), counts

# ---------- Step 3: gender and segments ----------
def add_gender(df):
    """Add a gender column: the product link first, the name as a back-up."""
    link = df["purl"].str.lower()
    name = df["name"].str.lower()

    link_men = link.str.contains(r"[/-]men-")
    link_women = link.str.contains(r"[/-]women-")
    link_kids = link.str.contains(r"[/-](?:boys?|girls?|kids?)-")
    name_men = name.str.contains(r"\bmen\b")
    name_women = name.str.contains(r"\bwomen\b")
    name_kids = name.str.contains(r"\b(?:boys?|girls?|kids?)\b")

    conditions = [
        link_kids, link_men & ~link_women, link_women & ~link_men,
        name_kids, name_men & ~name_women, name_women & ~name_men,
    ]
    choices = ["Kids", "Men", "Women", "Kids", "Men", "Women"]
    df["gender"] = np.select(conditions, choices, default="Unknown")
    return df


def apply_segments(df, counts):
    """Keep only the products that belong to a segment; count what is set aside."""
    wanted = {f"{gender}'s {ptype}" for gender, ptype in SEGMENTS}
    df["segment"] = df["gender"] + "'s " + df["product_type"]
    keep = df["segment"].isin(wanted)

    aside = df.loc[~keep, "gender"]
    counts["set_aside_gender"] = int((~keep).sum())
    counts["set_aside_detail"] = {
        "kids": int((aside == "Kids").sum()),
        "unknown_gender": int((aside == "Unknown").sum()),
        "no_segment": int(aside.isin(["Men", "Women"]).sum()),
    }
    return df[keep].copy()

# ---------- Step 4: ratings and tidy columns ----------
FINAL_COLUMNS = [
    "product_id", "name", "brand", "category", "product_type", "gender", "segment",
    "price", "mrp", "discount_pct", "file_discount",
    "rating", "rating_count", "has_rating", "url",
]


def tidy_columns(df, counts):
    """Handle placeholder ratings, rename columns, keep the final set."""
    df = df.rename(columns={
        "seller": "brand",
        "ratingTotal": "rating_count",
        "discount": "file_discount",
        "purl": "url",
    })
    df["brand"] = df["brand"].str.strip()
    df["name"] = df["name"].str.strip()

    # A rating of 0 with 0 reviews means "not rated", not "rated badly"
    df["has_rating"] = df["rating_count"] > 0
    df["rating"] = df["rating"].where(df["has_rating"])
    counts["unrated_products"] = int((~df["has_rating"]).sum())

    return df[FINAL_COLUMNS]

# ---------- Step 5: report and save ----------
REMOVAL_STEPS = [
    ("duplicate_ids", "Duplicate products (same product ID)"),
    ("invalid_prices", "Invalid prices"),
    ("extreme_discounts", f"Extreme discounts (over {MAX_DISCOUNT}%)"),
    ("outside_categories", "Outside the project's categories"),
    ("set_aside_gender", "Set aside for gender or segment"),
]


def build_report(counts, df):
    """Build the removal log the app's Data quality tab reads."""
    remaining = counts["rows_loaded"]
    steps = [{"step": "Rows loaded", "removed": 0, "remaining": remaining}]
    for key, label in REMOVAL_STEPS:
        remaining -= counts[key]
        steps.append({"step": label, "removed": counts[key], "remaining": remaining})

    if remaining != len(df):
        raise ValueError(f"Counts do not add up: {remaining} expected, {len(df)} kept")
    steps.append({"step": "Rows kept", "removed": 0, "remaining": len(df)})

    sizes = df["segment"].value_counts()
    segment_sizes = {f"{g}'s {t}": int(sizes.get(f"{g}'s {t}", 0)) for g, t in SEGMENTS}
    return {
        "source_file": RAW_PATH.name,
        "steps": steps,
        "set_aside_detail": counts["set_aside_detail"],
        "unrated_products": counts["unrated_products"],
        "segment_sizes": segment_sizes,
        "segments_below_minimum": [s for s, n in segment_sizes.items() if n < MIN_SEGMENT_SIZE],
        "prices_above_mrp": int((df["price"] > df["mrp"]).sum()),
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, counts = load_in_scope()
    df = add_gender(df)
    df = apply_segments(df, counts)
    df = tidy_columns(df, counts)
    report = build_report(counts, df)

    df.to_parquet(CLEAN_PATH, index=False)
    QUALITY_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for step in report["steps"]:
        print(f"{step['step']:<42}{step['removed']:>10,}{step['remaining']:>12,}")
    print("Unrated products (kept, flagged):", f"{report['unrated_products']:,}")
    print("Segment sizes:", report["segment_sizes"])
    print("Saved:", CLEAN_PATH.name, "and", QUALITY_PATH.name)


if __name__ == "__main__":
    main()