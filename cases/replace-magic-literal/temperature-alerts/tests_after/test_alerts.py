from alerts import CRITICAL_C, WARNING_C, status, summarize


def test_thresholds_are_inclusive():
    assert status(84.9) == "warning"
    assert status(85) == "critical"
    assert status(69.9) == "ok"
    assert status(70) == "warning"


def test_summarize():
    assert summarize([20, 70, 90, 91]) == {"ok": 1, "warning": 1, "critical": 2}


def test_constants():
    assert (CRITICAL_C, WARNING_C) == (85, 70)
