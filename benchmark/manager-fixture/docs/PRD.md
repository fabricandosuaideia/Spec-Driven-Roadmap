# Calc toolkit — PRD

A small Python library, `src/calc.py`, used by a shop's back office.

## 1. Core arithmetic

- C1. `add(a, b)` returns the sum of two integers. Anything that is not an `int` raises `TypeError`
  (a `bool` is not an int here).

## 2. Money formatting

- M1. `format_brl(cents)` turns an integer amount of cents into Brazilian reais text: `123456` becomes
  `R$ 1.234,56`, `5` becomes `R$ 0,05`. It reuses the core section's integer check.
- M2. Refunds are stored as negative amounts and must be shown too.
