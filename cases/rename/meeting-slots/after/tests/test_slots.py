from slots import free_slots, first_gap

BUSY = [(600, 660), (720, 780)]


def test_gaps_between_meetings():
    assert free_slots(BUSY, 30) == [(540, 600), (660, 720), (780, 1020)]


def test_min_minutes_filters_short_gaps():
    assert free_slots(BUSY, 90) == [(780, 1020)]


def test_first_gap_and_none():
    assert first_gap(BUSY, 30) == (540, 600)
    assert first_gap([(540, 1020)], 1) is None


def test_gap_exactly_min_length_counts():
    assert free_slots(BUSY, 240) == [(780, 1020)]
