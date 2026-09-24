---
name: extract-function
description: Extract Function refactoring for Python. Use when asked to extract a block of statements into a new function and call it from the original place.
---
# Extract Function

Move a contiguous block of statements out of a function into a new function whose parameters are the variables the block reads and whose return value is what the rest of the original function needs. Replace the block with a call. Nothing else changes.

Example:

```python
def greeting(name, hour):
    if hour < 12:
        part = "morning"
    elif hour < 18:
        part = "afternoon"
    else:
        part = "evening"
    return f"Good {part}, {name}."
```

Extract the time-of-day choice into `day_part(hour)`.

```python
def day_part(hour):
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


def greeting(name, hour):
    return f"Good {day_part(hour)}, {name}."
```
