from logparse import count_levels, parse_line


def test_parses_level_and_message():
    assert parse_line("WARN disk at 91%") == {"level": "WARN", "message": "disk at 91%"}


def test_defaults_to_info():
    assert parse_line("started up  ") == {"level": "INFO", "message": "started up"}


def test_lowercase_level_is_not_a_level():
    assert parse_line("error boom")["level"] == "INFO"


def test_count_levels():
    lines = ["INFO a", "ERROR b", "ERROR c", "plain"]
    assert count_levels(lines) == {"DEBUG": 0, "INFO": 2, "WARN": 0, "ERROR": 2}
