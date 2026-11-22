"""Small helpers shared by the app tabs."""

from src.business import break_even_loss, contribution


# 1. Money in rupees with Indian digit grouping, for example ₹1,29,900
def rupees(amount):
    sign = "-" if amount < 0 else ""
    digits = str(round(abs(amount)))
    if len(digits) > 3:
        head = digits[:-3]
        tail = digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"{sign}₹{digits}"


# 2. Break-even sales loss as text: the mockup's edge cases, otherwise a %
def break_even_text(c_now, c_test, current_discount, test_discount):
    if test_discount >= current_discount:
        return "No discount cut"
    if c_test <= 0:
        return "Still loses money"
    if c_now <= 0:
        return "Loses money now"
    return f"{break_even_loss(c_now, c_test):.1f}%"


# 3. Why-flagged sentence with the slider's minimum gap (same wording as Phase 6)
def why_text(row, min_gap):
    discount = f"{row['discount_pct']:.0f}% off"
    median = f"{row['peer_median']:.0f}%"
    if row["flagged"]:
        text = (f"{discount} is {row['gap']:.1f} points above the {median} median of "
                f"{row['n_listings']} similar listings; the middle half of them give "
                f"{row['peer_q25']:.0f}% to {row['peer_q75']:.0f}% off.")
    elif row["gap"] > 0:
        text = (f"Not flagged: {discount} is {row['gap']:.1f} points above the {median} "
                f"peer median, under the {min_gap}-point minimum.")
    else:
        text = f"Not flagged: {discount} is at or below the {median} peer median."
    if row["low_confidence"] == 1:
        text += f" Low confidence: only {row['n_listings']} listings in this peer group."
    if row["review_first"] == 1:
        text += " Review first: Phase 5 marked this listing as unusual."
    return text


# 4. Test columns: test discount = peer median, then profit per sale now and in the test
def add_test_columns(df, fee_pct, cost_pct, shipping):
    df = df.copy()
    df["test_discount"] = df["peer_median"].round()
    df["cost"] = df["mrp"] * cost_pct / 100
    c_now = contribution(df["mrp"], df["discount_pct"], fee_pct, df["cost"], shipping)
    c_test = contribution(df["mrp"], df["test_discount"], fee_pct, df["cost"], shipping)
    df["extra_per_sale"] = c_test - c_now
    break_even = []
    for now, test, current, new in zip(c_now, c_test, df["discount_pct"], df["test_discount"]):
        break_even.append(break_even_text(now, test, current, new))
    df["break_even"] = break_even
    return df