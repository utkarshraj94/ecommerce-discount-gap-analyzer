"""Data quality tab: how the raw file became the 18,037 listings, and the build checks."""

import altair as alt
import streamlit as st


def show(cleaning, checks, products, min_gap):
    st.subheader("Data quality")

    # 1. Three headline numbers from the cleaning steps
    loaded = int(cleaning["remaining"].iloc[0])
    kept = int(cleaning["remaining"].iloc[-1])
    with st.container(horizontal=True):
        st.metric("Rows loaded", f"{loaded:,}", border=True)
        st.metric("Rows removed", f"{loaded - kept:,}", border=True)
        st.metric("Listings analysed", f"{kept:,}", border=True)

    # 2. Cleaning funnel: rows left after each step, with what that step removed
    st.markdown("**Cleaning funnel**")
    funnel = cleaning.copy()
    funnel["order"] = range(len(funnel))
    labels = []
    for row in funnel.itertuples():
        if row.removed > 0:
            labels.append(f"{row.remaining:,} left ({row.removed:,} removed)")
        else:
            labels.append(f"{row.remaining:,}")
    funnel["label"] = labels

    base = alt.Chart(funnel).encode(
        y=alt.Y("step:N", sort=alt.EncodingSortField(field="order"), title=None,
                axis=alt.Axis(labelLimit=300)),
    )
    bars = base.mark_bar(color="#174EA6").encode(
        x=alt.X("remaining:Q", title="Rows left after the step"),
        tooltip=[alt.Tooltip("label:N", title="Rows")],
    )
    text = base.mark_text(align="left", dx=4, color="#31333F").encode(
        x="remaining:Q", text="label:N")
    st.altair_chart(bars + text, alt="Rows left after each cleaning step")
    st.caption("Most rows go in two steps: repeated product IDs, and products outside the "
               "five segments (kurtas, shirts and women's sneakers).")

       # 3. Build checks saved in Phase 6, next to the same counts at the sidebar's settings
    st.markdown("**Checks from the build**")
    groups = products[["segment", "peer_group"]].drop_duplicates()
    small_groups = products[products["low_confidence"] == 1][["segment", "peer_group"]]
    live = {
        "Listings kept": len(products),
        "Unrated listings": int((products["has_rating"] == 0).sum()),
        "Peer groups": len(groups),
        "Peer groups under 100 listings": len(small_groups.drop_duplicates()),
        "Test candidates (gap of 8+ points)": int(products["flagged"].sum()),
        "Candidates to review first": int((products["flagged"]
                                           & (products["review_first"] == 1)).sum()),
    }
    table = checks.rename(columns={"check": "Check", "value": "At build (gap 8)"})
    table["At your settings"] = table["Check"].map(live)
    st.dataframe(table, hide_index=True, alt="Checks from the build", column_config={
        "At build (gap 8)": st.column_config.NumberColumn(format="%,d"),
        "At your settings": st.column_config.NumberColumn(format="%,d"),
    })
    st.caption(f"\"At build\" was saved when app.db was built, at the default 8-point gap. "
               f"\"At your settings\" is counted now, at the {min_gap}-point gap in the sidebar; "
               "at 8 the two columns match.")

    # 4. Known limits of the data, in plain words
    st.markdown("**Known limits**")
    st.markdown(
        "- A snapshot of the Myntra catalogue (Kaggle, CC0 licence, last updated May 2023), "
        "not live prices.\n"
        "- No sales, stock or cost data: profit figures use the cost assumptions in the sidebar.\n"
        "- 72% of listings are unrated; they stay in, marked as unrated, not as badly rated.\n"
        "- Men's Shirts is a small segment, so 5 of its 9 peer groups are low confidence.\n"
        "- A deep discount can be old stock or a sale event; the list picks tests, it does not "
        "prove lost profit.")