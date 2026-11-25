"""Check a product tab: place a product that isn't in the catalogue and see its discount gap."""

import altair as alt
import pandas as pd
import streamlit as st

from src.app_tabs.candidate_list import CONFIG, make_table
from src.app_tabs.common import add_test_columns, rupees, why_text
from src.place_product import place_products

# The template for several products: the same fields as the processed data
TEMPLATE = pd.DataFrame([
    {"product_id": "A101", "name": "Women Printed Cotton Kurta", "brand": "My brand",
     "segment": "Women's Kurtas", "mrp": 2000, "price": 600, "rating": 4.2, "rating_count": 15},
    {"product_id": "A102", "name": "Men Solid Formal Shirt", "brand": "My brand",
     "segment": "Men's Shirts", "mrp": 1500, "price": 900, "rating": None, "rating_count": 0},
])
DEFAULT_SEGMENT = "Women's Kurtas"  # matches the example product name
NEEDED = ["name", "segment", "mrp", "price"]
OPTIONAL = {"product_id": None, "brand": "", "rating": None, "rating_count": 0, "url": None}


# 1. Place products with the catalogue's peer groups and the sidebar's minimum gap
def check(new_products, tables, min_gap):
    return place_products(new_products, tables["scaling"], tables["centres"],
                          tables["peer_groups"], min_gap)


# 2. The peer group's discounts as bars, with this product and the median as lines
def peer_chart(catalogue, row):
    peers = catalogue[(catalogue["segment"] == row["segment"])
                      & (catalogue["peer_group"] == row["peer_group"])]
    bins = (peers["discount_pct"] // 5 * 5).value_counts().sort_index().reset_index()
    bins.columns = ["start", "listings"]
    bins["end"] = bins["start"] + 5
    bins["sentence"] = (bins["listings"].astype(str) + " similar listings give "
                        + bins["start"].astype(int).astype(str) + "–"
                        + bins["end"].astype(int).astype(str) + "% off")
    bars = alt.Chart(bins).mark_bar(color="#A5B4C8").encode(
        x=alt.X("start:Q", bin="binned", title="Discount (%)"), x2="end:Q",
        y=alt.Y("listings:Q", title="Similar listings"),
        tooltip=alt.Tooltip("sentence:N", title=None))
    lines = pd.DataFrame({
        "discount": [row["discount_pct"], row["peer_median"]],
        "label": ["This product", "Peer median"],
        "sentence": [f"This product: {row['discount_pct']:.0f}% off",
                     f"Peer median: {row['peer_median']:.0f}% off"],
    })
    rules = alt.Chart(lines).mark_rule(strokeWidth=3).encode(
        x="discount:Q",
        color=alt.Color("label:N", title=None,
                        scale=alt.Scale(domain=["This product", "Peer median"],
                                        range=["#E8590C", "#174EA6"])),
        strokeDash=alt.condition(alt.datum.label == "Peer median",
                                 alt.value([6, 4]), alt.value([1, 0])),
        tooltip=alt.Tooltip("sentence:N", title=None))
    return (bars + rules).properties(height=260)


def show(catalogue, tables, min_gap, fee_pct, cost_pct, shipping):
    st.subheader("Check a product")
    st.caption("Enter a product that isn't in the catalogue. The app puts it in the peer group "
               "of the most similar listings (price level, ratings and product words, never "
               "discount) and compares its discount with theirs.")

    # 3. One product: the same fields as the processed data
    segments = sorted(tables["scaling"]["segment"])
    left, right = st.columns(2)
    name = left.text_input("Product name", "Women Printed Cotton Kurta", key="check_name",
                           help="Words such as cotton, printed, embroidered or solid help "
                                "find similar listings.")
    brand = right.text_input("Brand", "My brand", key="check_brand")
    seg = left.selectbox("Segment", segments, index=segments.index(DEFAULT_SEGMENT),
                         key="check_segment")
    product_id = right.text_input("Product ID (optional)", "", key="check_id")
    mrp = left.number_input("MRP (₹)", min_value=1, value=2000, step=50, key="check_mrp")
    price = right.number_input("Selling price (₹)", min_value=1, value=600, step=50,
                               key="check_price")
    rating = left.number_input("Rating (leave empty if unrated)", min_value=1.0, max_value=5.0,
                               value=None, step=0.1, key="check_rating")
    rating_count = right.number_input("Number of ratings", min_value=0, value=0, step=1,
                                      key="check_count")

    if price > mrp:
        st.error("The selling price can't be above the MRP.")
    else:
        # 4. Place it and add the test discount, extra profit and break-even
        product = pd.DataFrame([{
            "product_id": product_id or "New product", "name": name, "brand": brand,
            "segment": seg, "mrp": mrp, "price": price, "rating": rating,
            "rating_count": rating_count if rating is not None else 0,
        }])
        row = add_test_columns(check(product, tables, min_gap), fee_pct, cost_pct, shipping).iloc[0]

        # 5. Where it stands: four cards, the peer group and the reason
        with st.container(horizontal=True):
            st.metric("Its discount", f"{row['discount_pct']:.0f}%", border=True)
            st.metric("Peer median", f"{row['peer_median']:.0f}%", border=True,
                      help=f"The middle half of similar listings give "
                           f"{row['peer_q25']:.0f}% to {row['peer_q75']:.0f}% off.")
            st.metric("Gap", f"{row['gap']:+.1f} points", border=True,
                      help="Its discount minus the peer median.")
            st.metric("Test candidate", "Yes" if row["flagged"] else "No", border=True,
                      help=f"Yes when the gap is {min_gap} points or more.")
        st.markdown(f"**Peer group:** {row['peer_group_name']} "
                    f"({row['n_listings']:,} similar listings in {seg})")
        if row["flagged"]:
            st.warning(why_text(row, min_gap), icon=":material/flag:")
        else:
            st.success(why_text(row, min_gap), icon=":material/check_circle:")

        # 6. Money: what moving to the peer median would mean, with the sidebar's costs
        with st.container(horizontal=True):
            st.metric("Test discount (peer median)", f"{row['test_discount']:.0f}%", border=True)
            st.metric("Extra profit per sale", rupees(row["extra_per_sale"]), border=True,
                      help="Contribution at the test discount minus contribution now.")
            st.metric("Break-even sales loss", row["break_even"], border=True,
                      help="How many sales (%) the smaller discount can lose and still earn the same.")
        st.altair_chart(peer_chart(catalogue, row),
                        alt=f"Discounts of the {row['n_listings']:,} similar listings, "
                            f"with this product and the peer median marked")

    # 7. Several products: a CSV with the same columns, checked all at once
    st.divider()
    st.subheader("Check several products")
    st.caption("Columns: name, segment, mrp and price are needed; product_id, brand, rating "
               f"and rating_count are optional. Segment must be one of: {', '.join(segments)}.")
    st.download_button("Download a template CSV", TEMPLATE.to_csv(index=False),
                       file_name="products_template.csv", mime="text/csv",
                       icon=":material/download:")
    upload = st.file_uploader("Upload a CSV with the same columns", type="csv")
    if upload is None:
        return
    new = pd.read_csv(upload)
    missing = [col for col in NEEDED if col not in new.columns]
    if missing:
        st.error(f"The file is missing these columns: {', '.join(missing)}.")
        return

    # 8. Fill optional columns, then skip rows the app can't place
    for col, default in OPTIONAL.items():
        if col not in new.columns:
            new[col] = default
    new["product_id"] = new["product_id"].fillna(pd.Series(range(1, len(new) + 1)))
    ok = (new["segment"].isin(segments) & (new["mrp"] > 0)
          & (new["price"] > 0) & (new["price"] <= new["mrp"]))
    if (~ok).sum() > 0:
        st.warning(f"{(~ok).sum()} rows skipped: unknown segment, or a price that is missing, "
                   "zero or above the MRP.")
    if ok.sum() == 0:
        return

    # 9. The results table, ranked by gap, with a download
    results = make_table(check(new[ok], tables, min_gap), min_gap, fee_pct, cost_pct, shipping)
    st.dataframe(results, column_config=CONFIG)
    st.download_button("Download results (CSV)", results.to_csv(),
                       file_name="checked_products.csv", mime="text/csv",
                       icon=":material/download:")
