"""Calculator tab: profit per sale now and with a smaller discount."""

import altair as alt
import pandas as pd
import streamlit as st

from src.app_tabs.common import break_even_text, rupees
from src.business import break_even_loss, contribution


def show(fee_pct, cost_pct, shipping):
    st.subheader("Profit calculator")
    st.caption(f"Try one product. The marketplace fee ({fee_pct}%) comes from the sidebar. "
               "Cost and shipping start from the sidebar too and can be changed here.")

    # 1. Price inputs on one row
    col1, col2, col3 = st.columns(3)
    mrp = col1.number_input("MRP (₹)", min_value=100, max_value=100000, value=1000, step=50)
    current_discount = col2.number_input("Current discount (%)", 0, 90, 40)
    test_discount = col3.number_input("Test discount (%)", 0, 90, 30)

    # 2. Cost inputs on a second row (defaults come from the sidebar assumptions)
    col4, col5, col6 = st.columns(3)
    cost = col4.number_input("Product cost (₹)", 0, 100000, round(mrp * cost_pct / 100),
                             step=10, help="Assumption. Starts at the sidebar's cost % of MRP.")
    ship = col5.number_input("Shipping per order (₹)", 0, 2000, shipping, step=10)
    col6.metric("Marketplace fee", f"{fee_pct}%")

    # 3. Contribution of one sale now and in the test (formulas from src/business.py)
    c_now = contribution(mrp, current_discount, fee_pct, cost, ship)
    c_test = contribution(mrp, test_discount, fee_pct, cost, ship)
    result = break_even_text(c_now, c_test, current_discount, test_discount)

    with st.container(horizontal=True):
        st.metric("Contribution now (per sale)", rupees(c_now), border=True)
        st.metric("Contribution in test (per sale)", rupees(c_test), border=True)
        st.metric("Break-even sales loss", result, border=True)

    # 4. One plain sentence that reads the result; stop here if there is no number
    loss = break_even_loss(c_now, c_test)
    if loss is None:
        st.warning(f"No break-even number: {result.lower()}.", icon=":material/warning:")
        return
    st.info(f"The test earns more as long as sales fall by less than {loss:.1f}%.",
            icon=":material/info:")

    # 5. Chart data: profit change for 11 sales-fall steps (0% to 50%), per 100 sales today
    falls = list(range(0, 55, 5))
    changes = []
    results = []
    meanings = []
    for fall in falls:
        change = 100 * (1 - fall / 100) * c_test - 100 * c_now
        changes.append(change)
        if fall == 0:
            start = "If sales stay the same"
        else:
            start = f"If sales fall {fall}%"
        if change >= 0:
            results.append("Earns more")
            meanings.append(f"{start}, the test earns {rupees(change)} more than today "
                            "(per 100 sales today).")
        else:
            results.append("Earns less")
            meanings.append(f"{start}, the test earns {rupees(-change)} less than today "
                            "(per 100 sales today).")
    chart_data = pd.DataFrame({
        "Sales fall (%)": falls,
        "Profit change (₹)": changes,
        "Result": results,
        "What it means": meanings,
    })

    # 6. Bar chart: green above zero, red below; the tooltip shows only the sentence
    colours = alt.Scale(domain=["Earns more", "Earns less"], range=["#2E9E5B", "#D64545"])
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Sales fall (%):O", title="Sales fall (%)", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Profit change (₹):Q", title="Extra profit vs today, per 100 sales (₹)"),
        color=alt.Color("Result:N", scale=colours, legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip("What it means:N")],
    )
    st.altair_chart(chart, alt="Profit change for sales falls from 0% to 50%")