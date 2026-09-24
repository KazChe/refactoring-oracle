import pytest

from loyalty import Ledger


def test_purchase_earns_whole_dollars_times_rate():
    ledger = Ledger()
    assert ledger.purchase(12.99) == 24
    assert ledger.balance == 24
    assert ledger.history == [("earn", 24)]


def test_redeem():
    ledger = Ledger()
    ledger.purchase(50)
    assert ledger.redeem(30) == 70
    with pytest.raises(ValueError):
        ledger.redeem(1000)
