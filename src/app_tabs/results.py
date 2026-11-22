"""Test results tab: read a finished A/B test (current price against the test price)."""

import streamlit as st

from src.app_tabs.common import rupees
from src.business import break_even_loss, compare_test

# Sample numbers for the two demo buttons: units and contribution per unit, current then test
GAIN_DEMO = {"control_units": 1000, "control_contribution": 100,
             "test_units": 850, "test_contribution": 140}
LOSS_DEMO = {"control_units": 1000, "control_contribution": 100,
             "test_units": 700, "test_contribution": 130}


# 1. Put a set of numbers into the four input boxes (runs when a demo button is clicked)
def fill(numbers):
    for key in numbers:
        st.session_state[key] = numbers[key]


def show():
    st.subheader("Test results")
    st.caption("Enter the result of a finished test. Contribution per unit is what one sale "
               "earns after fee, cost and shipping; the Calculator tab works it out.")

    # 2. Start with the gain demo the first time the tab is drawn
    if "control_units" not in st.session_state:
        fill(GAIN_DEMO)

    # 3. Two demo buttons fill sample numbers (sample data, not real results)
    with st.container(horizontal=True):
        st.button("Demo: test wins", on_click=fill, args=(GAIN_DEMO,), icon=":material/trending_up:")
        st.button("Demo: test loses", on_click=fill, args=(LOSS_DEMO,),
                  icon=":material/trending_down:")
    st.caption("The demo numbers are sample data, not results from this catalogue.")

    # 4. The four inputs: current price group and test price group
    col1, col2 = st.columns(2, border=True)
    with col1:
        st.markdown("**Current discount (control)**")
        control_units = st.number_input("Units sold", min_value=0, step=10, key="control_units")
        control_contribution = st.number_input("Contribution per unit (₹)", step=5,
                                               key="control_contribution")
    with col2:
        st.markdown("**Smaller discount (test)**")
        test_units = st.number_input("Units sold", min_value=0, step=10, key="test_units")
        test_contribution = st.number_input("Contribution per unit (₹)", step=5,
                                            key="test_contribution")

    # 5. Guard against inputs that cannot be read
    if control_units == 0:
        st.info("Enter the units sold at the current discount to read the test.",
                icon=":material/info:")
        return

    # 6. Totals and changes (compare_test and break_even_loss come from src/business.py)
    result = compare_test(control_units, control_contribution, test_units, test_contribution)
    unit_change = (test_units - control_units) / control_units * 100
    loss_allowed = break_even_loss(control_contribution, test_contribution)
    if loss_allowed is None:
        break_even_label = "No per-unit gain"
    else:
        break_even_label = f"{loss_allowed:.1f}%"

    with st.container(horizontal=True):
        st.metric("Unit change", f"{unit_change:+.1f}%", border=True)
        st.metric("Break-even sales loss", break_even_label, border=True)
        st.metric("Total now", rupees(result["control_total"]), border=True)
        st.metric("Total in test", rupees(result["test_total"]), border=True)
        st.metric("Change", rupees(result["change"]), border=True)

    # 7. Win or loss message in plain words
    change_text = rupees(abs(result["change"]))
    if result["control_total"] > 0:
        change_pct = abs(result["change"]) / result["control_total"] * 100
        change_text = f"{change_text} ({change_pct:.0f}%)"
    if loss_allowed is None:
        units_text = f"Units changed by {unit_change:+.1f}%."
    else:
        units_text = (f"Units changed by {unit_change:+.1f}%; the test could lose up to "
                      f"{loss_allowed:.1f}% of units and still earn the same.")
    if result["change"] > 0:
        st.success(f"The test wins: it earns {change_text} more. {units_text}",
                   icon=":material/check_circle:")
    elif result["change"] < 0:
        st.error(f"The test loses: it earns {change_text} less. {units_text}",
                 icon=":material/cancel:")
    else:
        st.info(f"No difference in total contribution. {units_text}", icon=":material/info:")