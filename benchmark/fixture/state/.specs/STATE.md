# STATE

## Decisions

- **AD-001** (2026-06-02): votes are counted by aggregation on read, never a cached counter.
  Rationale: the pilot's write volume is trivial and a counter is one more thing to reconcile.
- **AD-002** (2026-07-18): outbound e-mail goes through the SMTP relay already required by sign-up;
  no provider SDK is compiled into the container.

## Handoff

- **Feature**: pauta-item-voting
- **Phase**: Execute
- **Completed**: T1
- **In-progress** (file:line): api/app/routers/items.py:63
- **Next step**: finish T2, then dispatch validation
- **Blockers**: none
- **Branch**: main
- **Uncommitted files**: none
