import pytest

from shipping import label, quote


def test_domestic_standard():
    assert quote(2, "domestic", False) == 6.5


def test_overweight_surcharge_and_zone():
    assert quote(30, "neighbor", False) == 74.4


def test_express():
    assert quote(2, "domestic", True) == 11.75


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        quote(2, "moon", False)
    with pytest.raises(ValueError):
        quote(0, "domestic", False)


def test_label():
    assert label(2, "domestic", True) == "EXPRESS domestic 2.0kg $11.75"
