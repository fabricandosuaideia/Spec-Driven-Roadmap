# item-create verification

**Verdict**: PASS
**Profile**: standard
**Diff range**: a1b2c3d..HEAD
**Round**: 1 - full
**Verifier**: independent sub-agent (author != verifier)

## Checks

| Check | Claim | Proof run | Evidence | Result |
| --- | --- | --- | --- | --- |
| C1 | creating an item returns 201 and the stored title | `pytest -k create` exit 0 | the create test | PASS |
| C2 | a blank title is rejected with 422 | `pytest -k blank` exit 0 | the blank-title test | PASS |

## Coverage

| Set (size) | Recomputed from | Member -> proof | Unproven |
| --- | --- | --- | --- |
| item create statuses (2) | the router | 201 -> C1, 422 -> C2 | - |

## Faults injected

| Mutation | Location | Killed |
| --- | --- | --- |
| status 201 -> 200 | the router | yes |
