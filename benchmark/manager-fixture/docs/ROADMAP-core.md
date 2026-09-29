# Core Arithmetic Roadmap

## Coverage

| Scope unit | Feature |
|---|---|
| C1 add two integers | core-add |

uncovered: none

## Open Questions

None.

## Expected Gray Areas

None.

## Execution Order

1. core-add

### core-add

- **objective** — `add(a, b)` in `src/calc.py` returns the sum of two integers and raises `TypeError` for anything that is not an `int` (a `bool` is not an int here), through one reusable check.
- **scope-units covered** — C1
- **depends on** — none
- **size** — Small
- **task estimate** — 1
- **implicit dimensions present** — none
- **external contract consumed** — none
- **open questions** — none
- **needs pre-written context.md** — no
