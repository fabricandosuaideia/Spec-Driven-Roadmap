# item-create verification

**Verdict**: PASS
**Profile**: standard
**Diff range**: a1b2c3d..HEAD
**Round**: 1 - full
**Verifier**: independent sub-agent (author != verifier)

## Checks

| Check | Claim | Proof run | Evidence | Result |
| --- | --- | --- | --- | --- |
| C1 | creating an item returns 201 and the stored title | `pytest tests/test_items.py -k create` exit 0 | `tests/test_items.py:41` - `assert r.status_code == 201` | PASS |
| C2 | a blank title is rejected with 422 | `pytest tests/test_items.py -k blank` exit 0 | `tests/test_items.py:58` - `assert r.status_code == 422` | PASS |

## Coverage

| Set (size) | Recomputed from | Member -> proof | Unproven |
| --- | --- | --- | --- |
| item create statuses (2) | `app/routers/items.py` | 201 -> C1, 422 -> C2 | - |

## Faults injected

| Mutation | Location | Killed |
| --- | --- | --- |
| status 201 -> 200 | `app/routers/items.py:37` | yes |
| drop the blank-title guard | `app/services/items.py:22` | yes |
