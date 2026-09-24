from slots import find_gaps, first_gap

BUSY = [(600, 660), (720, 780)]


def test_gaps_between_meetings():
    assert find_gaps(BUSY, 30) == [(540, 600), (660, 720), (780, 1020)]


def test_min_len_filters_short_gaps():
    assert find_gaps(BUSY, 90) == [(780, 1020)]


def test_first_gap_and_none():
    assert first_gap(BUSY, 30) == (540, 600)
    assert first_gap([(540, 1020)], 1) is None


def test_gap_exactly_min_length_counts():
    assert find_gaps(BUSY, 240) == [(780, 1020)]
