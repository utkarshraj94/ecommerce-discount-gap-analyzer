"""Brands tab: which brands discount more or less than similar listings."""

import altair as alt
import pandas as pd
import streamlit as st

MIN_LISTINGS = 20
SHOW_EACH_SIDE = 15
COLOURS = alt.Scale(domain=["Deeper than similar listings", "Same or less deep"],
                    range=["#E8590C", "#174EA6"])


def show(selected, segment, min_gap):
    st.subheader("Brands")
    st.caption(f"Brands with {MIN_LISTINGS} or more listings in {segment}. A brand's gap is the "
               "median of its listings' gaps, so one odd listing does not move it much.")

    # 1. One row per brand: size, median gap, median discount, candidates
    brands = selected.groupby("brand", as_index=False).agg(
        listings=("product_id", "count"),
        median_gap=("gap", "median"),
        median_discount=("discount_pct", "median"),
        candidates=("flagged", "sum"),
    )
    brands = brands[brands["listings"] >= MIN_LISTINGS].copy()
    if len(brands) == 0:
        st.info(f"No brand has {MIN_LISTINGS} or more listings in this segment.",
                icon=":material/info:")
        return
    brands["share"] = brands["candidates"] / brands["listings"] * 100
    brands = brands.sort_values("median_gap", ascending=False)

    # 2. Bars to draw: all brands, or the 15 deepest and the 15 least deep
    if len(brands) > 2 * SHOW_EACH_SIDE:
        shown = pd.concat([brands.head(SHOW_EACH_SIDE), brands.tail(SHOW_EACH_SIDE)])
        st.caption(f"The chart shows the {SHOW_EACH_SIDE} brands with the deepest and the "
                   f"{SHOW_EACH_SIDE} with the least deep discounts against similar listings; "
                   f"the table below has all {len(brands)}.")
    else:
        shown = brands.copy()

    # 3. A colour group and a sentence for each bar
    shown["side"] = "Same or less deep"
    shown.loc[shown["median_gap"] > 0, "side"] = "Deeper than similar listings"
    meanings = []
    for row in shown.itertuples():
        meanings.append(f"{row.brand}: {row.listings:,} listings, median gap "
                        f"{row.median_gap:+.1f} points; {row.candidates:,} test candidates "
                        f"({row.share:.0f}%) at the {min_gap}-point minimum.")
    shown["meaning"] = meanings

    # 4. Bars from a centre line at 0: right = deeper discounts than similar listings
    bars = alt.Chart(shown).mark_bar().encode(
        x=alt.X("median_gap:Q", title="Median gap (points): right = deeper than similar listings"),
        y=alt.Y("brand:N", sort=None, title=None),
        color=alt.Color("side:N", scale=COLOURS, legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[alt.Tooltip("meaning:N", title="What it means")],
    )
    centre = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#31333F").encode(x="x:Q")
    st.altair_chart(bars + centre, alt=f"Median gap per brand in {segment}")

    # 5. All brands as a table
    table = brands[["brand", "listings", "median_discount", "median_gap", "candidates", "share"]]
    table = table.rename(columns={
        "brand": "Brand",
        "listings": "Listings",
        "median_discount": "Median discount (%)",
        "median_gap": "Median gap (points)",
        "candidates": "Test candidates",
        "share": "Share flagged (%)",
    })
    st.dataframe(table, hide_index=True, alt=f"Brands in {segment}", column_config={
        "Median discount (%)": st.column_config.NumberColumn(format="%.0f%%"),
        "Median gap (points)": st.column_config.NumberColumn(format="%+.1f"),
        "Share flagged (%)": st.column_config.NumberColumn(format="%.0f%%"),
    })
    