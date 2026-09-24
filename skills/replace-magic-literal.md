---
name: replace-magic-literal
description: Replace Magic Literal with Constant refactoring for Python. Use when asked to replace numeric literals with named module-level constants.
---
# Replace Magic Literal with Constant

Define a named constant at module level with the literal's value, and use the constant everywhere the literal carried that meaning. The value does not change.

Example:

```python
def is_adult(age):
    return age >= 18
```

Replace the magic number with a constant `ADULT_AGE`.

```python
ADULT_AGE = 18


def is_adult(age):
    return age >= ADULT_AGE
```
