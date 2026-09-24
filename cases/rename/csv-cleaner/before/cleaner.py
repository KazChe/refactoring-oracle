"""Normalize column names from CSV headers."""

import re


def clean_hdr(raw):
    """Lowercase, strip, and collapse runs of non-alphanumerics into one underscore."""
    text = raw.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "column"


def clean_headers(raw_headers):
    seen = {}
    out = []
    for raw in raw_headers:
        name = clean_hdr(raw)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        out.append(name)
    return out
