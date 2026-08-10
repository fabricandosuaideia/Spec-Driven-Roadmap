# Answer key — what a correct run does with the fixture

This file is the benchmark's real asset. The fixture is just input; **this is what makes a result a
score instead of an impression.**

It lives in this repository, beside the rules it tests, for one reason: **the expected answer changes
when a rule changes.** In v3.12.0 the correct destination for the vote tie-break moved from
`## Expected Gray Areas` to the ledger, because test 1 became a gate. Had this file lived in a
separate repository it would still be asserting the old answer, green and wrong — the exact drift
`CLAUDE.md` spends a section on. **Update this file in the same commit as any rule that changes what
a correct run produces.**

---

## The seven planted ambiguities

The fixture's `PRD.md` is deliberately silent on seven points. Rule 1 forbids deciding any of them in
silence, so each must reach one of three destinations. Anything reaching a fourth destination — or
none — is a failure.

| # | Ambiguity | Where it hides | Test 1 | Correct destination |
|---|---|---|---|---|
| 1 | Password rule | `A1` says "e-mail and password", never what is valid | passes | feature `open questions` (+ roll-up) |
| 2 | Exact role permissions | `A5` names roles, defines only two verbs | passes | ledger — `Auth boundaries & rate limits` |
| 3 | Tie-break on equal votes | `C3` gives the sort key, never the tie | passes | ledger — `Concurrency / ordering` |
| 4 | Votes after an item is edited | `C5` allows editing, `C2` owns votes; neither meets | passes | ledger — `project-specific` |
| 5 | Notification channel | `E1`–`E3` name triggers, never the channel | passes | ledger — `project-specific` |
| 6 | Public API auth scheme | `F1` says "authenticated", names no scheme | passes | ledger — `Auth boundaries & rate limits` |
| 7 | Retention / deletion | **absent** — zero occurrences in the PRD | passes | ledger — `Data lifecycle / expiry`, not `N/A` |

**Why the destinations differ.** 2, 3, 6 and 7 map onto a rubric theme and reach several features, so
they are ledger rows. 4 and 5 also reach several features but map onto no rubric theme, so they take
the `project-specific` row Step 7a allows. 1 reaches one feature only, so it stays in that feature's
own `open questions` — and that is the case v3.12.0 exists for: before it, being small was a reason
to file it where nothing sweeps.

**A ledger row may be *decided* rather than open.** Answering it is a legitimate outcome — the run
asks, and a user who answers has decided. What is never legitimate is the answer appearing with
nobody asked. The scorer therefore checks *presence at the right destination*, not `status: open`.

**#7 is scored by the state of its ledger row, not by a word.** The other six are found by grepping
the roadmap corpus; #7 cannot be, and a run proved it. The scorer looked for
`reten|retention|exclus|delete|purg` and a correct run had written *"Nada é apagado de verdade: item
retirado por C6 ou removido por A5 fica com marca de retirado"* — the right answer, at the right
destination, in the language the source document is written in, matching nothing. It scored 6/7 and
read as a regression. A false red is as damaging as an empty green: it teaches whoever opens
`RESULTS.md` to discount the number, and it invites someone to "repair" behaviour that was correct.

So #7 asks whether the `Data lifecycle / expiry` row exists and carries something other than
`N/A`. The rubric theme name is a machine-read key and stays English in every language, which is what
makes the test survive translation. `N/A because …` is the failing state on purpose: for this PRD the
theme plainly applies — accounts close, `C6` withdraws an item, `A5` removes a person — so dismissing
it is the run reading the document instead of enumerating the entities it implies. `not decided`
passes, because the ambiguity reached the ledger, which is all this scorer ever claims to measure.

**#7 is the sharpest of the seven.** It cannot be found by reading the PRD, only by sweeping the
entities the PRD implies — a person removed from a team, an account closed, `C6`'s "withdraw item"
that never says hard or soft. A run that misses only #7 is a run that read instead of enumerating.

---

## Per-scenario expectations

### `0a-single` — single-section, the primary run

**This scenario does not stay single-section, and a run that does is the regression.** The PRD's 26
scope units decompose to roughly 20 features, well past the point where Step 8's size bullet re-raises
the mode question, so a correct run answers *single* at Phase 0 and then reverses. Two independent
runs at 3.18.0 did exactly that, unprompted. The scenario is therefore the **re-raise** under test,
not the mode: it is the one path where the procedure has to contradict an answer the user already
gave, which is the thing most likely to be quietly skipped.

Expect either shape from there, both correct:

- **All sections decomposed in one run.** Score the full seven.
- **Only the first section decomposed**, the rest left `NOT YET DECOMPOSED` in the index — the
  documented default, multi-section decomposition being lazy. Ambiguities living in sections nobody
  reached cannot be placed, so the scorer reports `PARTIAL`, refuses to write the run to `RESULTS.md`,
  and does not count it as a regression. Decompose the rest and score again for a comparable number.

- All seven ambiguities at their destination above.
- `## Expected Gray Areas`: **every line states where the answer already lives** (code, config, an
  existing convention). None may cite `feature-local` or `cheap to reverse` — those are routing
  tests, not filing reasons (Step 7b).
- In a greenfield fixture this block is **nearly empty and that is correct**: with no code and no
  conventions on disk, almost nothing can honestly fail test 1. A long block here means citations
  were fabricated to get through the gate.
- Coverage closes `uncovered: none` and accounts for all 26 units `A1`–`F3`.
- `check-roadmap.py` passes with zero failures. On a multi-section result this exercises a path the
  single-section shape never reaches: the ledger sits in the index while the question it points at
  sits in whichever section roadmap owns the affected features. The linter used to look for both in
  the same file and failed five correct section roadmaps at once.

### `0a-multi` — multi-section

- `docs/ROADMAP-INDEX.md` carries `## Status` and `## Cross-Cutting Decisions`; the section roadmaps
  reference and never restate them.
- Only the requested section is decomposed. The others read `NOT YET DECOMPOSED` — lazy decomposition
  is the design, not an omission.
- The seed does **not** fire for a section that has no `.txt`.

### `0b-interview` — interview, no downstream skill installed

- `docs/PROJECT.md` written from the interview, and the roadmap generated anyway.
- **Nothing created under `.specs/`** — not `STATE.md`, not a placeholder.
- The `**Handoff**` line records `pending — no downstream spec-driven skill installed`.
- No implementation prompt is handed over: there is no confirmed trigger phrase to build one from.

### `0c-brownfield` — working code, no scope document

- Two lists confirmed **in chat before** `docs/CODEBASE-SUMMARY.md` is written.
- Capabilities already built appear as `pre-existing` in the coverage table, never as features.
- `## Gaps / Likely Next Work` comes from the user's answer, never inferred from the code.

### `loop` — option B, the loop path

- Step 9 runs: every open question closed by interview, one at a time.
- Afterwards the roadmap holds **zero** `status: open` and **zero** `not decided`.
- The propagation pass runs and reports its five categories; converging inside the 3-pass cap.
- The emitted prompt is word-for-word the Step 10 template, with **`<current-feature>` still
  literal** — substituting it pins every iteration to feature one and the loop never terminates.
- `<DISCHARGED-LIST>` resolved (`none` when there are no question-only features).
- The new-session warning is given.

---

### `state-rerun`, `state-inflight`, `state-conversion` — the three that need a past

These start from a frozen project **with history**: a 17-feature single-section roadmap generated by
running the skill, then degraded by hand into what a real backlog looks like after a wave has
shipped. `benchmark/fixture/state/` is the shared tree and each scenario adds a small overlay.

**What is deliberately wrong in that tree, and must stay wrong:**

- one `### ` entry marked superseded in the `.md` and **absent from the `.txt`**;
- two adjacent not-yet-started names in a different order in the two files;
- 27 `.specs/features/` directories no roadmap names, carrying three dead prefixes (`mvp`, `beta`,
  `pilot`) — the ~4:1 orphan ratio measured from a real six-month project;
- four of the six recorded `validation.md` title forms, one genuine FAIL, one PASS whose evidence
  column reads *"revisado à mão"* and cites no `path.ext:NN`;
- a `## Handoff` in the downstream skill's eight fields, including the
  `**In-progress** (file:line):` label whose parenthetical has broken a parser here before.

**The linter baseline is non-zero on purpose: 1 failed, 1 warning.** The failure is the superseded
entry missing from the `.txt`; the warning is the 27 orphans. A run that "fixes" either has repaired
the fixture rather than done its job.

**Scored by comparison, never by grep.** `setup` snapshots the tree — heading order, the `.txt`, the
feature directories, the `## Decisions` body, `.specs/STATE.md` — and `score` diffs against it. The
seven-ambiguity grep is refused outright here: the input already contains all seven, so it would print
`7/7` whatever the run did.

- **`state-rerun`** — a wave-2 source arrives, and the run hits a **fork whose two answers are both
  the user's to give**: extend the existing roadmap, or give the wave its own section. The scorer
  detects which was taken and asserts what that branch requires — a build order extended in place with
  no index behind the user's back, or a conversion that produced an index and a second section. It
  asserts the shared half either way: every pre-existing feature survives in the same relative order,
  the pre-run build order survives in full, and the new wave actually lands.

  An earlier version of this scorer hardcoded the extend branch and failed a correct run that took the
  other one. That is worth naming because it is the same defect the skill's own gates kept committing
  this release — a false red — reappearing one layer up, in the thing that grades them. A scorer that
  assumes one answer to a question the procedure deliberately asks is grading the simulated user, not
  the skill.
- **`state-inflight`** — the Handoff names a feature with `spec.md` and no PASS. `.specs/STATE.md` is
  **byte-identical afterwards** (rule 11), and `## Status` says the Handoff was `not rewritten this
  run`.
- **`state-conversion`** — oversize single-section, names frozen by directories on disk. The produced
  `docs/ROADMAP-<slug>.md` must carry the slug **derived** from the frozen `.txt` prefix — an equality
  no free choice satisfies by accident, which is how "derived, never chosen" becomes a score.

**What the scores cannot see.** That the extend-versus-own-section question was *asked* rather than
inferred leaves no trace on disk. And a green `state-conversion` says the conversion mechanics are
right, not that the result was what the user wanted: the first run of this scenario passed every
assertion while reporting that the skill has no path for *"split this into several sections"* at all.
The score measures the operation; read the friction for whether it was the right operation.

### `loop-build` — the loop prompt's own project

Not a roadmap scenario at all: a small git project whose only failing test cannot pass without real
implementation work, used to execute the option-B loop prompt. `setup` installs the skill **and the
downstream skill** into it, which is the whole reason it is a scenario key — the prompt's
*"use the `<downstream-skill>` skill"* branch went unexercised through nine runs for no better reason
than the fixture having no `.claude/skills/`, and `.gitignore` forbids shipping one inside it.

What it asserts is in [`loop-fixture/README.md`](loop-fixture/README.md), and the short version is
that `git diff -- tests/` must be empty: the prompt forbids reaching a PASS by bending a test, and
that is the one clause whose failure destroys the only evidence the loop produces.

## Friction: the second number

Agent-reported, not scriptable, and worth recording anyway. Classify each point as `travou`,
`improvisou`, `contradicao`, `leitura-nao-mandada`, `impossivel` or `quase-errei`.

The one that matters is the share of **`improvisou`** — an agent deciding something the procedure
should have decided. It is the only friction type that measures the procedure rather than the agent.

Baselines measured on this fixture:

```
v3.10.0   63 points across 4 scenarios   improvisou 56%
v3.11.0   ~7.5 per scenario              improvisou 33%
```

**Regression:** `improvisou` rising above its previous release, or any planted ambiguity losing its
destination. Both are hard signals. A rising total friction count with `improvisou` flat is usually a
more honest reporter, not a worse skill — read before reacting.

---

## Changing this file

Only alongside the rule that changed what a correct run produces, in the same commit, with the reason
in the message. A benchmark whose answer key moves for convenience measures nothing.

Planting an eighth ambiguity is welcome — the fixture is deliberately under-specified in more places
than seven. Add it to the table, say where it hides, and say why its destination is what it is.
