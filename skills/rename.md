---
name: rename
description: Rename refactoring for Python. Use when asked to rename a function, parameter, or variable everywhere it is used.
---
# Rename

Change a name at its definition and at every use, including call sites, keyword arguments, docstrings, and tests that reference it. Only the name changes.

Example:

```python
def calc(amt, pct):
    """Apply pct to amt."""
    return amt * pct / 100


def tax(amt):
    return calc(amt, 8)
```

Rename `calc` to `apply_percent` and `amt` to `amount`.

```python
def apply_percent(amount, pct):
    """Apply pct to amount."""
    return amount * pct / 100


def tax(amount):
    return apply_percent(amount, 8)
```
