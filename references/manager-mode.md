# Manager Mode — The Whole Backlog, Unattended, on the Owner's Delegation

An additional way of working, beside the seed's options A, B and C. Those build one roadmap and stop
at its end, because the seam between two sections is where a person re-plans. Manager mode is for an
owner who has decided nobody will be there: it takes every section still to do, in build order, and
for each one decomposes it, deciding what would otherwise be asked, and builds it with option C's
pipeline — section after section, until the backlog ends, a section the owner reserved comes up, or
something breaks that it must not build on.

**Claude Code only**: it is a Workflow script (`scripts/manager-pipeline.js`), and the Workflow tool
exists nowhere else. **Experimental**: first run on a real project on 2026-09-29. It walks
`docs/ROADMAP-INDEX.md`'s sections; a single-section project is one section, `docs/ROADMAP.md`, which
gets the same autonomy without the decomposing.

## Two levels — how much permission the owner gives

Like running an agent with narrower or wider permissions, the owner picks how far the manager may go
without them (`manager.autonomy` in `pipeline.json`):

- **`decide` — level 1, the default.** It answers the open questions itself (marked as its own), and
  in its builds it may correct a test asserting what the owner revoked. When something breaks — a red
  batch barrier, a feature the downstream gate cannot decide, a chain blocked behind a failed feature
  — it **stops** and waits for the owner.
- **`unblock` — level 2, more permission.** Everything level 1 does, and it also **repairs what
  would stop it**:
  - **A red barrier is triaged, not just reported.** For each failing test `scripts/triage-probe.py`
    runs it on the main branch as it was before the merges being judged and as it is now: *regression*
    (it names the merged feature that broke it, by bisection), *preexisting* (it failed before them
    too — broken or flaky), or *not reproduced*. That classification is the script's, never an
    agent's view. A fresh repairer fixes each at the root — a regression in the feature's code, never
    in its test; a preexisting failure at its cause, never by raising a timeout, loosening an assertion,
    skipping or retrying — and proves it ten runs in a row; an independent checker refuses any
    repair that loosens anything; the repair merges through the gate and the barrier runs again. At
    most two cycles; anything not reproduced stops the run, as level 1 would. A failing test is
    always named, never located by `file:line` — a repair that adds a line above it moves it, and the
    command would then find no test (the probe refuses such a command).
  - **A feature the gate cannot decide is classified, not held.** A fresh agent reads its report and
    decides done or build — when in doubt, build: rebuilding finished work costs a visible attempt,
    calling unfinished work done leaves a hole nothing revisits — and records it in `featureStatus`
    as the manager's decision.

  Its price: more of the owner's calls are made for them, including changes to tests and to code
  outside the feature being built. Every one is recorded — decisions in the roadmaps and the run's
  record, repairs as commits named `TRIAGE <kind> <test>: <cause>` — for the owner to review after.
  What it will not do at any level: push, touch anything outside the project, or build on a red main
  branch it could not repair.

## What changes, and what does not

**Rule 1 changes, and only here.** Everywhere else this skill never decides a genuine ambiguity. In
manager mode the owner has delegated that, in writing, and the manager decides — taking the option the
procedure itself calls conservative, or the cheapest to reverse — and marks every such answer
**Decided by the manager (owner's delegation of <date>)**, so the owner can find and review each one.
An answer not marked that way would be indistinguishable from one the owner gave.

**Rule 10 changes, and only here.** The manager marches through sections, which the seed never does.
What does not change: this skill still authors no spec, plan, check or code. Every feature is built by
the downstream skill, run by option C's agents, with the same prover, verifier, reviewer, merge gate
and barrier.

**One test rule changes, and only here.** Everywhere else a builder never edits an existing test to
reach a pass: a test that is wrong stays red for a person to authorise. Nobody is there in manager
mode, and on a real project two features in two days each spent all their attempts, and stopped the
chain behind them, on tests asserting behaviour the owner had revoked — the owner authorised the same
correction by hand both times. So in manager mode the builder may correct **that assertion and only
it**, when an owner decision recorded in the roadmap (an answered question, a settled Cross-Cutting
Decision) revokes exactly the behaviour it states: in a commit of its own quoting the decision, the new
assertion as strong as the old. The independent verifier checks every change to an existing test on
the branch and refuses the feature for any that is not such a correction — an undeclared edit, a
decision that does not revoke it, a weaker assertion, a skip or a deletion.

**Why a script and not a prompt.** A manager that is a conversation grows with every section: on a
measured multi-agent build the coordinator went from 41k to 88k tokens of context in 25 turns, and a
conversation that runs for a day is compacted — which is where a mission gets lost. This manager's
mission is its code and the files on disk. Every agent it starts is fresh and reads only what its role
needs; the session that launches it receives one line per section.

**Why each section is decomposed right before it is built**, not all at once up front: a section's plan
names code, and every section built before it changes that code. Decomposing just in time plans each
section against the code as the previous ones left it.

## Before the first run

1. **The pipeline's config.** `docs/process/pipeline.json` must exist and be confirmed — the gate every
   feature passes, the batch barrier if the project keeps one, the model. If it does not, do option C's
   config first: [handover-prompt.md](handover-prompt.md), Step 10, "Option C — the pipeline", step 1.
2. **The delegation — the one thing only the owner writes.** Show the owner what the manager will
   decide on their behalf: every open question of every section it decomposes, and any row of the
   `## Cross-Cutting Decisions` ledger those sections raise. Then ask, in the conversation's language,
   what they delegate, and write **their words** into `manager.delegation` and today's date into
   `manager.delegatedOn`. Never write it yourself, and never paraphrase it into something broader:
   `plan-pipeline.py --manager` refuses to run without it, and the decomposer quotes it verbatim.
3. **Where to stop.** Ask which sections need the owner whatever happens — live validation with real
   users, a vendor or paid-service choice, anything irreversible or outward-facing — and write their
   slugs into `manager.stopAt`. The manager stops before the first of them.
4. **How much per run.** `manager.sectionsPerRun` (default 4): a Workflow run caps its agents at 1000,
   and a section of ten tier-A features can use a hundred. The manager stops at the cap and says so;
   launching again continues.
5. **Speed.** The same two levers as option C, with the same prices — handover-prompt.md, Step 10,
   "Option C — the pipeline": `lanes` (measure first with `bench-gate.py --lanes 2`) and the
   builder's effort at tier A. A third happens by itself: Phase 2 groups small same-area units into
   one feature (decompose-phase.md Step 3), so a section of small fixes pays the per-feature cycle
   fewer times.
6. **The level.** `manager.autonomy`: `decide` (the default) or `unblock` — ask, with the price of each
   as "Two levels — how much permission the owner gives" above states it, and write the owner's answer; never raise it yourself.
7. **Optionally, a stronger model for the decisions.** `manager.decomposeModel` sets the decomposer's
   model on its own. Decomposition is where the manager decides; the builders follow what it wrote.
8. **A clean tree on the main branch**, and nothing else running in that folder: with one lane, the
   pipeline's builders switch branches in it.

Then run:

```
python3 <this-skill-dir>/scripts/plan-pipeline.py --root <project-root> --manager > /dev/null
```

and show the owner the one line it prints: which sections have work left, which need decomposing,
where it will stop.

**Features the gate cannot decide.** The line may name features "needing the owner": a feature with a
report the downstream gate refuses — a real FAIL, or a PASS written in a shape the script does not
read — or a feature still pending that a finished one depends on. The manager never builds a section
holding one, nor any section depending on it, because it cannot tell finished work from unfinished
there: on a real project six features of a closed section had PASS reports the script could not read,
and an unattended run would have rebuilt all of them. For each, read its report with the owner and
write the owner's word into `pipeline.json`: `"featureStatus": {"<feature>": "done"}` when the report
really says it is finished, `"build"` when it must be built again. Never edit the report itself — it
is the downstream skill's record, not this skill's.

## The prompt

Hand over this prompt, `<PROJECT-ROOT>` and `<ROADMAP-SKILL-DIR>` resolved as in handoff-seed.md
Step 6's table, for a new session:

```
Run the project in manager mode. First run
`python3 <ROADMAP-SKILL-DIR>/scripts/plan-pipeline.py --root <PROJECT-ROOT> --manager`
and read only the one line it prints to stderr; if it exits non-zero, report that line and stop.
Otherwise launch the Workflow tool with the absolute scriptPath that line names and the JSON the
command printed as args. I am asking you to
run this workflow. Do not arm a monitor on its events and do not comment on them while it runs — each
notification you answer re-reads this whole conversation. When it returns, report its lines.
This request is for the session that launches the workflow. Every agent the workflow starts —
decomposer, planner, builder, prover, verifier, reviewer, merger, barrier, recorder — has already
been launched by it: it does the role task it was given, and never runs plan-pipeline.py or looks
for a Workflow tool.
```

Say beside it, as for option C: open a new session for it; it merges into the main branch locally and
pushes only if `pipeline.json` says `"push": true`.

## What a run does

For each section in `## Ordering`'s order:

- **Already done** (decomposed, every feature passing its downstream gate): skipped, at no cost.
- **In `stopAt`**: the run stops there.
- **Depends on a section that did not finish** in this run (a feature blocked, held or not merged):
  skipped — never built on a base nobody proved. A section that does not depend on it still runs.
- **A barrier an earlier run never finished** (code on the main branch after the last green barrier,
  which `plan-pipeline.py` reads from the commit each green barrier records): a finished section is
  not called done until that barrier has run, and it runs before anything new is built; red stops the
  run, as above, and level `unblock` triages it from the last proved commit.
- **Not decomposed**: a fresh decomposer runs Phase 2 for it (decompose-phase.md, the whole
  procedure), decides every question, marks each decision, runs `check-roadmap.py` to 0 failed and
  commits.
- **Then** a fresh planner runs `plan-pipeline.py` for that roadmap, and `roadmap-pipeline.js` builds it
  as a child workflow — the whole of option C, barrier included.
- **A red barrier** stops the run: the main branch is red.

At the end a fresh agent runs the seed (Steps 1-7; Step 8 has nobody to ask) and records the run — its
lines and **every decision the manager made** — in `docs/roadmap-history.md` through the `**Last run**:`
line, and commits. The run's result lists the same decisions when that record could not be written.

## Afterwards

- **Review the decisions.** They are the price of the run: search the roadmaps for `Decided by the
  manager`, or read the run's account in `docs/roadmap-history.md`. A decision the owner would have
  made differently is a change request against built code, not a wording fix — say so when reporting.
- **Continue** by launching again: decomposed sections and passing features are read from disk, so a
  new run starts where the last one stopped.
- **Measure** with *"measure my agent cost"*: every agent is labelled by role, so the cost of deciding
  (decomposers) and of building shows separately.
