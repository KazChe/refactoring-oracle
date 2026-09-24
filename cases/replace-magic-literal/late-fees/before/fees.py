"""Library late fees."""


def late_fee(days_late, is_dvd):
    if days_late <= 0:
        return 0.0
    rate = 1.0 if is_dvd else 0.25
    fee = days_late * rate
    if fee > 15.0:
        fee = 15.0
    return fee


def statement(items):
    total = sum(late_fee(days, dvd) for days, dvd in items)
    return f"{len(items)} item(s), ${total:.2f} due"
