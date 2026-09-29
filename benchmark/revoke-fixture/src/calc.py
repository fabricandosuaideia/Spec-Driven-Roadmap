"""A tiny calculator."""


def div(a, b):
    """Integer division, rounding down. Division by zero returns None."""
    if b == 0:
        return None
    return a // b
