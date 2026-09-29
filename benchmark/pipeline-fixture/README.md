# The pipeline fixture

A tiny git project for **executing** option C — `scripts/roadmap-pipeline.js`, launched with the args
`scripts/plan-pipeline.py` prints — with real agents. Scenario `pipeline-build` sets it up with
`tlc-spec-lean` installed. Two small features (`calc-add`, then `calc-sub`, which depends on it), a
feature gate (`gate.sh`) that takes longer than one of the pipeline's waits, and a separate batch
barrier (`barrier.sh`).

**Why it exists.** The pipeline's first real run (a user's project, 2026-09-29) built its first feature
and never proved it: the Workflow harness relays the launch request to every agent as the user's
voice, so provers ran `plan-pipeline.py` and looked for a Workflow tool instead of proving; and a gate
longer than one command's 10 minutes was started in the background and never waited for, because a
workflow agent is finished the moment it replies. Neither is visible to `check-pipeline.mjs`, whose
agents are stubs — only a real run shows what an agent does with its prompt.

`docs/process/pipeline.json` is pre-confirmed for the test and sets `waitChunk` to 45 s, so the
100-second gate needs several waits — the same shape as a 13-minute gate against 9-minute waits,
at a fraction of the cost. It sets `"model": "sonnet"`.

What a correct run shows is in [`../expected.md`](../expected.md), section `pipeline-build`.
