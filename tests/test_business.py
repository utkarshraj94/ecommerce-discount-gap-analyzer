from src.business import break_even_loss, compare_test, contribution


# 1. Contribution: 600 selling price, minus 20% fee, minus 300 cost and 80 shipping
def test_contribution():
    assert contribution(1000, 40, 20, 300, 80) == 100


# 2. Break-even: 100 now and 140 in the test -> may lose 28.6% of units
def test_break_even():
    assert round(break_even_loss(100, 140), 1) == 28.6


# 3. No answer when the listing loses money now, or the test earns no more
def test_break_even_none():
    assert break_even_loss(0, 140) is None
    assert break_even_loss(100, 90) is None


# 4. Demo test that wins and demo test that loses
def test_demo_win():
    assert compare_test(1000, 100, 850, 140)["change"] == 19000


def test_demo_loss():
    assert compare_test(1000, 100, 650, 140)["change"] == -9000