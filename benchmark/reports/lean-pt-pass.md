# item-create verificação

**Verdict**: PASS
**Profile**: standard
**Diff range**: a1b2c3d..HEAD
**Round**: 1 - full
**Verifier**: independent sub-agent (author != verifier)

## Checks

| Check | Claim | Proof run | Evidence | Result |
| --- | --- | --- | --- | --- |
| C1 | criar um item devolve 201 e o título gravado | `pytest tests/test_items.py -k create` exit 0 | `tests/test_items.py:41` - `assert r.status_code == 201` | PASS |
| C2 | título em branco é recusado com 422 | `pytest tests/test_items.py -k blank` exit 0 | `tests/test_items.py:58` - `assert r.status_code == 422` | PASS |

## Coverage

| Set (size) | Recomputed from | Member -> proof | Unproven |
| --- | --- | --- | --- |
| statuses de criação (2) | `app/routers/items.py` | 201 -> C1, 422 -> C2 | - |

## Faults injected

| Mutation | Location | Killed |
| --- | --- | --- |
| status 201 -> 200 | `app/routers/items.py:37` | yes |

Nota: a suíte roda em 4 s; nenhum teste foi alterado durante a verificação.
