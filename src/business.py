"""Business rules: shared settings and the profit formulas."""

MIN_GAP = 8            # points above the peer median before a listing is a test candidate
MIN_GROUP_SIZE = 100   # peer groups smaller than this are low confidence


# 1. Contribution of one sale: what is left after the fee, the cost and shipping
def contribution(mrp, discount_pct, fee_pct, cost, shipping):
    selling_price = mrp * (1 - discount_pct / 100)
    return selling_price * (1 - fee_pct / 100) - cost - shipping


# 2. Break-even sales loss: the % of units a smaller discount can lose and still earn the same
def break_even_loss(c_now, c_test):
    if c_now <= 0 or c_test <= c_now:
        return None
    return (1 - c_now / c_test) * 100


# 3. Compare a finished A/B test: total contribution in each group and the change
def compare_test(control_units, control_contribution, test_units, test_contribution):
    control_total = control_units * control_contribution
    test_total = test_units * test_contribution
    return {
        "control_total": control_total,
        "test_total": test_total,
        "change": test_total - control_total,
    }


def main():
    # 4. Quick check with the plan's example: MRP 1000, fee 20%, cost 300, shipping 80
    c_now = contribution(1000, 40, 20, 300, 80)
    c_test = contribution(1000, 30, 20, 300, 80)
    print("Contribution now (40% off):", c_now)
    print("Contribution in test (30% off):", c_test)
    print("Break-even sales loss %:", round(break_even_loss(c_now, c_test), 1))
    print("Test result:", compare_test(1000, 100, 850, 140))


if __name__ == "__main__":
    main()