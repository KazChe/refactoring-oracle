from fees import BOOK_DAILY, DVD_DAILY, MAX_FEE, late_fee, statement


def test_rates():
    assert late_fee(4, True) == 4.0
    assert late_fee(4, False) == 1.0
    assert late_fee(0, True) == 0.0


def test_cap():
    assert late_fee(100, True) == 15.0
    assert late_fee(60, False) == 15.0


def test_statement():
    assert statement([(4, True), (4, False)]) == "2 item(s), $5.00 due"


def test_constants():
    assert (DVD_DAILY, BOOK_DAILY, MAX_FEE) == (1.0, 0.25, 15.0)
