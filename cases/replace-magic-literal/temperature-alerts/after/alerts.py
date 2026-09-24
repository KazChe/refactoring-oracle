"""Server temperature alerts."""

CRITICAL_C = 85
WARNING_C = 70


def status(celsius):
    if celsius >= CRITICAL_C:
        return "critical"
    if celsius >= WARNING_C:
        return "warning"
    return "ok"


def summarize(readings):
    counts = {"ok": 0, "warning": 0, "critical": 0}
    for reading in readings:
        counts[status(reading)] += 1
    return counts
