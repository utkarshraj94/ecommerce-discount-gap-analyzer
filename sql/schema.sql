-- Turn on foreign key checks (SQLite has them off by default)
PRAGMA foreign_keys = ON;

-- Remove old tables so the file can be re-run. Fact table first.
DROP TABLE IF EXISTS fact_listing;
DROP TABLE IF EXISTS dim_brand;
DROP TABLE IF EXISTS dim_category;

-- One row per brand
CREATE TABLE dim_brand (
    brand_id   INTEGER PRIMARY KEY,
    brand_name TEXT NOT NULL UNIQUE
);

-- One row per segment, e.g. "Men's Kurtas"
CREATE TABLE dim_category (
    category_id  INTEGER PRIMARY KEY,
    segment      TEXT NOT NULL UNIQUE,
    product_type TEXT NOT NULL,
    gender       TEXT NOT NULL
);

-- One row per product listing
CREATE TABLE fact_listing (
    product_id   INTEGER PRIMARY KEY,
    brand_id     INTEGER NOT NULL REFERENCES dim_brand(brand_id),
    category_id  INTEGER NOT NULL REFERENCES dim_category(category_id),
    name         TEXT,
    price        REAL NOT NULL CHECK (price > 0),
    mrp          REAL NOT NULL CHECK (mrp >= price),
    discount_pct REAL NOT NULL CHECK (discount_pct BETWEEN 0 AND 95),
    rating       REAL CHECK (rating BETWEEN 1 AND 5),
    rating_count INTEGER NOT NULL CHECK (rating_count >= 0),
    has_rating   INTEGER NOT NULL CHECK (has_rating IN (0, 1)),
    url          TEXT NOT NULL
);

-- Indexes make joins and filters on these columns faster
CREATE INDEX idx_fact_brand    ON fact_listing(brand_id);
CREATE INDEX idx_fact_category ON fact_listing(category_id);