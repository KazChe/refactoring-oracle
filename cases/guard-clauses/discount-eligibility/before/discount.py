"""Discount eligibility for an order."""


def discount_rate(customer, order_total, coupon):
    rate = 0.0
    if customer is not None:
        if customer.get("active"):
            if order_total >= 100:
                if coupon == "SAVE20":
                    rate = 0.2
                else:
                    rate = 0.1
            else:
                if coupon == "SAVE20":
                    rate = 0.05
    return rate


def final_price(customer, order_total, coupon):
    return round(order_total * (1 - discount_rate(customer, order_total, coupon)), 2)
