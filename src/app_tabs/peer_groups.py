"""Peer groups tab: price against discount, and each group's usual discount range."""

import altair as alt
import streamlit as st

from src.app_tabs.common import why_text

SAMPLE_SIZE = 5000
COLOURS = alt.Scale(domain=["Test candidate", "Not flagged"], range=["#E8590C", "#174EA6"])


def show(selected, segment, min_gap):
    st.subheader("Peer groups")
    st.caption("Each listing is compared only with similar listings in its peer group "
               "(price band, rating, style), not with the whole segment.")

    # 1. Sample up to 5,000 listings so the chart stays fast
    if len(selected) > SAMPLE_SIZE:
        points = selected.sample(n=SAMPLE_SIZE, random_state=1).copy()
        st.caption(f"Showing a random {SAMPLE_SIZE:,} of {len(selected):,} listings.")
    else:
        points = selected.copy()

    # 2. A status word and a sentence for each point's tooltip
    points["status"] = "Not flagged"
    points.loc[points["flagged"], "status"] = "Test candidate"
    points["why"] = points.apply(why_text, axis=1, min_gap=min_gap)

    # 3. Scatter: MRP (log scale) against discount, orange = test candidate
    scatter = alt.Chart(points).mark_circle(size=35, opacity=0.6).encode(
        x=alt.X("mrp:Q", scale=alt.Scale(type="log"), title="MRP (₹, log scale)"),
        y=alt.Y("discount_pct:Q", title="Discount (%)"),
        color=alt.Color("status:N", scale=COLOURS, legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip("name:N", title="Product"),
                 alt.Tooltip("brand:N", title="Brand"),
                 alt.Tooltip("peer_group_name:N", title="Peer group"),
                 alt.Tooltip("why:N", title="Why")],
    )
    st.altair_chart(scatter, alt=f"MRP against discount for listings in {segment}")

    # 4. One row per peer group: size, discount range, candidates with the slider's gap
    groups = selected.groupby(["peer_group", "peer_group_name"], as_index=False).agg(
        listings=("product_id", "count"),
        q25=("peer_q25", "first"),
        median=("peer_median", "first"),
        q75=("peer_q75", "first"),
        candidates=("flagged", "sum"),
        low_confidence=("low_confidence", "first"),
    )
    groups["label"] = groups["peer_group"].astype(str) + ". " + groups["peer_group_name"]
    groups["flag_line"] = (groups["median"] + min_gap).clip(upper=100)
    meanings = []
    for row in groups.itertuples():
        meanings.append(f"The middle half of these {row.listings:,} listings give "
                        f"{row.q25:.0f}% to {row.q75:.0f}% off; the median is {row.median:.0f}%. "
                        f"Listings above {row.flag_line:.0f}% off are flagged "
                        f"({row.candidates:,} of them).")
    groups["meaning"] = meanings

    # 5. Range chart: a bar from the 25th to the 75th percentile, the median as a dark tick,
    #    and the flag line (median + minimum gap) as an orange tick
    st.markdown("**Usual discount in each peer group**")
    base = alt.Chart(groups).encode(
        y=alt.Y("label:N", sort=None, title=None, axis=alt.Axis(labelLimit=420)),
        tooltip=[alt.Tooltip("meaning:N", title="What it means")],
    )
    middle_half = base.mark_bar(size=16, color="#9DB7E0").encode(
        x=alt.X("q25:Q", title="Discount (%)", scale=alt.Scale(domain=[0, 100])),
        x2="q75:Q",
    )
    median_tick = base.mark_tick(color="#31333F", thickness=3, size=22).encode(x="median:Q")
    flag_tick = base.mark_tick(color="#E8590C", thickness=3, size=22).encode(x="flag_line:Q")
    st.altair_chart(middle_half + median_tick + flag_tick,
                    alt=f"Discount range of each peer group in {segment}")
    st.caption("Blue bar: the middle half of discounts in the group. Dark tick: the median. "
               f"Orange tick: the median plus the {min_gap}-point minimum gap.")

    # 6. The same groups as a table
    table = groups[["label", "listings", "q25", "median", "q75", "candidates", "low_confidence"]]
    table = table.rename(columns={
        "label": "Peer group",
        "listings": "Listings",
        "q25": "25th percentile (%)",
        "median": "Median (%)",
        "q75": "75th percentile (%)",
        "candidates": "Test candidates",
        "low_confidence": "Low confidence",
    })
    table["Low confidence"] = table["Low confidence"].map({1: "Yes", 0: ""})
    st.dataframe(table, hide_index=True, alt=f"Peer groups in {segment}", column_config={
        "25th percentile (%)": st.column_config.NumberColumn(format="%.0f%%"),
        "Median (%)": st.column_config.NumberColumn(format="%.0f%%"),
        "75th percentile (%)": st.column_config.NumberColumn(format="%.0f%%"),
        "Low confidence": st.column_config.TextColumn(
            help="Yes = fewer than 100 listings, so the median is less reliable."),
    })