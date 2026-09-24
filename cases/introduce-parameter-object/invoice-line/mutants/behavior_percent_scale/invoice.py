"""Invoice line math."""

from dataclasses import dataclass


@dataclass
class Line:
    unit_price: float
    quantity: int
    discount_pct: float


def line_total(line):
    gross = line.unit_price * line.quantity
    return round(gross * (1 - line.discount_pct / 10), 2)


def invoice_total(lines):
    return round(sum(line_total(line) for line in lines), 2)


def describe(unit_price, quantity, discount_pct):
    total = line_total(Line(unit_price=unit_price, quantity=quantity, discount_pct=discount_pct))
    return f"{quantity} x {unit_price:.2f} less {discount_pct}% = {total:.2f}"
