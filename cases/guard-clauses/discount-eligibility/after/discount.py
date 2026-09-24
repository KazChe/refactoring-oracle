"""Discount eligibility for an order."""


def discount_rate(customer, order_total, coupon):
    if customer is None:
        return 0.0
    if not customer.get("active"):
        return 0.0
    if order_total >= 100:
        return 0.2 if coupon == "SAVE20" else 0.1
    if coupon == "SAVE20":
        return 0.05
    return 0.0


def final_price(customer, order_total, coupon):
    return round(order_total * (1 - discount_rate(customer, order_total, coupon)), 2)
