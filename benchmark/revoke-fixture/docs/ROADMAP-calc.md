# Calculator Roadmap

## Coverage

| Scope unit | Feature |
|---|---|
| D1 division by zero is an error | calc-div-raise |

uncovered: none

## Open Questions

- `calc-div-raise` · status: answered — What does `div(a, 0)` do? **Answer (owner, 2026-09-29):** it raises `ZeroDivisionError`. Returning `None` is revoked: callers were silently carrying `None` into totals.

## Expected Gray Areas

None.

## Execution Order

1. calc-div-raise

### calc-div-raise

- **objective** — `div(a, 0)` in `src/calc.py` raises `ZeroDivisionError` instead of returning `None`; every other division is unchanged.
- **scope-units covered** — D1
- **depends on** — none
- **size** — Small
- **task estimate** — 1
- **implicit dimensions present** — none
- **external contract consumed** — none
- **open questions** —
  - status: answered — What does `div(a, 0)` do? **Answer (owner, 2026-09-29):** it raises `ZeroDivisionError`. Returning `None` is revoked: callers were silently carrying `None` into totals.
- **needs pre-written context.md** — no
