# The revoked-test fixture

A tiny one-section git project for **executing** manager mode's one test exception with real agents.
Scenario `manager-revoke` sets it up with `tlc-spec-lean` installed.

`src/calc.py`'s `div(a, 0)` returns `None`, and `tests/test_calc.py` asserts exactly that. The only
feature, `calc-div-raise`, changes it to raise `ZeroDivisionError`, and its open question carries the
owner's answer revoking the old behaviour. Nobody is there: in manager mode the builder may correct
that one assertion — in its own commit quoting the decision, at the same strength — and the
independent verifier must confirm it. `test_div_floors`, in the same file, is not revoked and must come
out untouched.

What a correct run shows is in [`../expected.md`](../expected.md), section `manager-revoke`.
