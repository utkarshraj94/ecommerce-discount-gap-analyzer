"""Product lookup tab: search one listing, see why it was or wasn't flagged."""

import streamlit as st

from src.app_tabs.common import add_test_columns, rupees, why_text

MAX_OPTIONS = 200


def show(selected, segment, min_gap, fee_pct, cost_pct, shipping):
    st.subheader("Product lookup")

        # 1. Search box with suggestions: brands and product names of the chosen segment;
    #    any other word (for example "linen") also works: type it and press Enter
    words = list(selected["brand"].unique()) + list(selected["name"].unique())
    suggestions = sorted(set(words))
    text = st.selectbox("Search a product or brand", suggestions, index=None,
                        placeholder="Start typing, for example: Puma, linen, Anouk",
                        accept_new_options=True, filter_mode="contains",
                        help=f"Suggests brands and product names from {segment}. "
                             "Pick one, or type any word and press Enter.")
    if text is None:
        st.caption("Type part of a product name or a brand to start.")
        return

    # 2. Listings whose name or brand contains the text (upper or lower case)
    in_name = selected["name"].str.contains(text, case=False, regex=False)
    in_brand = selected["brand"].str.contains(text, case=False, regex=False)
    matches = selected[in_name | in_brand].sort_values("gap", ascending=False)
    if len(matches) == 0:
        st.info("No products match that search.", icon=":material/search_off:")
        return
    if len(matches) > MAX_OPTIONS:
        st.caption(f"{len(matches):,} matches; the list shows the {MAX_OPTIONS} with the largest "
                   "gap. Type more to narrow it down.")
        matches = matches.head(MAX_OPTIONS)
    else:
        st.caption(f"{len(matches):,} matches, largest gap first.")

    # 3. Pick one listing; the label shows brand, name, price and discount
    labels = {}
    for row in matches.itertuples():
        labels[row.product_id] = (f"{row.brand} - {row.name} ({rupees(row.price)}, "
                                  f"{row.discount_pct:.0f}% off)")
    product_id = st.selectbox("Listing", list(labels), format_func=labels.get)
    product = add_test_columns(matches[matches["product_id"] == product_id],
                               fee_pct, cost_pct, shipping).iloc[0]

    # 4. The card: name, marks, link, five numbers and the why sentence
    with st.container(border=True):
        st.markdown(f"**{product['name']}**")
        with st.container(horizontal=True):
            if product["flagged"]:
                st.badge("Test candidate", color="orange")
            else:
                st.badge("Not flagged", color="gray")
            if product["low_confidence"] == 1:
                st.badge("Low confidence", color="violet")
            if product["review_first"] == 1:
                st.badge("Review first", color="red")
        st.caption(f"{product['brand']} · {product['peer_group_name']}")

        with st.container(horizontal=True):
            st.metric("MRP", rupees(product["mrp"]), border=True)
            st.metric("Price", rupees(product["price"]), border=True)
            st.metric("Discount", f"{product['discount_pct']:.0f}%", border=True)
            st.metric("Peer median", f"{product['peer_median']:.0f}%", border=True)
            st.metric("Gap", f"{product['gap']:+.1f} points", border=True)

        st.info(why_text(product, min_gap), icon=":material/info:")

        # 5. For a candidate: what the test at the peer median would mean
        if product["flagged"]:
            st.markdown(f"**If tested at {product['test_discount']:.0f}% off** "
                        f"(cost {cost_pct}% of MRP, fee {fee_pct}%, shipping ₹{shipping}): "
                        f"{rupees(product['extra_per_sale'])} extra per sale; "
                        f"break-even sales loss {product['break_even']}.")
        st.link_button("Open on Myntra", product["url"], icon=":material/open_in_new:")

    # 6. The 3 most similar listings: same peer group, closest MRP
    st.markdown("**3 closest similar listings** (same peer group, closest MRP)")
    group = selected[(selected["peer_group"] == product["peer_group"])
                     & (selected["product_id"] != product_id)].copy()
    group["mrp_difference"] = (group["mrp"] - product["mrp"]).abs()
    closest = group.sort_values("mrp_difference").head(3)
    table = closest[["name", "brand", "mrp", "discount_pct", "gap", "url"]].rename(columns={
        "name": "Product",
        "brand": "Brand",
        "mrp": "MRP (₹)",
        "discount_pct": "Discount (%)",
        "gap": "Gap (points)",
        "url": "Link",
    })
    st.dataframe(table, hide_index=True, alt="Closest similar listings", column_config={
        "MRP (₹)": st.column_config.NumberColumn(format="₹%,d"),
        "Discount (%)": st.column_config.NumberColumn(format="%.0f%%"),
        "Gap (points)": st.column_config.NumberColumn(format="%+.1f"),
        "Link": st.column_config.LinkColumn(display_text="Open"),
    })