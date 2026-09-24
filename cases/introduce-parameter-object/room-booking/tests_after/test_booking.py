import pytest

from booking import Stay, cheapest, quote


def test_base_price():
    assert quote(Stay(room_type="standard", nights=2, guests=2, breakfast=False)) == 240.0


def test_extra_guests_and_breakfast():
    assert quote(Stay("deluxe", 3, 3, True)) == 771.0


def test_unknown_room():
    with pytest.raises(ValueError):
        quote(Stay("closet", 1, 1, False))


def test_cheapest_keeps_its_signature():
    assert cheapest(1, 1, False) == "standard"
