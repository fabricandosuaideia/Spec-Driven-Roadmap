# notes-list verification

**Verdict**: PASS
**Profile**: standard
**Diff range**: 1a2b3c4..HEAD
**Round**: 1 - full
**Verifier**: independent sub-agent (author != verifier)

## Checks

| Check | Claim | Proof run | Evidence | Result |
| --- | --- | --- | --- | --- |
| C1 | listing returns notes newest first | `pytest tests/test_notes.py -k list` exit 0 | `tests/test_notes.py:30` - `assert r.status_code == 200` | PASS |

## Coverage

| Set (size) | Recomputed from | Member -> proof | Unproven |
| --- | --- | --- | --- |
| list statuses (1) | `app/notes.py` | 200 -> C1 | - |

## Faults injected

| Mutation | Location | Killed |
| --- | --- | --- |
| order asc -> desc | `app/notes.py:21` | no |
