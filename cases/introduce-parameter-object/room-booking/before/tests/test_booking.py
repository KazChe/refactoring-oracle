import pytest

from booking import cheapest, quote


def test_base_price():
    assert quote("standard", 2, 2, False) == 240.0


def test_extra_guests_and_breakfast():
    assert quote("deluxe", 3, 3, True) == 771.0


def test_unknown_room():
    with pytest.raises(ValueError):
        quote("closet", 1, 1, False)


def test_cheapest():
    assert cheapest(1, 1, False) == "standard"
