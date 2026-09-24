---
name: inline-function
description: Inline Function refactoring for Python. Use when asked to inline a small helper into its caller and remove the helper.
---
# Inline Function

Replace each call to a small function with the function's body, substituting the arguments for the parameters, then delete the function. The caller's behavior does not change.

Example:

```python
def _is_weekend(day):
    return day in ("sat", "sun")


def rate(day):
    if _is_weekend(day):
        return 1.5
    return 1.0
```

Inline `_is_weekend` into `rate`.

```python
def rate(day):
    if day in ("sat", "sun"):
        return 1.5
    return 1.0
```
