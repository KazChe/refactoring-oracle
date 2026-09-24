---
name: guard-clauses
description: Replace Nested Conditional with Guard Clauses refactoring for Python. Use when asked to flatten nested ifs into early returns.
---
# Replace Nested Conditional with Guard Clauses

Turn each special case into an early return at the top of the function, so the normal path is not nested. The set of inputs mapped to each result stays exactly the same.

Example:

```python
def shipping(order):
    cost = 0
    if order is not None:
        if order["total"] < 50:
            cost = 5
    return cost
```

Rewrite `shipping` with guard clauses.

```python
def shipping(order):
    if order is None:
        return 0
    if order["total"] >= 50:
        return 0
    return 5
```
