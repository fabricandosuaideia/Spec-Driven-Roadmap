# The unblock fixture

A tiny **single-section** git project for executing manager mode at level `unblock` with real agents.
Scenario `manager-unblock` sets it up with `tlc-spec-lean` installed.

One feature to build (`calc-add`), and a defect that predates it: `src/tags.py`'s `unique_tags()`
promises alphabetical order and returns `list(set(...))`, whose order depends on Python's hash seed.
`tests/test_tags.py` asserts the promise. The per-feature gate (`gate.sh`) runs only the calculator's
tests; the batch barrier (`barrier.sh`) runs everything with `PYTHONHASHSEED=2`, under which the order
comes out wrong — so the barrier is red after `calc-add` merges, deterministically, for a reason that
has nothing to do with `calc-add`.

At level `unblock` the run must triage it (`triage-probe.py`: it fails before the merge too, so
**preexisting**), repair the cause in the code — not by loosening the test — have the repair checked,
merge it, and see the barrier green. What a correct run shows is in [`../expected.md`](../expected.md),
section `manager-unblock`.
