from discount import discount_rate, final_price

ACTIVE = {"active": True}
INACTIVE = {"active": False}


def test_no_customer_or_inactive():
    assert discount_rate(None, 500, "SAVE20") == 0.0
    assert discount_rate(INACTIVE, 500, "SAVE20") == 0.0


def test_large_orders():
    assert discount_rate(ACTIVE, 100, "SAVE20") == 0.2
    assert discount_rate(ACTIVE, 100, None) == 0.1


def test_small_orders():
    assert discount_rate(ACTIVE, 99.99, "SAVE20") == 0.05
    assert discount_rate(ACTIVE, 99.99, None) == 0.0


def test_final_price():
    assert final_price(ACTIVE, 200, "SAVE20") == 160.0
