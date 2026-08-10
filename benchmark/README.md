# Benchmark

A frozen input, an answer key, and a score. It exists so that a change to this skill can be shown not
to have broken it — by execution, which is the only thing that ever caught a real defect here.

**Not shipped to users.** The installers copy `SKILL.md`, `references/` and the runtime `scripts/`;
this directory is for whoever works *on* the skill.

## Why it lives in this repository

The tempting alternative is a separate benchmark repository, frozen in time. It is the wrong shape,
for one reason: **the answer key changes when a rule changes.** In v3.12.0 the correct destination for
the vote tie-break moved from `## Expected Gray Areas` to the ledger, because test 1 became a gate.
An answer key in another repository would still assert the old destination — green, and wrong.

That is two things that must agree, in two places, with no mechanism keeping them in step. It is the
failure [`CLAUDE.md`](../CLAUDE.md) names as the pattern behind 15 of 37 findings in a full review.
So the input is frozen and the answer key versions with the rules it tests.

A well-known third-party repository as the fixture fails for a different reason: **you cannot plant a
defect in someone else's PRD.** Without planted defects there is no score, only "it ran" — which is
what prose review already gave, and it found nothing. As a *secondary* check against real-world input
it would be worth having; as the benchmark, no.

## What is in here

| | |
|---|---|
| `fixture/PRD.md` | 26 numbered scope units across six sections, and **seven planted ambiguities** |
| `fixture/brownfield/` | a working FastAPI + React project with no scope document, for the 0c path |
| [`expected.md`](expected.md) | the answer key — where each planted ambiguity must land, and why |
| [`reports/`](reports/) | thirteen `validation.md` reports, for the Step 2 completion test |
| `RESULTS.md` | the scoreboard, **appended by the runner**, never edited by hand |

**`reports/` is a different kind of test and runs differently.** The scenarios above execute the
whole skill and score the roadmap it produces; that one hands an agent a single rule and thirteen files
and asks what the rule yields. It exists because Step 2 decides which features are done, the seed
skips every feature it calls done, and a wrong `done` means the loop builds on top of work that never
passed. Run it the way a rule change should always be checked — two variants, agents that have seen
neither, no hint that a second variant exists — and read
[`reports-EXPECTED.md`](reports-EXPECTED.md) for what each file is there to catch.

## Running it

```bash
python3 scripts/run-benchmark.py list
python3 scripts/run-benchmark.py setup 0a-single        # prints the path to work in
#   ... an agent executes the skill in that path ...
python3 scripts/run-benchmark.py score <path> --record
```

`setup` creates the project under a parent that contains **nothing else**. That is not tidiness:
seven finished runs once sat side by side under one parent, and any of them could `ls ..` and read
another's answers to the same PRD.

**Running several agents on one scenario — `setup <scenario> --agents N`.** It builds N separate
copies, each under its own parent, and prints one path per agent. Give each agent exactly one, and
never the same one to two of them: a shared tree does not produce two results, it produces none.
Three agents were once handed a single directory, overwrote each other, and the whole run had to be
thrown away. Hand-rolling the copies is where this fails, so the flag exists to make it not worth
hand-rolling.

`score` checks the seven planted ambiguities reached a destination, runs `check-roadmap.py`, and with
`--record` appends a row to `RESULTS.md`. Exit `1` means a planted ambiguity is missing.

## Launching the agent — the part no script can do

The skill is a procedure an agent reads and follows, so an agent runs it. **How it is launched
decides whether the result means anything.** Four rules, each of which changed an outcome here:

1. **A fresh agent, with no knowledge of the change being tested.** Whoever wrote the procedure is
   its worst reader: they know what it was *meant* to say. In the v3.12.0 validation the executor was
   told nothing about what had changed, and reproduced the new rule from the text alone — which is
   the only evidence that the text works without someone explaining it.

2. **"Follow it literally."** Faced with an ambiguous instruction, take the most literal reading and
   record it; never fill the gap with good sense. An agent that repairs the procedure while executing
   it hides exactly what you are trying to see.

3. **"Friction is the output."** Say so explicitly. Stalling, improvising, hitting a contradiction —
   these are the result, not a side effect. A run reporting zero friction is suspected of not having
   followed the text.

4. **Simulate the user honestly, and ask the agent to confess.** When the procedure asks a question,
   answer as a reasonable person would — then have the agent declare, at the end, **which answers it
   decided on its own**, making clear that this is the data and not a failure. That is how the
   discount that matters surfaced: 7 of 7 by "nobody filled a gap in silence", 4 of 7 by "a human
   actually decided".

## Reading a result

Two numbers, and they answer different questions.

**Captured, out of seven** — did the skill's central promise hold? A drop is a regression, full stop.

**Share of `improvisou` friction** — an agent deciding what the procedure should have decided. It is
the only friction type that measures the *procedure* rather than the agent, and it fell from 56% to
33% across v3.10.0 → v3.11.0 while pointing straight at what to fix.

A rising total friction count with `improvisou` flat usually means a more honest reporter, not a
worse skill. Read before reacting.

## What is not covered yet

The four entry paths and the loop all start from **input only**. Three scenarios need a project with
a past — re-run over an existing roadmap, seed with work in flight, conversion over generated output —
and none has ever been run. [`state-scenarios.md`](state-scenarios.md) records what a fixture for them
must carry, measured against a real six-month project rather than imagined.

## Changing the fixture

The input is frozen. Change it only to **plant an eighth ambiguity** — the PRD is under-specified in
more places than seven — and when you do, add it to `expected.md` with where it hides and why its
destination is what it is.

Editing `expected.md` for any other reason needs the rule change that justifies it, in the same
commit, with the reason in the message. **A benchmark whose answer key moves for convenience measures
nothing.**
