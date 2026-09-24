from invoice import Line, describe, invoice_total, line_total


def test_line_total():
    assert line_total(Line(unit_price=10.0, quantity=3, discount_pct=10)) == 27.0


def test_invoice_total():
    lines = [Line(10.0, 3, 10), Line(2.5, 4, 0)]
    assert invoice_total(lines) == 37.0


def test_describe_keeps_its_signature():
    assert describe(10.0, 3, 10) == "3 x 10.00 less 10% = 27.00"
