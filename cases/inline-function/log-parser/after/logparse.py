"""Parse simple 'LEVEL message' log lines."""

LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")


def parse_line(line):
    head, _, rest = line.partition(" ")
    if head in LEVELS:
        return {"level": head, "message": rest.strip()}
    return {"level": "INFO", "message": line.strip()}


def count_levels(lines):
    counts = {level: 0 for level in LEVELS}
    for line in lines:
        counts[parse_line(line)["level"]] += 1
    return counts
