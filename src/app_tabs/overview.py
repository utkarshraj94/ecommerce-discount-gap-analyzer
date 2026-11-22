"""Overview tab: every segment side by side, and every listing's gap in the chosen one."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

SAMPLE_SIZE = 5000
COLOURS = alt.Scale(domain=["Test candidate", "Not flagged"], range=["#E8590C", "#174EA6"])


def show(products, selected, segment, min_gap):
    st.subheader("Overview")

    # 1. One row per segment, with candidates counted at the slider's gap
    summary = products.groupby("segment", as_index=False).agg(
        listings=("product_id", "count"),
        peer_groups=("peer_group", "nunique"),
        candidates=("flagged", "sum"),
    )
    summary["share"] = summary["candidates"] / summary["listings"] * 100

    # 2. Average gap of the candidates, and the peer group with the most candidates
    average_gaps = []
    start_notes = []
    for name in summary["segment"]:
        flagged = products[(products["segment"] == name) & products["flagged"]]
        if len(flagged) == 0:
            average_gaps.append(0)
            start_notes.append("No candidates at this gap")
            continue
        average_gaps.append(flagged["gap"].mean())
        counts = flagged.groupby("peer_group_name")["product_id"].count()
        top_group = counts.idxmax()
        start_notes.append(f"{top_group} ({counts.max():,} candidates)")
    summary["average_gap"] = average_gaps
    summary["start"] = start_notes

    # 3. Show the table, largest share first
    summary = summary.sort_values("share", ascending=False)
    table = summary.rename(columns={
        "segment": "Segment",
        "listings": "Listings",
        "peer_groups": "Peer groups",
        "candidates": "Test candidates",
        "share": "Share flagged (%)",
        "average_gap": "Average gap of candidates (points)",
        "start": "Where to start (peer group with most candidates)",
    })
    st.dataframe(table, hide_index=True, alt="Test candidates per segment", column_config={
        "Share flagged (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "Average gap of candidates (points)": st.column_config.NumberColumn(format="%.1f"),
    })
    st.caption(f"All counts use the {min_gap}-point minimum gap from the sidebar.")

    # 4. Dot strip for the chosen segment: each dot is a listing, placed by its gap;
    #    the up-and-down spread is random, only so dots do not sit on top of each other
    st.markdown(f"**Every listing's gap in {segment}**")
    if len(selected) > SAMPLE_SIZE:
        points = selected.sample(n=SAMPLE_SIZE, random_state=1).copy()
        st.caption(f"Showing a random {SAMPLE_SIZE:,} of {len(selected):,} listings.")
    else:
        points = selected.copy()
    points["status"] = "Not flagged"
    points.loc[points["flagged"], "status"] = "Test candidate"
    points["spread"] = np.random.default_rng(1).uniform(0, 1, len(points))

    dots = alt.Chart(points).mark_circle(size=18, opacity=0.5).encode(
        x=alt.X("gap:Q", title="Gap: discount minus peer median (points)"),
        y=alt.Y("spread:Q", axis=None, title=None),
        color=alt.Color("status:N", scale=COLOURS, legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip("name:N", title="Product"),
                 alt.Tooltip("brand:N", title="Brand"),
                 alt.Tooltip("gap:Q", title="Gap (points)", format=".1f")],
    )
    line = alt.Chart(pd.DataFrame({"x": [min_gap]})).mark_rule(
        color="#E8590C", strokeDash=[6, 4], size=2).encode(x="x:Q")
    st.altair_chart((dots + line).properties(height=220),
                    alt=f"Gap of each listing in {segment} against the minimum gap")
    st.caption(f"Dashed line: the {min_gap}-point minimum gap. Dots to its right are test "
               "candidates; dots left of 0 already discount less than similar listings.")