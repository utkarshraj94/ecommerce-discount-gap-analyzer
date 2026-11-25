import sqlite3
from pathlib import Path

import pandas as pd

from src.place_product import make_features, place_products

DB = Path(__file__).parent.parent / "data" / "processed" / "app.db"


def load(table):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df


def test_catalogue_listings_land_in_their_own_group():
    listings = load("app_products").sample(500, random_state=1)
    placed = place_products(listings, load("app_scaling"), load("app_centres"), load("app_peer_groups"))
    assert (placed["peer_group"].to_numpy() == listings["peer_group"].to_numpy()).all()
    assert (placed["gap"].to_numpy() == listings["gap"].to_numpy()).all()


def test_unrated_product_gets_the_segment_average_rating():
    product = pd.DataFrame([{"name": "Men Solid Kurta", "segment": "Men's Kurtas",
                             "mrp": 2000, "price": 800, "rating": None, "rating_count": 0}])
    feat = make_features(product, load("app_scaling"))
    assert feat.loc[0, "has_rating"] == 0
    assert abs(feat.loc[0, "rating_filled_z"]) < 1e-9
    assert feat.loc[0, "is_solid"] == 1


def test_discount_and_gap():
    product = pd.DataFrame([{"name": "Women Printed Kurta", "segment": "Women's Kurtas",
                             "mrp": 2000, "price": 600, "rating": 4.2, "rating_count": 15}])
    placed = place_products(product, load("app_scaling"), load("app_centres"), load("app_peer_groups"))
    assert round(placed.loc[0, "discount_pct"], 6) == 70
    assert placed.loc[0, "gap"] == round(70 - placed.loc[0, "peer_median"], 1)
