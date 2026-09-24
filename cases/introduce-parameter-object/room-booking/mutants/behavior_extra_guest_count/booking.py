"""Hotel room booking quote."""

from dataclasses import dataclass

NIGHTLY = {"standard": 120.0, "deluxe": 190.0, "suite": 310.0}


@dataclass
class Stay:
    room_type: str
    nights: int
    guests: int
    breakfast: bool


def quote(stay):
    if stay.room_type not in NIGHTLY:
        raise ValueError(f"unknown room {stay.room_type!r}")
    price = NIGHTLY[stay.room_type] * stay.nights
    if stay.guests > 2:
        price += 25.0 * (stay.guests - 1) * stay.nights
    if stay.breakfast:
        price += 14.0 * stay.guests * stay.nights
    return round(price, 2)


def cheapest(nights, guests, breakfast):
    return min(NIGHTLY, key=lambda room: quote(Stay(room, nights, guests, breakfast)))
