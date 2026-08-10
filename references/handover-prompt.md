# Handover — Which Prompt, and Emitting It

The seed's last act, split out of [handoff-seed.md](handoff-seed.md) because it has a different
trigger and a different reader. Steps 1-7 run on every seed; these three run only when Step 7 did
**not** end the procedure — and its exit list ends it whenever nothing was seeded or Step 6 was
skipped. An agent that only needs to refresh a `## Status` block has no reason to carry the loop
prompt's rules, so they live here.

**Enter here from handoff-seed.md Step 7, never on your own.** Everything these steps rely on —
the target feature, the remaining build order, the blocker, the mode's resolved paths — is what
Steps 1-6 produced. Running them against anything else emits a prompt pointing at nothing.

**How step numbers read here.** A bare `Step 1`-`Step 7` is [handoff-seed.md](handoff-seed.md)'s —
the numbering is continuous across the two files because it is one procedure. A bare `Step 8`-`Step
10` is this file's. Any other file's steps are named with it, as they already are elsewhere
(`index-phase Step 4`, `decompose-phase Step 7`). Nothing is renumbered by the split.

Step 6's placeholder table is the authority on `<ROADMAP-PATH>`, `<STATUS-PATH>` and
`<BUILD-ORDER-TXT>`; Step 10 resolves all three against it.

## Contents

- [Step 8 — Ask which implementation prompt to hand over](#step-8--ask-which-implementation-prompt-to-hand-over)
- [Step 9 — Loop option only: close every open question first](#step-9--loop-option-only-close-every-open-question-first)
- [Step 10 — Hand over the prompt, warn about the session, stop](#step-10--hand-over-the-prompt-warn-about-the-session-stop)

---

## Step 8 — Ask which implementation prompt to hand over

The roadmap is done and the user now has to actually build from it. There are two legitimate ways to
drive that, and **which one is the user's call — never pick for them, and never default to the loop
because it looks faster.** Ask, in the confirmed output language:

- **Option A — one feature at a time.** They get the prompt for `<target>` only, run it, and come
  back for the next feature when it passes. Full control, a checkpoint per feature.
- **Option B — one `/loop` run over one roadmap.** The build does not stop until every feature in
  *that roadmap* is verified PASS. **A loop covers exactly one roadmap file**, so say which:
  - *Single-section mode:* `docs/ROADMAP.md` — that is the whole backlog, so B finishes the product.
  - *Multi-section mode:* the target section's `docs/ROADMAP-<slug>.md` alone, the one Step 4 picked.
    Name that section, name every other section as not covered, and say what happens when it ends:
    they come back, this skill re-seeds, and the next section gets its own loop. Give the reason or
    it reads as a limitation — a boundary contract's producer names are *"provisional until that
    section is decomposed"* (index-phase Step 4; Step 10's scope rule carries the same reason in
    full — keep the two in step), so the gap between two sections is where a plan meets what
    actually shipped. That is a checkpoint, not a step a loop can take unattended.

  State the precondition up front: **that roadmap must have zero open questions**, because a loop has
  no one to ask. If any remain, you will interview them closed first, and only then produce the prompt.

  **When Step 4 recorded a provisional producer, say so here and do not present option B as the
  default** — every feature that consumes one would be built unattended against names that can still
  move. Option A is unaffected, because a human is present. The user may still choose B; then Step 10
  names the provisional producers beside the prompt, in the surrounding message.

Everywhere below, **"the roadmap"** means that one file and its build order — `<ROADMAP-PATH>` and
`<BUILD-ORDER-TXT>` exactly as Step 6's table resolves them for the target section.

**Say what option B actually trades away — it is not "no questions left".** Closing the roadmap's
open questions does not close the gray areas Phase 2 Step 7b deliberately left to the downstream
skill's own Discuss. In a loop those get the agent's default, recorded with its rationale in each
spec's Assumptions & Open Questions, for the user to review afterwards. That is a legitimate trade
and it is that skill's own documented fallback — see Step 10 below, which cites it — but it is the
user's to make knowingly:
option B means *"the roadmap has no gaps, and the implementation-shape calls inside each feature get
decided for you and written down"*. Name the count from that roadmap's `## Expected Gray Areas` so
the size of the trade is concrete rather than abstract — and say it is a floor, not a ceiling: that
block holds only what Phase 2's own sweep turned up (decompose-phase Step 7b), while each feature's
Discuss generates its own on top of it. A roadmap that omits the block has none, not an error. Under
option A those same gray areas are put to the user in context, with the code in front of them — which
is the better answer whenever a human is available.

**Option B is also the path of greatest accumulation** — a cost that only surfaces after several
waves of work over the same roadmap. Step 9 closes *every* open question in that roadmap before the
prompt exists, and decompose-phase Step 8 requires the results to stay: *"Answered entries stay —
never deleted"*, because the answer itself is the record. Each loop therefore deposits a full set of
answered questions that never leaves the file — in the `## Open Questions` roll-up, and in each
carrying feature's own `open questions` field. Across successive waves aimed at one roadmap that is
the single largest driver of its growth, and it is why a new wave usually reads better as its own
section than as an extension of the one already there —
see `New scope arriving at a project that already has a roadmap` in scope-phase.md. That is a cost
to name, not a veto: option B remains the user's to choose, exactly as this step already frames it.

If Step 6 recorded a blocker, say so here: option A cannot give a clean start command until that
question is answered, and option B's sweep is what answers it.

Option A → skip to Step 10. Option B → Step 9.

## Step 9 — Loop option only: close every open question first

*Only when the user chose option B.*

A loop runs unattended. Every ambiguity rule 1 refused to guess is a place the run would either stall
or silently guess — so all of them get closed **before** the prompt exists. Announce that first: say
you will read the roadmap for gaps, and that the roadmap must be complete before you can hand over a
loop prompt.

**1. Sweep the roadmap the loop will actually run, in full.** Not just the target feature — the loop
runs past every feature in that file without stopping. Scope the sweep to exactly what the loop
covers and no wider: a question about a section this loop will not build is asked weeks early,
against a decomposition that "When to re-run, and what is frozen" expects to move before it is built.

- Single-section mode: `docs/ROADMAP.md`.
- Multi-section mode: the target section's `docs/ROADMAP-<slug>.md` **only** — plus, in
  `docs/ROADMAP-INDEX.md`, the **Marked-open** items of every boundary contract on an edge into this
  section that a feature here cites in its `external contract consumed` field. Those are open
  questions living in no roll-up, and Step 6's **Blockers** rule checks them for the target feature
  only; the loop runs past every other feature that consumes one.

Read each file top to bottom. Collect open questions from **both** places they live: each feature's
`open questions` field, and the `## Open Questions` roll-up. They can disagree — a question present
in one and missing from the other is still an open question, and the roll-up is the half the loop
prompt's reader is least likely to check.

Also read `## Cross-Cutting Decisions` (in `docs/ROADMAP.md`, or `docs/ROADMAP-INDEX.md` in
multi-section mode), for three things. Its `not decided` rows are the project-level index of
unanswered themes, and they are **in scope for this interview even when their entry lives in a file
this sweep does not cover** — decomposition is lazy, so a theme first raised by a sibling section
keeps its one roll-up entry there (decompose-phase Step 7a). For each `not decided` row: open the
`<roadmap-path>` it names, read only that file's `## Open Questions`, and if the entry's `affects:`
line reads `all` or names any feature in this roadmap, ask it here and write it back per point 3.
Repair a mismatch before anything else, because it is exactly the shape that reaches the build
unnoticed: an entry with no row → add the `not decided` row naming it; a row whose named path holds
no such entry → create the entry in this roadmap's `## Open Questions`, tagged `cross-cutting` with
`affects: all`, and ask it here too. Point 4's propagation check tests every new
answer against the decided rows. And a theme sitting there as an `N/A because` row whose reason no
longer holds is a gap the sweep must close: a decomposed roadmap now touches it, so ask it in this
interview like any other open question and write the answer over the row (decompose-phase Step 7a's
supersession rule). A loop cannot ask it later. A ``deferred to feature`` row is neither of those and
is not swept: its question is carried by a feature in the build order, so this sweep already meets it
in that feature's own `open questions` field.

**Do not sweep `## Expected Gray Areas`.** Those were deliberately left to the downstream skill's own
Discuss (decompose-phase Step 7b) — they failed **test 1**, meaning the code, config or an existing
convention already answers them and Discuss resolves them
better answered with the code in front of them. Step 10's prompt is what tells the run how to handle
them unattended; re-asking them here is the exact waste decompose-phase Step 7 exists to prevent.

**No section but the target's is covered by this loop** — decomposed or not, and for two different
reasons. A `NOT YET DECOMPOSED` section has no build order to run, and decomposing it is a Phase 2
run this skill never marches into on its own (rule 10). A decomposed sibling is excluded by Step 10's
scope rule instead. Either way, name every uncovered section explicitly, so the user does not read
"loop until done" as "loop until the whole product exists".

**2. Interview them closed, one at a time, in build order** — earliest-blocking question first, so an
answer that reshapes later questions arrives before them. For each: quote the question, cite where
the source leaves it unresolved (the field already carries that citation), and wait for the answer.
Never batch them into one wall of questions, and never answer one yourself.

If the user replies "you decide": ask once for the single constraint that actually governs the
choice, then record the resulting choice as the answer, noting it was delegated. Never leave a
question effectively unanswered while tagging it `answered`.

If the user abandons the interview or defers a question, **option B is off the table.** Say so, and
fall back to option A at the first still-open question. Never emit a loop prompt over a roadmap with
a known gap.

**3. Write each answer back, everywhere its carrier lives.** Which writes those are depends on what
carries the question (decompose-phase Step 8), and the carriers do not take the same set.

**Feature-carried — two writes.** Retag that feature's `open questions` line `status: answered` and
write the answer inline; do the same on that question's `## Open Questions` entry. Answered entries
are never deleted. Then re-evaluate that feature's **needs pre-written context.md** — it stays `yes`
if any implicit dimension is still present, and flips to `no` only when the open question was its
sole cause.

**`cross-cutting` — two writes, and neither is a feature's field.** The carrier is the entry's own
`affects:` line, so there is no `open questions` line to retag and you must not create one.

- Retag the `## Open Questions` entry `status: answered` and write the answer inline. **Leave
  `affects:` in place** — it records what the answer reached, and point 4 reads it to know where to
  look for propagation.
- Promote that theme's `not decided` row in `## Cross-Cutting Decisions` to the real decision, with
  one line of rationale. This is a state change, not a third copy: the roll-up keeps the answered
  question as the record of where the decision came from, and the row is the standing rule the build
  obeys — Step 6's **Next step**, Step 10's prompts and the `CLAUDE.md` bridge all point at the
  ledger and never at the roll-up. An answer that lands only in `## Open Questions` was collected and
  then dropped on the floor; a row still reading `not decided` beside an answered question tells the
  build to re-decide what the user just settled.
- Touch no feature's **needs pre-written context.md**. A cross-cutting question never set that flag —
  Step 6 computes it from the feature's own dimensions and its own field — so answering one cannot
  clear it, and flipping it here would claim a Discuss trigger went away that was never there.

**A marked-open boundary-contract item is written back where it lives** — in `docs/ROADMAP-INDEX.md`'s
contract for that edge, the answer replacing the question while keeping the question text as the
record of what was decided and why. It has no roll-up entry; the contract is its only home.

**Stay inside the question.** An answer never re-opens scope-units, sizing, or task estimates — those
are Phase 2's, and no answer makes them this step's to edit. It can legitimately reach two other
things: an edge between features that already exist, and the coverage table. **Both route through
point 4's categories 4 and 5, and only there** — never decide either here, or one trigger gets two
answers. Never quietly patch a decomposition inside this step.

**4. Re-read from disk, and check what the answers set off.** When the last answer is written, read
every swept roadmap file again, top to bottom, from disk — not from your memory of the interview. Do
not report "no gaps" on the strength of having asked the questions; report it on the strength of
having re-read the files.

The re-read does two things at once. First, the obvious one: confirm no `status: open` survives
anywhere, in either place. If one turns up — the usual cause is a roll-up and a feature field that
were out of sync — close it and start the pass over.

Second, and this is what the pass is really for: **an answer is not inert.** It can create work
somewhere else in the roadmap that nobody wrote down, and the loop will not notice. Test each answer
just given against this fixed list, in the other features, not only in the one that carried the
question:

1. **It adds a dimension elsewhere.** "Payments retry automatically" gives the orders feature
   idempotency/dedup that was never flagged on it.
2. **It creates a question elsewhere.** "Soft delete, always" forces "do reports count
   soft-deleted rows?" onto a feature that had no open question at all.
3. **It contradicts an earlier answer** — including a `## Cross-Cutting Decisions` entry, or an
   `N/A because <reason>` whose reason the answer just invalidated.
4. **It adds or moves an edge between features that already exist.** "Every write is audited" makes
   the orders feature depend on the audit-log feature already in this roadmap, listed after it because
   nothing needed it first. Coverage does not change; the order does.
5. **It requires a capability no feature provides.** "Auth through an external IdP" needs config and
   secrets handling no feature's objective or scope-units deliver. `uncovered: none` is now false.

**Categories 4 and 5 arrive looking identical** — both read as *"something has to exist before X"*.
Tell them apart on the **coverage table**, never on the dependency graph. Name the capability the
answer requires, then look for its owner:

- A feature in this roadmap delivers it (its objective or `scope-units covered` say so), or a row
  already reads `covered by reference to …`, `deferred to …`, or `pre-existing` → **4**.
- Nothing delivers it and no row claims it → **5**.

The self-check: **a 4 never edits the coverage table.** If the repair needs a new row, a changed
disposition, or a new feature, it is a 5 — and a 5 is not yours to repair.

**Route categories 1–3 as questions.** Each becomes a new question, asked the same way, written back
the same way, and then the whole pass runs again, because the new answers propagate too.

**Route category 4 as a bounded repair, not a question.** Rule 4's no-forward-dependencies makes the
fix forced, so there is nothing genuine to put to the user; applying an invariant is not deciding an
ambiguity. Establish the movable window first: list `.specs/features/`. **Every name with a directory
on disk is frozen in place** — decompose-phase freezes names and relative order at directory
existence, not at PASS, so a FAIL or a half-written spec freezes its feature too. The rest of the
build-order file is movable (*"reordering it only among not-yet-started features is fine"*). Then:

- **The edge already points backwards** — the provider is listed earlier. Nothing moves. Write the
  dependent's `depends on` field and touch no other file.
- **Otherwise move the provider, never the dependents**, to the latest position still before every
  feature that depends on it and still after everything it depends on. Moving one feature earlier
  leaves every other position intact; moving dependents later cascades into their own dependents and
  can push work across an increment boundary the user never moved.
- **Stop if that position does not exist** — the provider is frozen, would have to cross a frozen
  feature, or is not in this roadmap at all. Report the edge and what it collides with: something
  already built, or already delegated elsewhere, now needs something planned after it. No reordering
  fixes that, and renaming around it is forbidden. Option B is off the table — and so is option A:
  the recorded order still carries the dependency this pass just proved it cannot legally satisfy,
  so follow **What follows either re-run exit** below.

A legal move writes exactly three things: the `depends on` field, the roadmap's execution-order block
(keep its increment markers), and the `.txt` (names only, one per line). Editing anything else means
you misread the case. Then run the pass again — the re-read is what proves rule 4 still holds
everywhere after the move.

**Route category 5 as a stop.** Never invent the missing feature here; decompose-phase Step 7c
refuses the same move for the same reason. Keep the answer (point 3's writes already landed it) and
append one clause to its `## Open Questions` entry naming the capability that has no owner. Then take
option B off the table and follow **What follows either re-run exit** below. The answer is not lost:
that answered entry is what the re-run reads instead of putting the same question to the user twice.

**What follows either re-run exit.** Two paths reach here: a category-5 stop, and a category-4
collision no legal move repairs. Hand over no prompt — not option B, and not option A: the target
came out of a decomposition you have just proved wrong, and a re-run may reorder any feature that has
no `.specs/features/<name>/` directory yet, which the target by definition has not. Answers already
written back stay on disk; they are correct and the re-run extends around them. Say explicitly that
the `## Status` block and the `## Handoff` written in Steps 5-6 describe the pre-answer decomposition
and must not be acted on until Phase 2 re-runs and this seed runs again from Step 1 — Step 1's
evidence test is what makes that second run safe.

Make it durable before stopping — a warning that lives only in chat dies with the session (Step 5).
Rewrite the `**Handoff**` line of the `## Status` block to its `superseded` state, and rewrite the
body of `## Handoff` in `.specs/STATE.md` inside the same eight fields: the cause in **Blockers**,
and **Next step** reading `re-run Phase 2 for <ROADMAP-PATH>, then re-run this skill's seed` instead
of the specify trigger. Then stop.

**Cap it at three passes.** If a third pass still produces a new question or a category-4 move, stop
and say so plainly: a set of answers that keeps generating more work is evidence the scope is not
settled, and that is information the user needs — not something to grind out.

Write down what the capped pass found before falling back — dropping it is rule 1's silent default
with extra steps. Each question the last pass turned up and did not ask takes point 3's
feature-carried shape, minus the answer: the carrying feature's `open questions` field,
`status: open`, plus its matching `## Open Questions` entry — and set that feature's
`needs pre-written context.md` to `yes`, which is what that field then derives to. A category-4 edge
left unapplied is written the same way, as a question on the dependent feature naming the provider
and what the move collided with. A question no feature carries takes point 3's `cross-cutting` shape
instead — the roll-up entry with its `affects:` line **and** its `not decided` row, since the row is
the half Step 6's Blockers source 3 reads. This does not restart the pass: the cap has already taken
option B off the table, and option A is the path that tolerates a recorded open question.

Option B is off the table in that case; fall back to option A and report where it kept branching —
through point 5, whose re-run of Steps 2-6 is what promotes any of these that reaches the target into
the Handoff's **Blockers** field, so Step 10's blocker branch reports the question instead of handing
over a command. An uncapped fixpoint is how a check designed to protect an unattended run becomes an
unattended run of its own.

**5. Recompute the seed if anything moved.** Closing a question can discharge a question-only feature
(Step 2's exception), which changes the target and the remaining order — and it clears the Step 6
**Blockers** field. If any question was closed or any feature moved, re-run Steps 2–6 before emitting
the prompt, so the `## Status` block and the Handoff cannot contradict the prompt you are about to
hand over. Re-running Step 6 re-reads the ledger: a `not decided` row point 3 failed to promote will
re-block here, which is the check working, not a new problem. **A blocker surviving this re-run takes
option B off the table** — emit no loop prompt, name the question and the file its entry lives in,
and fall back to option A's blocker branch (Step 10).

**If that re-run reaches Step 4's "nothing to seed", there is no loop to hand over.** Discharging the
last unbuilt feature finishes the backlog. Say so plainly: the questions just closed are written into
the roadmap, Step 5's `## Status` block is current, and no prompt follows — Step 6 is skipped along
with Step 10, because a Handoff pointing at nothing and a loop prompt with an empty `<target>` are the
same error in two files. Do not fall back to option A either; it has no target for the same reason.

## Step 10 — Hand over the prompt, warn about the session, stop

Give the prompt **verbatim, in one copy-paste block** — the downstream skill is entered by the user
typing its trigger, so a paraphrase is a broken handoff. Resolve the placeholders exactly as the
table below prescribes — Step 6's table defines only three of the seven, and one of the seven must
not be resolved at all. Write the prose in the confirmed output language, but keep trigger phrases,
feature names and file paths exactly as they are on disk.

**Placeholders — resolve six, leave the seventh exactly as written.** The two templates use one kind
of placeholder they do not share, and mixing them up is the one way to emit a prompt that looks right
and cannot work:

| Placeholder | Emit as | Value |
|---|---|---|
| `<target>` | substituted | Step 4's target feature name |
| `<ROADMAP-PATH>` | substituted | Step 6's table |
| `<STATUS-PATH>` | substituted | Step 6's table |
| `<BUILD-ORDER-TXT>` | substituted | Step 6's table |
| `<downstream-skill>` | substituted | the skill confirmed at Phase 0 — its **name**, not its trigger phrase; both appear in the prompt and they are different strings |
| `<DISCHARGED-LIST>` | substituted | resolved below; `none` when there are none |
| `<current-feature>` | **literal — type the angle brackets** | nothing. It is the loop run's own per-iteration variable, defined inside the prompt itself |

`<current-feature>` is the only placeholder that survives into the pasted text, and it survives on
purpose. Substituting it — with `<target>` or anything else — pins every iteration to one feature:
the run re-specifies feature one forever and gates every later feature on feature one's
`validation.md`. The loop then never terminates and nothing past the first feature is ever built.
If a placeholder is not in this table, do not invent a value: stop and say which one.

`specify feature` in both templates below is `tlc-spec-driven`'s trigger. If Phase 0 confirmed a
different downstream skill, substitute **its** fresh-start trigger phrase — the same one Step 6's
**Next step** carries. A prompt built on a trigger the installed skill does not answer to is inert.

**Option A — one feature:**

```
specify feature <target> — create it at `.specs/features/<target>/` using that exact directory name.
Spec source: <ROADMAP-PATH>. Read <STATUS-PATH> `## Cross-Cutting Decisions` before Discuss and treat
it as settled — do not re-decide what it answers.
```

The directory-name clause is not redundant with Step 6. This prompt is pasted into a **fresh**
session, and the downstream skill reads `## Handoff` on resume only — so this prompt, not the
Handoff, is the only place the exact name reaches a fresh start. One drifted directory name makes
verified work look unbuilt to the next seed.

*Unless Step 6 recorded a blocker.* Then give no command at all: report the question that has to be
answered first, so the user is not handed a command that would start a feature that cannot start
cleanly.

Omit the last sentence only for a **legacy roadmap generated before Step 7 existed** — that is the
only way the block is absent, since decompose-phase's sanity check forces it to exist (all-`N/A` at
minimum) and Phase 1 pre-creates the heading in multi-section mode. Check the file before omitting;
do not reason your way into this branch. That sentence is what makes decompose-phase Step 7a reach
the build, and a prompt without it hands the user a roadmap whose project-wide answers the downstream
skill will never see.

**Option B — one roadmap in one loop.** Tell the user first that `/loop` must be the literal first
thing in the message — it is their CLI's own loop command (Claude Code, Cursor, OpenCode all have
one), and it is already baked into the front of the prompt below, so it must be pasted as-is, not
retyped after a greeting. This skill never runs that loop itself; it only writes the prompt.

**Scope rule — one loop, one roadmap, in both modes.** `<ROADMAP-PATH>` and `<BUILD-ORDER-TXT>` are
single files: Step 6's table resolves them to the target section's pair, and that is exactly right.
Never widen this to every decomposed section, and never emit a list of pairs — there is one template
because there is one roadmap per loop.

The reason is structural, not tidiness. Inside one roadmap every dependency points backwards to a
feature in the same file (rule 4), so the whole order is knowable when the prompt is written. Across
roadmaps it is not: cross-section needs are boundary contracts whose producer names are *"provisional
until that section is decomposed"* (index-phase Step 4), decomposition is lazy by design, and a
section decomposed early is the one most likely to be built against names that have since moved. A
loop crossing that seam builds the next section against a plan the previous section's shipping has
already invalidated, with no one present to notice — and the loop's only evidence, a per-feature
PASS, cannot detect it. The seam is where the user re-seeds: this procedure re-runs from Step 1,
Step 3 recounts what is really done, and the next section gets its own loop over a roadmap that can
be corrected first.

Say all of this in the same breath as the prompt: which roadmap the loop builds, which sections it
does not, and that the next one is one re-seed away.

```
/loop Implement the roadmap at <ROADMAP-PATH>, one feature at a time, in the exact order of
<BUILD-ORDER-TXT>, using the `<downstream-skill>` skill for every feature — run its full cycle
(specify → design → tasks → execute → verify). This run covers <ROADMAP-PATH> and nothing else: no
other `docs/ROADMAP*.md` file is in scope, whatever <STATUS-PATH> lists.

`<current-feature>` below is this run's own variable, not a name to resolve once. At the start of
every iteration, re-read <BUILD-ORDER-TXT> and set it to the first name at or after `<target>` that
is not on the discharged list below and has no verified PASS in
`.specs/features/<current-feature>/validation.md`. Start that feature with:
`specify feature <current-feature> — create it at `.specs/features/<current-feature>/` using that
exact directory name, spec source: <ROADMAP-PATH>`. Do not skip a feature, do not reorder them, and
do not start the next one until the current one has that verified PASS. Exception — these features
are already discharged and must be skipped, never built: <DISCHARGED-LIST>.

Before each feature's gray-area discussion, read <STATUS-PATH> `## Cross-Cutting Decisions` and
treat every entry as settled — do not re-decide it, and keep every feature consistent with it.

No user is available for this run. Dispose of every stop as follows and never wait for an answer,
but never leave one silently unrecorded either:

- A gray area not settled in `## Cross-Cutting Decisions` — treat it as declined: choose the
  default and record it with its rationale in that feature's spec under Assumptions & Open Questions.
- A request to approve this run's own spec, context, design or task list — approve and continue,
  then note in that same section which artifacts were self-approved. Nobody reviewed them, and that
  line is what lets somebody review them later.
- A choice about how to execute — sub-agents, batching, ordering inside a feature — pick one, say
  which, continue.
- A project-level fact the run cannot invent, such as which test framework to use — take it from
  `## Cross-Cutting Decisions`; if it is not there, record it as an open question and choose the most
  conservative option that exists in the repository already. Never invent a credential and never
  reach a network service to resolve one.
- A failing test — never edit, weaken, skip or delete a test to reach a PASS, and never record a
  feature as done while its suite is red. If a test is genuinely wrong, leave it failing and write
  down why. This is the one stop where continuing costs more than halting: a verified PASS is the
  only evidence this run produces, and a test bent to produce it destroys the evidence rather than
  the defect.
- **The same forgery from the implementation side is also forbidden, and it is the one that hides.**
  Never change behaviour in a way that contradicts an acceptance criterion or a settled
  `## Cross-Cutting Decisions` entry in order to turn a test green. Inverting a rule usually satisfies
  the assertion, leaves `tests/` untouched, and arrives in a diff of the source carrying no label that
  says what was traded away. When the only implementations that pass are ones the spec forbids, that
  is a genuinely wrong test: leave it red and say which criterion each rejected implementation
  violated.
- **Where a feature's own artifacts demand what this instruction forbids, this instruction wins.** A
  `tasks.md` whose done-when is *"test X passes"*, a roadmap entry claiming `open questions — none`
  while an unanswered one blocks the work — rewrite the artifact to match the acceptance criterion,
  and record that you rewrote it and why. Left unstated, this is the pressure point that manufactures
  a bent test: a task list ordering the very thing the rule refuses.

**A feature counts as done only when its `validation.md` carries a consolidated verdict line reading
PASS, with at least one `file:line` citation.** A report whose acceptance-criteria rows contain the
word `PASS` while its verdict says otherwise is **not** a pass — never decide this by searching the
file for `PASS`, which is exactly how a failed feature gets skipped. Write your own verdict so that
test cannot be got wrong: one consolidated line, and nothing above it that reads like one.

**Nobody is reviewing this run, so every verification is self-verification.** Say so in the report:
name the artifacts you approved yourself and the verdict you reached on your own work. A PASS this
run records is evidence the suite was green, not evidence anyone independent agreed — and the
difference matters to whoever reads it next.

If the same feature comes out of verification without a PASS twice, stop the whole run and report it.
Two verification runs, not two rewrites: you are never required to ship a change you have already
shown to be wrong merely to spend a cycle. Do not try a third time and do not move on to the next
feature — a feature that cannot pass is the one thing this loop cannot settle by itself, and
continuing past it builds on top of it. **This stop outranks the finishing condition below.** That
one asks for a PASS on every feature and can therefore never be reached when a feature has none;
stopping here, and saying which feature and why, is the correct end of the run.

**Write a FAIL so it cannot be misread, the same way you write a PASS.** One consolidated verdict
line and nothing above it that resembles one — per-criterion rows say `MET` / `NOT MET`, never
`PASS`. **When a criterion is met by the code and denied by the test guarding it**, say exactly that
rather than collapsing it either way: `MET, contradicted by <test>`. Calling it `MET` hides a red
suite and calling it `NOT MET` blames code that is correct, and the consolidated verdict is a FAIL in
both readings anyway — what a later reader needs is which of the two is broken.

**A phase with nothing to do is done, not skipped.** If the implementation already satisfies every
acceptance criterion, execute is complete: say so and move to verification. Do not manufacture a
change to have something to show — an edit made for that reason is indistinguishable, in a diff, from
one made to bend a result. A FAIL that a later iteration mistakes for a pass is how the loop skips past unfinished work,
which is the one outcome every rule here is aimed at.

**When a feature ends without a PASS, no task inside it is complete either.** Leave its checkboxes
unticked, whatever their individual done-whens say. A `tasks.md` full of ticks under a failed feature
is read by the next reviewer as progress that did not happen.

**Leave the work uncommitted.** No branch, no commit, no tag — a red suite entering history is a
handoff nobody asked for, and the point of stopping is that a person looks before anything lands.

**Reconcile every claim an artifact makes about itself, not only the ones named here.** `open
questions — none` beside an unanswered question is the example; a task's done-when, a comment
asserting a project fact the data beside it contradicts, a status line describing work that did not
happen are the same defect. Where the artifact and the evidence disagree, the evidence wins: fix the
artifact and record that you did.

Write the run's outcome into <STATUS-PATH> `## Status` before you stop: which feature you were on,
what state it reached, and — when you stopped — the reason, in one line each. A run that halts and
leaves no trace in the roadmap looks, to the next reader, exactly like one that never started.
Backlog position is at that same block. Stop when every name in <BUILD-ORDER-TXT> from
`<target>` onward has a verified PASS or is on the discharged list above; report and stop there
rather than continuing into another roadmap.
```

Five clauses in that template are load-bearing and easy to "tidy" into breakage. The
`<current-feature>` resume rule replaces a literal `Start at <target>`, because `/loop` re-reads the
whole prompt every iteration and a fixed start restarts at the same feature forever. The stop
condition says *"or is on the discharged list"* because a question-only feature can never earn a PASS
— without that clause the run either spins on it or fabricates a verdict.

**The two-strikes rule is the loop's only termination guarantee**, and it is easy to read as
pessimism and cut. The template forbids starting the next feature before this one has a verified
PASS, and stops only when every name has one; a feature that cannot pass therefore satisfies neither
condition and the loop re-enters it for as long as it is allowed to run. Nothing else in the prompt
bounds that.

**The failing-test clause is the one place where "never stop to ask" would be actively harmful.** The
downstream skill halts and asks when a test looks wrong (`tlc-spec-driven`'s `references/implement.md`
does exactly this); telling an unattended run never to stop, without saying what to do instead,
leaves rewriting the test as the available improvisation — and the loop's whole notion of *done* is
the verdict that test feeds. Every other disposition in that list can be audited afterwards from the
artifacts on disk. This one cannot, because it destroys the artifact that would have shown it.

And the scope sentence
matters most in multi-section mode, where `<STATUS-PATH>` **is** `docs/ROADMAP-INDEX.md`, the file
listing every other roadmap: without it a diligent run finds the rest of the backlog and keeps going.
In single-section mode that clause is vacuously true and costs one line — keep it rather than
emitting a conditional template.

The two added paragraphs are what keep the run from stalling. The downstream skill triggers its own
Discuss automatically whenever a feature has any implicit dimension present — which, in a well-formed
roadmap, includes the very first feature, since decompose-phase Step 3 puts the shared persistence
foundation there. That discussion is interactive by design and offers no "skip all". Unattended, it
either hangs on a question nobody will answer or invents an answer and leaves no trace.

**The declined-gray-area instruction is not a workaround; it is that skill's own documented
fallback** — `tlc-spec-driven`'s discuss.md already routes any gray area the user declines or leaves
undiscussed into the spec's Assumptions & Open Questions with the agent's default and rationale,
*"never silently dropped"*. The loop prompt only states, up front, that every remaining gray area is
in that state. Confirm the wording against the confirmed downstream skill's own reference; if it
defines no such fallback, say so and do not invent one — offer option A instead.

**Resolve `<DISCHARGED-LIST>` before emitting, or the loop cannot terminate.** Phase 2 may formalize
a blocking open question as its own feature (decompose-phase Step 3). It is a normal feature name in
`<BUILD-ORDER-TXT>`, but it *"produces no code, so it can never earn a PASS `validation.md`"* — it is
discharged by its question reading `status: answered`, which is exactly what Step 9 just did to every
question. Left unnamed, the prompt orders the run to wait for a PASS that can never exist: it either
spins on that feature or fabricates a verdict to get past it. Walk `<BUILD-ORDER-TXT>` against Step
2's question-only test. `<BUILD-ORDER-TXT>` supplies the **name set**: **one** file, as Step 6's table
resolved it, from `<target>` to its end. It carries names only — no comments, no markers
(decompose-phase Step 8) — so look each name up in `<ROADMAP-PATH>` and keep the ones whose entry
carries Step 2's `discharge:` line; write `none` when there are none. It is singular in both modes
because the loop is (scope rule above). Names before `<target>` are behind the run, and names from
another section's `.txt` are not in this file and the run never reaches them — listing either only
sends the run looking for a feature it has no order for.

Point at the paths; never paste the roadmap's contents into the prompt — the files are on disk and
the run will read them, and an inlined copy goes stale the moment anything is edited. The sections
this loop does not cover are named in the surrounding message, never inside the prompt: the prompt is
an instruction to one run over one roadmap, and a list of roadmaps it must not touch is an invitation
to touch them. If the user's tool has no `/loop`, the body still works as a plain instruction — say
so, and say the run will then need supervising.

**Say where the loop's own decisions will be waiting.** Each gray area the cross-cutting ledger has
not already settled gets the run's default, recorded with its rationale in that feature's
`.specs/features/<name>/spec.md`, under its Assumptions & Open Questions section — one spec per
feature the loop builds. Tell the user, in the surrounding message, that reading those sections once
the loop ends is the next step this handoff expects and not extra work option B created: they are
where every call made on the user's behalf comes back, each with the reason it was made. Say it out
here only — the prompt already carries the instruction that writes them, and reviewing them is the
user's job after the run, not an instruction the run can act on.

**Then the session warning — both options, every time, unconditionally.** Do not omit it because the
option looked simple or the session felt short. Render it prominently, in the confirmed output
language:

> ⚠️ **Open a new chat session before running this prompt.** Paste it into a fresh session with clean
> context — not this one. This session is full of scope and decomposition reasoning that construction
> does not need; the downstream skill re-derives everything it needs from the paths in this prompt and
> the roadmap files on disk — and from `.specs/STATE.md` on any later `resume work`, which is what the
> Handoff is for. Building here risks the agent working from remembered conversation instead of the
> written artifacts, and it starts the build with the context budget already spent.

**Optional bridge, offered as text — never written automatically.** The downstream skill reaches
`docs/` only through its Knowledge Verification Chain, which names the directory and no file — and
the Handoff's own pointer is gone at the first `pause work`, since that section is overwritten. So
offer these lines every time, and let what is on disk decide only where they go: if the project has
a `CLAUDE.md`, offer them to paste into it; if it has none, name the file their agent auto-loads at
project root — `CLAUDE.md` for Claude Code, the equivalent for whatever tool they use — and hand
them the same lines to put there. A missing `CLAUDE.md` changes the destination, never whether the
offer is made. Either way this is output and nothing else: create no file, edit no file, and leave
the paste to them (their file, their call).

```markdown
- `docs/ROADMAP-INDEX.md` `## Status` — current backlog position and the next feature to build.
- `docs/ROADMAP-INDEX.md` `## Cross-Cutting Decisions` — project-wide decisions already made with
  the user (deletion policy, auth model, failure handling, …). Read before discussing gray areas;
  treat as settled and keep every feature consistent with it.
- `docs/ROADMAP-*.md` — per-feature objective, scope-units, dependencies, flagged dimensions.
  Read the relevant section before specifying a feature.
```

In single-section mode both blocks are in `docs/ROADMAP.md`; adjust the paths accordingly. This
bridge is the durable half of the delivery: the Handoff's **Next step** carries the pointer for the
next feature only, while these lines make it reach every feature after it.

**Say what declining costs, so the choice is an informed one.** Once the first `pause work`
overwrites **Next step**, nothing left in the project points a hand-started session at
the `## Cross-Cutting Decisions` block, so every later feature's Discuss begins blind to
decisions already made with the user — and re-asks them, per feature, answered inconsistently.
Under option B the loop prompt carries its own pointer to that block for as long as that loop
runs; a session started by hand afterwards, or instead of it, carries none. Say this once, as the
reason the lines are worth pasting, and then accept whatever they decide.

Then stop. Do not wait, do not poll `validation.md`, do not check back in — including under option B,
where the loop is the user's CLI running the downstream skill, not this skill continuing. If asked to
seed again later, this procedure simply re-runs from Step 1, and Step 1's evidence test is what keeps
it from clobbering real progress.
