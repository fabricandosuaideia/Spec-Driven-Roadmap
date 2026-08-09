# CLAUDE.md — how work is done in this repository

> **Speak the user's language.** Reply in whatever language the person is writing to you in —
> Portuguese, Spanish, English or anything else — without being asked and without switching back.
> This repository is written in English and stays that way; that is a convention for the *files*,
> never an instruction about the *conversation*.
>
> Keep the two apart, because they have different rules. What the skill **generates** follows
> `references/scope-phase.md`: the language of the source document, or of the conversation when
> there is no source, with feature names, slugs, filenames and every generated section heading
> staying in English because they are machine-read keys. What you **say** follows the person in
> front of you.

This file does not describe *what* the skill does — that is [`README.md`](README.md),
[`SKILL.md`](SKILL.md) and [`references/`](references/). It records **how work is done here**:
techniques tested in this repository that held up, so they are not rediscovered every session.

Each lesson carries the evidence that made it credible. The numbers come from real runs recorded in
[`CHANGELOG.md`](CHANGELOG.md), not from opinion — and several of them are defects the maintainer
shipped and measured afterwards. They are here because the pattern is more useful than the modesty.

Origin: the release sequence from v3.4.0 to v3.13.0. The lessons generalise; the evidence is local.

---

## Working here: what to run, and when

Before the lessons, the mechanics. Everything below is a command; none of it is optional.

| | |
|---|---|
| `scripts/check-consistency.py` | 23 checks over the invariants that keep this repo's duplicated facts in step. **Run after any edit to `SKILL.md`, `references/` or `scripts/`.** |
| `scripts/check-roadmap.py` | Lints a roadmap the skill produced. Shipped to users; Phase 2 runs it. |
| `scripts/run-benchmark.py` | Sets up an isolated run and scores it. See [`benchmark/`](benchmark/). |
| `scripts/convert-to-multi.py` | Shipped to users. The single→multi conversion. |
| `scripts/bump-version.sh` | Writes all three version declarations **and runs the consistency check**, refusing the release when it fails. |

**The loop for any change:**

1. Read the reference you are about to edit **completely**. `SKILL.md` says so and it is not
   ceremony — the contradictions found here lived 300 lines from the edit, or in another file.
2. Make the change.
3. `python3 scripts/check-consistency.py` — must report `0 failed`.
4. **If the change alters what a correct run produces, run the benchmark** ([`benchmark/README.md`](benchmark/README.md))
   and update [`benchmark/expected.md`](benchmark/expected.md) **in the same commit**. A rule and its
   answer key drifting apart is the failure this repository has committed most often.
5. Add the `CHANGELOG.md` entry **before** bumping — the gate checks the entry exists for the new
   version.
6. `bash scripts/bump-version.sh <version>` — it runs the gate and exits non-zero if anything fails.

**Ask before committing, tagging or pushing.** Every release here is a public artifact with a tag;
none of it is yours to decide unprompted.

**Never edit by hand:** `benchmark/RESULTS.md` (the runner appends it), and the three version
declarations (`bump-version.sh` writes them together, and refuses when they already disagree).

**What is never touched without saying so:** the 13 non-negotiable rules in `SKILL.md`, the three
prompt templates in `references/handover-prompt.md` Step 10, and the eight-field Handoff schema in
`handoff-seed.md` Step 6. Two rule changes have happened in this repository's history; both are named
in the `CHANGELOG.md` entry that made them.

**Reading the downstream skill.** `references/handoff-seed.md` requires reading `tlc-spec-driven`'s
real schema from disk, never from memory. It is vendored under `.claude/skills/` and **gitignored**,
so a fresh clone does not have it — see [`CONTRIBUTING.md`](CONTRIBUTING.md) before concluding that
no downstream skill is installed.

---

## 1. A prose change is worth nothing until it has been executed

**The most expensive lesson here.** Nine consecutive releases of prose review — adversarial reading,
cross-checking, counts verified — found none of what **a single execution** found.

Worse: every time a prose fix shipped without being executed, the next execution found a defect in
it. Including in fixes made to fix defects:

```
3.6.1   closed 3 grave defects  ->  created 2
3.10.0  closed 4                ->  created 1, caught by the re-run
3.12.0  closed 1                ->  created 2, one of them breaking the rule it was fixing
```

**So:** when editing a procedure, a specification, a prompt — anything another person or agent will
*execute* — plan the execution alongside the edit. "I re-read it and it is correct" is not
verification; it is exactly what preceded each of the cases above.

## 2. When a rule can become a script, make it one

Four times in this repository a written rule became code, always for the same reason: **a written
procedure cannot be run against a test case.**

The decisive case: a destructive migration procedure was **rejected three rounds running** by
adversarial review. Rewritten as a script, the first execution exposed a fourth defect none of the
three reviews could see, and a fourth round against 54 fixtures found five more — two of which only
appeared when real `git` commands ran.

**Signs a rule should be a script:** it has an order of operations; it has a rollback path; it
derives a value from somewhere else; it is verifiable by comparison. If you are writing "never do X
before Y" in prose, a function does that better.

## 3. A checker with no caller is a decoration

A consistency script existed for two releases with **zero callers**: not in the installers, named in
no document, and there is no CI here. It ran only when someone remembered — and memory failing is
precisely the disease it exists to catch.

> A checker nobody invokes is **worse** than none: it produces the belief in a net without the net.

**So:** when you create a check, decide in the same commit **where it is invoked**, and pick a point
the process cannot route around. Here that was the version-bump script — you cannot cut a release
without bumping.

## 4. A declared constant with no reader rots

Two declarative tables shipped with **zero readers**. One of them held a **wrong** fact — seven
entries where the canonical number is six — sitting in the tree, invisible, because nothing consulted
it.

It became an automated check: *every module-level constant must be read somewhere in its own file.*
It is the only check here aimed at the disease rather than a symptom.

## 5. Verify the remedy, not just the finding

Measured across three batches in this repository:

```
6 remedies refuted  ->  26 of 31 needed correcting  ->  5 of 7 rejected in triage
```

A wrong remedy, applied, **introduces a defect while looking like progress**. Real examples caught
before anything was written: a fix that would have made a propagation pass loop forever; a clause
that would have refused to seed a section under construction; a check that invented an artifact which
does not exist.

**So:** between "finding confirmed" and "apply", insert a phase answering **two separate** questions —
*(a) does the defect still exist today?* and *(b) does the proposed remedy break something else?* —
by re-reading the whole passage the fix touches. Discarding is a legitimate outcome, and the list of
discards is usually more informative than the list of applications.

## 6. In a gate, a silent skip is worse than a failure

A linter carried the principle "skip rather than guess" — right for an unparseable file, **wrong**
for an unparseable item: it turned a total parse failure into a pass. A roadmap with a circular
dependency and a 40-task feature came out with `0 failed`, exit 0.

**Rule:** if the unit you were supposed to judge could not be read, that is a **failure**, not
silence. An empty green is the worst result a gate can give, because it switches off the attention of
whoever reads it.

## 7. Measure before proposing; never invent a number

Two numbers were published here without measuring — "300 lines" and "29 findings" — and both were
wrong. The first was wrong **in kind**: the real distance was not within a file but between files, so
a proximity-based tool would have caught 1 case out of 7.

Measuring also reversed a design decision. Counting the duplicated facts (64 candidates, and the
enumeration had not saturated) proved a hand-maintained registry would cover ~13% and become one more
thing that drifts. The correct conclusion was **not to build** the proposed mechanism.

**So:** every quantitative claim comes from a command you ran. If you did not measure, write "not
measured" — it is more useful than an estimate that looks like data.

## 8. To test execution, use agents with no history

Whoever wrote the procedure is its **worst possible reader**: they know what it was *meant* to say.

Instructions that made the difference in the tests here:

- **"Follow it literally."** Faced with ambiguity, take the most literal reading and record it — never
  fill the gap with good sense. An agent that repairs the procedure while executing it hides exactly
  what you are trying to see.
- **"Friction is the output."** State that stalling, improvising and finding contradictions are the
  *result*, not a side effect. A run reporting zero friction is suspected of not having followed the
  text.
- **Do not say what changed.** To validate a change, the executor must not know which one it is. If
  the text only works with someone explaining it, it does not work.

The most useful metric this produced: the share of friction of the kind **"improvised"** — an agent
deciding something the procedure should have decided. It fell from 56% to 33% and pointed straight at
what to fix.

## 9. Isolate the test environment

Seven completed runs sat side by side under one parent directory. Any of them could `ls ..` and see
the others' results for the same input.

**So:** the test project's parent directory contains **only it**. And archive the previous state
before cleaning — it is the baseline for everything measured, and deleting it costs you the "before"
of every number.

## 10. Plant known defects so quality becomes a score

> Standardised as [`benchmark/`](benchmark/): frozen fixture, answer key, and a runner that isolates
> the run and scores it. Read [`benchmark/README.md`](benchmark/README.md) before testing a change —
> especially the four rules for launching the agent, which are what make a result mean anything.


The test PRD carried **seven deliberately planted ambiguities**. That turned "does the never-decide-an-
ambiguity rule work?" from an impression into a score: **5 of 7 → 7 of 7**.

Without planted defects there is no way to know whether a fix worked. With them the answer is a
number, and regression becomes visible.

**A companion worth copying:** ask the executor to **declare when it decided something silently**,
making clear that this is the data and not a failure on its part. That is how the discount that
matters surfaced — 7 of 7 by the metric "nobody filled a gap in silence", but 4 of 7 by the metric "a
human actually decided".

---

## The pattern running through all of it

**Accretion without reconciliation.** Every time a release added a fact in one place, the places that
**write**, **audit** and **document** that fact stayed on the previous version. It explained 15 of 37
findings in a full review, and then happened again two releases later, committed while fixing
something else.

Duplicating a fact on purpose — so each file is self-sufficient for the agent reading it — is a
defensible choice. Having no mechanism to keep the copies in step is not. While that depends on the
maintainer's memory, the memory will fail; here it failed on at least five distinct facts across two
releases, which is why `scripts/check-consistency.py` exists.

## What did not work

Recorded so it is not attempted again:

- **A hand-maintained fact registry** (`facts.yaml` and the like) for keeping copies in step.
  Measured: covers ~13% of the normative sentences, needs manual upkeep, and the registry itself
  drifts — this repository's two declarative tables rotted within weeks.
- **A release gate resting on LLM judgement**, with no determinism. No CI, no hook, and a cost per
  release: it becomes theatre, producing an artifact that *resembles* verification.
- **Splitting a file by size.** Splitting worked only where there was a real seam — two triggers and
  two readers in one file. Cutting by line count is the kind of surgery that introduced defects three
  times.
