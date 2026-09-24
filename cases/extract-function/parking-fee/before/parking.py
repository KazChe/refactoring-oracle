"""Parking fee for a garage with an evening discount."""

HOURLY = 3.5
DAILY_CAP = 24.0


def fee(minutes, entered_hour):
    hours = -(-minutes // 60)
    base = hours * HOURLY
    if base > DAILY_CAP:
        base = DAILY_CAP
    if entered_hour >= 18 or entered_hour < 6:
        base = round(base * 0.8, 2)
    return base


def receipt(minutes, entered_hour):
    return f"parked {minutes} min, due ${fee(minutes, entered_hour):.2f}"
