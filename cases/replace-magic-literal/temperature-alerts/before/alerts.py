"""Server temperature alerts."""


def status(celsius):
    if celsius >= 85:
        return "critical"
    if celsius >= 70:
        return "warning"
    return "ok"


def summarize(readings):
    counts = {"ok": 0, "warning": 0, "critical": 0}
    for reading in readings:
        counts[status(reading)] += 1
    return counts
