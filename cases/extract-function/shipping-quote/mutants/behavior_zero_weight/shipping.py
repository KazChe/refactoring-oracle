"""Shipping quotes by weight and destination zone."""

ZONE_RATES = {"domestic": 1.0, "neighbor": 1.6, "overseas": 2.9}


def validate(weight_kg, zone):
    if zone not in ZONE_RATES:
        raise ValueError(f"unknown zone {zone!r}")
    if weight_kg < 0:
        raise ValueError("weight must be positive")


def quote(weight_kg, zone, express):
    validate(weight_kg, zone)
    base = 4.0 + 1.25 * weight_kg
    if weight_kg > 20:
        base += (weight_kg - 20) * 0.5
    price = base * ZONE_RATES[zone]
    if express:
        price = price * 1.5 + 2.0
    return round(price, 2)


def label(weight_kg, zone, express):
    tag = "EXPRESS" if express else "STANDARD"
    return f"{tag} {zone} {weight_kg:.1f}kg ${quote(weight_kg, zone, express):.2f}"
