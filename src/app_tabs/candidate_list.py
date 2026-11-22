"""Test candidates tab: flagged listings, the test plan and a CSV download."""

import streamlit as st

from src.app_tabs.common import add_test_columns, why_text

# Columns to show, in order: name in the data -> name on screen
COLUMNS = {
    "segment": "Segment",
    "name": "Product",
    "brand": "Brand",
    "mrp": "MRP (₹)",
    "discount_pct": "Discount (%)",
    "peer_median": "Peer median (%)",
    "gap": "Gap (points)",
    "test_discount": "Test discount (%)",
    "extra_per_sale": "Extra per sale (₹)",
    "break_even": "Break-even sales loss",
    "marks": "Marks",
    "why": "Why flagged",
    "url": "Link",
}

# How each column looks
CONFIG = {
    "Plan": st.column_config.CheckboxColumn(help="Tick to add the product to the test plan."),
    "MRP (₹)": st.column_config.NumberColumn(format="₹%,d"),
    "Discount (%)": st.column_config.NumberColumn(format="%.0f%%"),
    "Peer median (%)": st.column_config.NumberColumn(format="%.0f%%"),
    "Gap (points)": st.column_config.NumberColumn(format="%.1f"),
    "Test discount (%)": st.column_config.NumberColumn(
        format="%.0f%%", help="The peer median: the usual discount for similar listings."),
    "Extra per sale (₹)": st.column_config.NumberColumn(
        format="₹%,.0f", help="Contribution in the test minus contribution now, per sale."),
    "Break-even sales loss": st.column_config.TextColumn(
        help="How many sales (%) the test can lose and still earn the same."),
    "Why flagged": st.column_config.TextColumn(width="large"),
    "Link": st.column_config.LinkColumn(display_text="Open"),
}


# 1. Build the table for some listings: test columns, marks, sentence, screen names
def make_table(rows, min_gap, fee_pct, cost_pct, shipping):
    table = add_test_columns(rows, fee_pct, cost_pct, shipping)
    marks = []
    for low, review in zip(table["low_confidence"], table["review_first"]):
        words = []
        if low == 1:
            words.append("Low confidence")
        if review == 1:
            words.append("Review first")
        marks.append(", ".join(words))
    table["marks"] = marks
    table["why"] = table.apply(why_text, axis=1, min_gap=min_gap)
    table = table.round({"discount_pct": 1, "peer_median": 1, "extra_per_sale": 0})
    table = table.sort_values("gap", ascending=False)
    table = table.set_index("product_id")
    table = table[list(COLUMNS)].rename(columns=COLUMNS)
    return table


def show(selected, products, segment, min_gap, fee_pct, cost_pct, shipping):
    st.subheader("Test candidates")
    st.warning("A deep discount can mean old stock or a sale event. This list picks products "
               "worth an A/B test with a smaller discount; it is not proof of lost profit.",
               icon=":material/warning:")

    # 2. Flagged listings in this segment, largest gap first
    flagged = selected[selected["flagged"]]
    if len(flagged) == 0:
        st.info("No listings meet this gap. Lower the minimum gap in the sidebar.",
                icon=":material/info:")
    else:
        table = make_table(flagged, min_gap, fee_pct, cost_pct, shipping)
        table = table.drop(columns=["Segment"])
        table.insert(0, "Plan", table.index.isin(st.session_state["plan"]))
        st.caption(f"{len(table):,} candidates, largest gap first. Tick Plan to add a product "
                   f"to the test plan. Assumptions: cost {cost_pct}% of MRP, fee {fee_pct}%, "
                   f"shipping ₹{shipping}.")
        edited = st.data_editor(
            table, key=f"editor_{segment}_{min_gap}", hide_index=True,
            disabled=list(table.columns.drop("Plan")), column_config=CONFIG,
            alt=f"Test candidates in {segment}")

        # 3. Save the ticks: keep plan products not shown here, then add the ticked ones
        shown_ids = list(edited.index)
        kept = [pid for pid in st.session_state["plan"] if pid not in shown_ids]
        ticked = list(edited.index[edited["Plan"]])
        st.session_state["plan"] = kept + ticked

    # 4. The test plan from all segments, with a CSV download
    st.subheader("Test plan")
    plan_rows = products[products["product_id"].isin(st.session_state["plan"])]
    if len(plan_rows) == 0:
        st.info("No products selected yet. Tick Plan in the table above.",
                icon=":material/info:")
        return
    plan_table = make_table(plan_rows, min_gap, fee_pct, cost_pct, shipping)
    st.dataframe(plan_table, hide_index=True, column_config=CONFIG, alt="Test plan")
    st.download_button("Download test plan (CSV)", plan_table.to_csv(),
                       file_name="test_plan.csv", mime="text/csv",
                       icon=":material/download:")