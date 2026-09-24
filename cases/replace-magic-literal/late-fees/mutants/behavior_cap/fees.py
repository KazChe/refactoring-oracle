"""Library late fees."""

DVD_DAILY = 1.0
BOOK_DAILY = 0.25
MAX_FEE = 16.0


def late_fee(days_late, is_dvd):
    if days_late <= 0:
        return 0.0
    rate = DVD_DAILY if is_dvd else BOOK_DAILY
    fee = days_late * rate
    if fee > MAX_FEE:
        fee = MAX_FEE
    return fee


def statement(items):
    total = sum(late_fee(days, dvd) for days, dvd in items)
    return f"{len(items)} item(s), ${total:.2f} due"
