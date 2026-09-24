from refund import refund_amount, refund_message

TICKET = {"price": 80.0, "used": False}
USED = {"price": 80.0, "used": True}


def test_none_or_used():
    assert refund_amount(None, 10) == 0.0
    assert refund_amount(USED, 10) == 0.0


def test_full_and_half():
    assert refund_amount(TICKET, 7) == 80.0
    assert refund_amount(TICKET, 6) == 40.0
    assert refund_amount(TICKET, 1) == 40.0
    assert refund_amount(TICKET, 0) == 0.0


def test_message():
    assert refund_message(TICKET, 10) == "refund $80.00"
    assert refund_message(USED, 10) == "no refund"
