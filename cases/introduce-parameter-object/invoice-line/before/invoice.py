"""Invoice line math."""


def line_total(unit_price, quantity, discount_pct):
    gross = unit_price * quantity
    return round(gross * (1 - discount_pct / 100), 2)


def invoice_total(lines):
    return round(sum(line_total(p, q, d) for p, q, d in lines), 2)


def describe(unit_price, quantity, discount_pct):
    total = line_total(unit_price, quantity, discount_pct)
    return f"{quantity} x {unit_price:.2f} less {discount_pct}% = {total:.2f}"
