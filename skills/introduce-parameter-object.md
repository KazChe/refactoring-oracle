---
name: introduce-parameter-object
description: Introduce Parameter Object refactoring for Python. Use when asked to group function parameters into a dataclass.
---
# Introduce Parameter Object

Replace a group of parameters with one instance of a new dataclass that has those parameters as fields. Callers construct the object. Inside the function, reads of the old parameters become attribute reads.

Example:

```python
def area(width, height):
    return width * height


print(area(3, 4))
```

Introduce Parameter Object called `Rect` for `width`, `height`.

```python
from dataclasses import dataclass


@dataclass
class Rect:
    width: float
    height: float


def area(rect):
    return rect.width * rect.height


print(area(Rect(width=3, height=4)))
```
