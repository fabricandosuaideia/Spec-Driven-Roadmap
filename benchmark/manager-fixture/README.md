# The manager-mode fixture

A tiny multi-section git project for **executing** manager mode — `scripts/manager-pipeline.js`,
launched with the args `scripts/plan-pipeline.py --manager` prints — with real agents. Scenario
`manager-build` sets it up with `tlc-spec-lean` installed.

Two sections in `docs/ROADMAP-INDEX.md`: `core`, already decomposed (one feature), and `money`, not
decomposed, whose source in `docs/PRD.md` leaves one thing open on purpose — how a negative amount is
shown. Nobody is there to ask: the run must decide it under the delegation written in
`docs/process/pipeline.json`, mark it **Decided by the manager**, and build on that decision.

What a correct run shows is in [`../expected.md`](../expected.md), section `manager-build`.
