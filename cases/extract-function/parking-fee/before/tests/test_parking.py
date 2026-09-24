from parking import fee, receipt


def test_rounds_up_to_the_hour():
    assert fee(61, 12) == 7.0


def test_daily_cap():
    assert fee(20 * 60, 12) == 24.0


def test_evening_discount_applies_after_six_and_before_six():
    assert fee(120, 19) == 5.6
    assert fee(120, 18) == 5.6
    assert fee(120, 5) == 5.6
    assert fee(120, 6) == 7.0


def test_receipt():
    assert receipt(30, 10) == "parked 30 min, due $3.50"
