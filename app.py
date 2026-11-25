import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from src.app_tabs import (brands, calculator, candidate_list, check_product, data_quality, lookup,
                          overview, peer_groups, results)
from src.business import MIN_GAP

DB_PATH = Path(__file__).parent / "data" / "processed" / "app.db"
APP_TITLE = "E-commerce Discount Gap Analyzer: Myntra Catalogue"
TAB_NAMES = [
    ":material/dashboard: Overview",
    ":material/groups: Peer groups",
    ":material/flag: Test candidates",
    ":material/search: Product lookup",
    ":material/add_box: Check a product",
    ":material/sell: Brands",
    ":material/calculate: Calculator",
    ":material/science: Test results",
    ":material/fact_check: Data quality",
]

# 1. Page settings: browser tab title, tab icon and a wide layout
st.set_page_config(page_title="Discount Gap Analyzer",
                   page_icon=":material/sell:", layout="wide")


# 2. Read one table from app.db; the cache means each table loads only once
@st.cache_data
def load_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    table = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return table


products = load_table("app_products")

# 3. The test plan (shortlist) lives in session_state so it survives reruns (every click)
if "plan" not in st.session_state:
    st.session_state["plan"] = []

# 4. Sidebar, part 1: which listings to look at
segment_list = sorted(products["segment"].unique())
with st.sidebar:
    st.header("Settings", icon=":material/tune:")
    segment = st.selectbox("Segment", segment_list)
    min_gap = st.slider(
        "Minimum gap above peer median (points)", 0, 20, MIN_GAP,
        help="How far above similar products a discount must be before it is flagged.")

    # 5. Sidebar, part 2: cost assumptions (the data has no costs)
    st.subheader("Cost assumptions", icon=":material/payments:")
    fee_pct = st.slider("Marketplace fee (%)", 10, 30, 20)
    cost_pct = st.slider("Product cost (% of MRP)", 5, 60, 15,
                         help="Assumption: the data has no cost field.")
    shipping = st.number_input("Shipping per order (₹)", 0, 500, 80, step=10)
    st.caption("Data: Myntra product catalogue (Kaggle), 18,037 listings in 5 segments. "
               "Fee, cost and shipping are your assumptions, not data.")

# 6. Flag test candidates with the slider's gap, then keep the chosen segment
products["flagged"] = (products["gap"] > 0) & (products["gap"] >= min_gap)
selected = products[products["segment"] == segment]
n_flagged = int(selected["flagged"].sum())
share_flagged = n_flagged / len(selected) * 100

# 7. Top of page: title, purpose and a help box with the key words
st.title(APP_TITLE, icon=":material/sell:")
st.caption("Which listings discount more than similar products, "
           "and which ones are worth a smaller-discount A/B test.")
with st.expander("What the words mean", icon=":material/help:"):
    st.markdown(
        "- **Peer group:** similar listings in the same segment (price band, rating, style).\n"
        "- **Peer median:** the middle discount in that peer group.\n"
        "- **Gap:** this listing's discount minus its peer median, in points.\n"
        "- **Test candidate:** gap above 0 and at least the minimum gap.\n"
        "- **Contribution:** what one sale earns after fee, cost and shipping.\n"
        "- **Break-even sales loss:** how many sales (%) a smaller discount can lose "
        "and still earn the same.")

# 8. Four headline numbers as bordered cards; the plan card is filled at the end
with st.container(horizontal=True):
    st.metric("Listings in segment", f"{len(selected):,}", border=True)
    st.metric("Peer groups", selected["peer_group"].nunique(), border=True)
    st.metric("Test candidates", f"{n_flagged:,}", border=True,
              help=f"{share_flagged:.0f}% of the listings in this segment.")
    plan_card = st.empty()

# 9. The nine tabs, one name each
(overview_tab, peer_tab, candidates_tab, lookup_tab, check_tab,
 brands_tab, calculator_tab, results_tab, quality_tab) = st.tabs(TAB_NAMES)

# 10. Fill each tab
with overview_tab:
    overview.show(products, selected, segment, min_gap)
with peer_tab:
    peer_groups.show(selected, segment, min_gap)
with candidates_tab:
    candidate_list.show(selected, products, segment, min_gap, fee_pct, cost_pct, shipping)
with lookup_tab:
    lookup.show(selected, segment, min_gap, fee_pct, cost_pct, shipping)
with check_tab:
    tables = {"scaling": load_table("app_scaling"), "centres": load_table("app_centres"),
              "peer_groups": load_table("app_peer_groups")}
    check_product.show(products, tables, min_gap, fee_pct, cost_pct, shipping)
with brands_tab:
    brands.show(selected, segment, min_gap)
with calculator_tab:
    calculator.show(fee_pct, cost_pct, shipping)
with results_tab:
    results.show()
with quality_tab:
    data_quality.show(load_table("app_data_quality"), load_table("app_checks"),
                      products, min_gap)

# 11. Fill the plan card last, after the Test candidates tab has saved the ticks
plan_card.metric("Products in test plan", len(st.session_state["plan"]), border=True)