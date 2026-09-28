# notes-create verification

**Verdict**: PASS
**Profile**: standard
**Diff range**: 1a2b3c4..HEAD
**Round**: 1 - full
**Verifier**: independent sub-agent (author != verifier)

## Checks

| Check | Claim | Proof run | Evidence | Result |
| --- | --- | --- | --- | --- |
| C1 | creating a note returns 201 | `pytest tests/test_notes.py -k create` exit 0 | `tests/test_notes.py:12` - `assert r.status_code == 201` | PASS |

## Coverage

| Set (size) | Recomputed from | Member -> proof | Unproven |
| --- | --- | --- | --- |
| create statuses (1) | `app/notes.py` | 201 -> C1 | - |

## Faults injected

| Mutation | Location | Killed |
| --- | --- | --- |
| status 201 -> 200 | `app/notes.py:9` | yes |
