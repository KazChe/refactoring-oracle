from invoice import describe, invoice_total, line_total


def test_line_total():
    assert line_total(10.0, 3, 10) == 27.0


def test_invoice_total():
    assert invoice_total([(10.0, 3, 10), (2.5, 4, 0)]) == 37.0


def test_describe():
    assert describe(10.0, 3, 10) == "3 x 10.00 less 10% = 27.00"
