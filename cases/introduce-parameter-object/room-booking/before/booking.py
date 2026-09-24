"""Hotel room booking quote."""

NIGHTLY = {"standard": 120.0, "deluxe": 190.0, "suite": 310.0}


def quote(room_type, nights, guests, breakfast):
    if room_type not in NIGHTLY:
        raise ValueError(f"unknown room {room_type!r}")
    price = NIGHTLY[room_type] * nights
    if guests > 2:
        price += 25.0 * (guests - 2) * nights
    if breakfast:
        price += 14.0 * guests * nights
    return round(price, 2)


def cheapest(nights, guests, breakfast):
    return min(NIGHTLY, key=lambda room: quote(room, nights, guests, breakfast))
