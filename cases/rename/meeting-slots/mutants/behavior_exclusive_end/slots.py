"""Find free meeting slots in a working day, in minutes since midnight."""

DAY_START = 9 * 60
DAY_END = 17 * 60


def free_slots(busy, min_minutes):
    """Free [start, end) intervals at least min_minutes minutes long."""
    gaps = []
    cursor = DAY_START
    for start, end in sorted(busy):
        if start - cursor >= min_minutes:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if DAY_END - cursor > min_minutes:
        gaps.append((cursor, DAY_END))
    return gaps


def first_gap(busy, min_minutes):
    gaps = free_slots(busy, min_minutes)
    return gaps[0] if gaps else None
