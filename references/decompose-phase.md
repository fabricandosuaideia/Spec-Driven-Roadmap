# Phase 2 — Decomposing Into Features

## Contents

- [Mode differences and inputs](#mode-differences-and-inputs)
- [Step 1 — Enumerate the scope-units first](#step-1--enumerate-the-scope-units-first)
- [Step 2 — Derive the feature execution order](#step-2--derive-the-feature-execution-order)
- [Step 3 — Slice into features](#step-3--slice-into-features)
- [Step 4 — Shared ownership across sections](#step-4--shared-ownership-across-sections) (multi-section only)
- [Step 5 — Defer work that cannot be built yet](#step-5--defer-work-that-cannot-be-built-yet) (multi-section only)
- [Step 6 — Write each feature with all ten fields](#step-6--write-each-feature-with-all-ten-fields)
- [Step 7 — Pre-empt the gray areas](#step-7--pre-empt-the-gray-areas)
- [Step 8 — Close the roadmap](#step-8--close-the-roadmap)
- [When to re-run, and what is frozen](#when-to-re-run-and-what-is-frozen)
- [Sanity checks](#sanity-checks)

## Mode differences and inputs

- **Multi-section mode:** run per section, lazily, right before the user is ready to build it.
  Decomposing a section that will not be built for weeks risks staleness; just-in-time keeps each
  roadmap close to what is actually about to be built. If the user wants the whole backlog visible
  upfront, that is a fine reason to run it for every section — just not the default.
  *Load:* `docs/ROADMAP-INDEX.md` (this section's prefix, dependencies, and boundary contracts), the
  target section's own content, and the project's conventions doc. **Never load a sibling section in
  full** — a need for sibling detail is already captured as a boundary contract; cite it.
- **Single-section mode:** run once against the whole source. No index, no per-section prefix table,
  no boundary contracts. Assign one project-level prefix up front — **lowercase kebab-case**, short
  and mnemonic, and not colliding with a prefix in `docs/ROADMAP-*.md`, `docs/ROADMAP.md` or on a
  `.specs/features/*` directory (index-phase.md Step 2 sets the same rule for slugs). Case and
  underscores are not cosmetic here: a later conversion derives the section slug from this prefix
  and takes lowercase kebab-case only, while feature names freeze once `.specs/features/<name>/`
  exists. Every "external contract consumed" is "none".
  *Load:* the whole source and the conventions doc.

## Step 1 — Enumerate the scope-units first

**Build a compact inventory before decomposing anything:** one line per scope-unit — its ID, a short
label, and **what the unit leaves unsaid**, or `—` when it leaves nothing. Whatever the source's
atomic unit is (a diagram node, a requirement ID, a table row, an `M1`/`G1` bullet from Phase 0b/0c),
it gets a line.

Decompose from that inventory, re-reading the full text only for the unit you are currently writing
a feature for. This is what keeps a large source tractable and what makes the coverage table
trustworthy — a unit that was never enumerated cannot be noticed as missing later.

**The third part is written here because here is the only place it can be seen.** A label records
what the unit *is*, and a unit never looks like it is missing what it does not mention: *"sign-up
takes an e-mail and a password"* names no rule for what a valid password is and reads complete
anyway. The pass above is the one moment the whole source is open — after it the reading narrows to
one unit at a time, and a silence inside a unit stops being visible.

**Then walk the entities, not the pairs.** For each entity named by more than one scope-unit — an
item, a vote, an account; usually a handful — ask what one unit's operation does to state another
unit owns. *Editing an item after votes are already cast* is that shape, and it is unfindable later:
Step 3 assigns each unit to exactly one feature, so two units that interact are never in the same
field of view again. Comparing every pair of units instead is quadratic — 26 units is 325 pairs —
and spends the tractability this inventory exists to buy.

Both sweeps produce working state, not output. Nothing here is decided, and nothing is yet a question
or a forecast: Step 7's three tests route each mark, and Step 8 checks that each one arrived.

**Requirements that are not units are inventoried too.** A constraints section, a non-functional
requirement, a global rule: none of them is a scope-unit, none earns a feature, and none gets a row
in Step 8's coverage table. Enumerating them anyway is what keeps `uncovered: none` from overstating
itself — instead of a disposition, the line names where the requirement lands: the features it binds,
or a row of `## Cross-Cutting Decisions`. The table then covers the units, and nothing else in the
source ends the phase with no destination.

**If the source cannot be enumerated in one pass, stop and say so**, and recommend multi-section mode
instead. Silently reading part of a large document and producing a confident coverage table is the
one failure this phase must not have.

## Step 2 — Derive the feature execution order

- If the section has internal structure (a sequence, edges between its units, an explicit pipeline),
  derive the order from that and show the derivation — a small dependency diagram is enough.
- Otherwise order by natural build dependency: foundational persistence first, shared modules next,
  consumers after, cross-cutting extras (export, admin tooling, toggles) last.
- **If the source declares an MVP or v1 boundary, every feature inside it is ordered before every
  feature outside it**, dependencies permitting. A `## MVP Scope` from Phase 0b is exactly such a
  boundary.
- A section's graph is sometimes one long linear pipeline. Say so when it is; do not invent a
  fan-out to make the diagram look richer than reality.

## Step 3 — Slice into features

**Every feature is a vertical slice** — route + service + persistence + test for one coherent
capability. "The whole schema", "the whole API layer", "all the UI" is not a feature. Never slice by
architectural layer; the one bounded exception is the shared-foundation move below.

Assign every scope-unit to exactly one feature. A feature typically groups several related units (a
table + the module that reads it + the rule that governs it) and never re-declares a unit already
claimed elsewhere.

Units marked `pre-existing` (Phase 0c's `## Capabilities Already Built`) are enumerated in Step 1 and
appear in the coverage table with that disposition, but get no feature — they are already built.
A source's explicit out-of-scope statements — Phase 0b's `## Explicitly Out of Scope`, or an existing
document's own out-of-scope section — are **not** scope-units at all: they are never enumerated,
never appear in the coverage table, and never become features.

Common slicing moves:

- **Shared foundation first.** When several downstream features read/write the same schema or reuse
  the same interface, give it its own feature ahead of them (a `-schema` or `-registry` feature),
  even if no edge in the source points there first — persistence must exist before anything writes
  to it. This is rule 2's one bounded exception, so **name its consumers** in the objective; a
  foundation with fewer than three consumers should just be folded into the feature that uses it.
- **One feature per swappable adapter.** An abstract interface with multiple concrete
  implementations gives each implementation its own feature behind the shared foundation. They
  usually carry independent "confirm the technology" open questions and should not be bundled.
- **Correction and gap-only features are legitimate.** Not everything buildable has a matching unit
  in the source. Write it anyway, marked "no scope-unit — originated from `<the correction>`". Never
  force a fake citation, never drop it silently.
- **Formalize a blocking open question as its own feature.** When an unresolved architectural
  question gates several downstream features, give it a small feature whose first task is getting it
  answered. Dependents depend on that feature, never on a guessed answer. Such a feature produces no
  code, so it can never earn a PASS `validation.md` — record its discharge explicitly instead: it is
  done when the answer is written into this roadmap's `## Open Questions` with `status: answered`,
  or when `.specs/features/<name>/context.md` exists. Mark it in the feature's own entry with this
  exact line, verbatim, so the seed finds it without parsing prose:
  `discharge: no code — answered open question or context.md`. Three separate consumers key off that
  line (the seed's done-test, its target pick, and the loop prompt's skip list); a prose paraphrase
  that varies per run either strands the seed on a feature that can never PASS, or lets a real
  feature be skipped as discharged.
- **Split at eight tasks.** When honest counting exceeds eight, split along the clearest internal
  seam (read-path vs. write-path; core vs. add-on) and state the reason in both halves.

## Step 4 — Shared ownership across sections

*Multi-section mode only.*

Sometimes a unit structurally sits in section C but must be built by section A because C depends on
it. Resolve by:

1. Following `docs/ROADMAP-INDEX.md`'s boundary contracts if they already made the call.
2. If the index is silent, deciding by genuine build necessity and **recording it in both roadmaps**:
   the owning roadmap's feature lists the unit as covered with a note on why it lives there; the
   consuming roadmap's coverage table marks it `covered by reference to <owning-roadmap>/<feature>`.
   *If the consuming roadmap does not exist yet* — the normal case, since decomposition is lazy —
   record the ownership call in `docs/ROADMAP-INDEX.md`'s boundary contract for that edge instead.
   That roadmap picks it up from there when it is eventually decomposed. Never create a roadmap file
   early just to hold one coverage row.

Never build the same schema twice, and never let a unit vanish because each side assumed the other
claimed it.

## Step 5 — Defer work that cannot be built yet

*Multi-section mode only.*

A requirement may apply here but need a mechanism only a later section provides. Do not invert the
build order. Instead: leave it out of this feature list; add a note naming what is deferred, to which
roadmap, and why (citing the missing dependency); mark the unit `deferred` in the coverage table
(Step 8). When that later roadmap is decomposed, add the feature there with a cross-reference back.
This skill keeps no to-do list of its own — the note in the roadmap is the only record.

## Step 6 — Write each feature with all ten fields

- **name** — `<prefix>-<kebab-case>`, unique across the project. English, always (it becomes a
  directory name).
- **objective** — one sentence.
- **scope-units covered** — the source's own IDs, or "none — originated from `<X>`".
- **depends on** — features earlier in this same roadmap; "—" for the first.
- **external contract consumed** — an item from the index's boundary contracts, or "none" (always
  "none" in single-section mode).
- **size** — Small / Medium / Large / Complex, consistent within the roadmap. Complex usually means
  it should have been split in Step 3.
- **task estimate** — a number, ≤8. That is rule 3's maximum, not a target: above it Step 3 is not
  finished — split per its **Split at eight tasks** move.
- **implicit dimensions present** — any of: persistence/state, external calls, auth, payments,
  concurrency, state transitions; or "none". These are the dimensions that trigger the downstream
  skill's own Discuss step.
- **open questions** — one line per unresolved point, phrased as a question, citing the exact place
  in the source that leaves it open, each tagged `status: open` or `status: answered`; or "none".
  **This is where rule 1's refusal to guess actually lands** — without this field there is nowhere to
  put an ambiguity, and it gets silently resolved or dropped. When there are none, write `none` and
  stop: a qualified `none — settled in the ledger` is not the same value to anything that matches
  this field, which reads it as a carried question and then hunts for the roll-up entry it never
  got. Qualify it in the ledger row or the roll-up, never here.
- **needs pre-written context.md** — yes if any dimension is present or any open question is
  `status: open`; no otherwise.
- **discharge** — *question-only features only* (Step 3): the literal line
  `discharge: no code — answered open question or context.md`. Not one of the ten; absent on every
  other feature, and the seed's done-test, its target pick and the loop's skip list all key off it
  verbatim.

## Step 7 — Pre-empt the gray areas

The downstream skill runs its own gray-area discussion inside Specify, automatically, for every
feature with a dimension present. **That step belongs where it is** — it decides implementation shape
with the code in front of it, and `tlc-spec-driven`'s own rule is *"facts you look up; decisions you
ask"*. A question asked here, that the built code would have answered for free later, spends the
user's attention and gets asked again anyway.

So this step does not try to pre-empt everything. It separates the decisions that are genuinely wrong
to leave until then from the ones that are right to leave until then.

**The test — all three, or it is not asked here:**

1. **Only the user can decide it** — product or business judgment, not discoverable by reading code,
   config or existing conventions.
2. **It reaches beyond one feature** — two or more features, or a project-wide invariant.
3. **Reversing it later is expensive** — it gets embedded in several features, so changing it means
   reworking all of them.

**Test 1 is a gate; tests 2 and 3 are a router.** Read in the obvious way — "fails any of the three,
so it is not asked" — the list sends a decision only the user can make into `## Expected Gray Areas`
the moment it happens to be feature-local, and that block is swept by nothing: the loop gate skips it
by design and Discuss picks a default. That is rule 1's silent default with a different label on it,
and two independent runs of this phase invented their own tie-break rather than follow it.

So: **failing test 1 is the only route to `## Expected Gray Areas`.** If the answer exists in code,
config or an existing convention, it was never an ambiguity — it is a lookup, and Discuss resolves it
better later. If it exists nowhere but in the user's head, it is recorded as a question no matter how
small its blast radius; tests 2 and 3 then decide only *where* — the ledger and the roll-up when both
pass, the carrying feature's own `open questions` field when either fails.

This does not widen the sweep. Rule 8's economy is test 1 itself: the thing that "the built code
would have answered later" fails it and still goes to `## Expected Gray Areas`, exactly as before.
What changes is that a user-only decision can no longer be filed there for being small.

Test 2 is the load-bearing one for *routing*, and not by accident. A decision that spans features is a decision
whose effects propagate — and the downstream Discuss is scoped to one feature at a time, with an
explicit guardrail against leaving that boundary. That whole class is invisible from inside any
single feature's discussion. It is the one thing this phase can see and that phase structurally
cannot.

### 7a — Sweep the cross-cutting themes, once per project

The checklist is not a new invention: it is the downstream skill's own canonical
**implicit-requirement dimensions rubric**, asked once at project scope instead of once per feature.
Read that rubric from the confirmed skill's own reference before using it — the table below is
`tlc-spec-driven` v3.x's nine, from `references/specify.md`, and a different downstream skill will
have its own, of its own length.

**If Phase 0 recorded that no skill is installed, use the table below as the rubric** — it is the
default assumption's, and the ledger has to be complete for a human reader too. Note in the block
which rubric it was built against, so a later run under a confirmed skill can reconcile it.

**This rubric is not Step 6's dimension flags.** Those six — persistence/state, external calls, auth,
payments, concurrency, state transitions — are that skill's Discuss **trigger** list, from
`discuss.md`; they answer *whether* Discuss fires. The rubric answers *what it will ask*. There is no
`payments` theme and no `persistence/state` theme, and there need not be: a payments feature's gray
areas land under idempotency/retry/dedup, failure/partial-failure, external-dependency failure and
auth boundaries. **Map the gray area to a theme, never the feature's flag to a theme.**

| Theme | The project-level decision |
|---|---|
| Input validation & bounds | Where validation lives, the canonical error shape, standard limits |
| Failure / partial-failure states | On a partial write: roll back, compensate, or leave pending — and is it user-visible |
| Idempotency / retry / duplicate handling | Which operations are safely retryable, and what makes two calls duplicates |
| Auth boundaries & rate limits | The identity/role model, who may act on whose data, throttle policy |
| Concurrency / ordering | Last-write-wins vs. optimistic locking; what ordering is guaranteed |
| Data lifecycle / expiry | Soft vs. hard delete, cascade rules, retention, archival |
| Observability | What is logged and traced as a baseline, and what must never be (PII) |
| External-dependency failure | Timeouts, fallbacks, and whether the system degrades or fails when a third party is down |
| State-transition integrity | The canonical state machines and their guards |

**A gray area that passes all three tests but matches no rubric theme still gets a row.** The rubric
is the downstream skill's list of what *its* Discuss will ask; it is not a claim that every
project-wide decision falls inside it. Two independent runs of this phase hit the same wall — *"which
channel do notifications go out on?"* and *"which e-mail provider?"* — both passing only-the-user-
decides, spans-two-or-more-features and expensive-to-reverse, and neither mapping onto any of the
nine. The literal reading leaves them unwritable: rule 1 says every ambiguity has a home, Step 8 says
a `cross-cutting` entry names its rubric theme, and this step caps the ledger at one row per theme.
Both runs demoted the question to a single feature, which under-reports its reach — the seed then
never blocks the other features the answer governs, which is the one thing `affects:` exists to
prevent.

So: add a row named for the decision itself, marked `project-specific` where a theme name would go.
It follows every other rule — one row, one of the four states, and an `## Open Questions` entry
tagged `cross-cutting` with an `affects:` line when it is left unanswered. The sanity check below
counts rubric themes; `project-specific` rows are additional and are not counted against it. Do not
invent these to pad the ledger: a row here has to have passed all three tests, and the burden of
showing that is on the row.

**Only themes the roadmap actually touches get asked.** For each theme: either features in this
roadmap touch it — then ask — or record it as `N/A because <reason> (as of <this-roadmap>)`. That
escape is mandatory, and its reasoning is borrowed from the same skill's own dimensions sweep: it
stops the checklist being padded with invented requirements while still proving nothing was silently
skipped. Only the reasoning is borrowed — that sweep is scoped by feature size (full for
Large/Complex, collapsed for Medium, skipped entirely for Small) and this one is unconditional. The
asymmetry is the point: a Small feature skips the sweep downstream, so the rubric is never walked for
it — its Discuss still fires on any dimension present, but only over the three or four
feature-specific gray areas it generates, so a project-wide invariant gets decided feature-locally
and inconsistently, or not at all.

**Ask them batched, with a recommended default and one line of reasoning each**, so the user accepts
or overrides in a word — the shape the downstream skill's own "Quick" pace uses. These are few (nine
at the absolute most, usually three or four) and they are the payload of this step; do not drip-feed
them one per turn. This is the one place the skill batches: Phase 0 asks one at a time and so does the
seed's loop interview, because there each answer reshapes the next. These do not — they are
independent themes carrying defaults, and drip-feeding nine of them is what makes a user stop reading.

**A recommended default is not a decided ambiguity.** Rule 1 forbids picking a silent default; it
does not forbid proposing one the user can accept in a word. The dividing line is the answer: an
accepted default is the user's decision. An **unanswered** one is not, and never becomes one by
silence.

**`## Cross-Cutting Decisions` is a ledger of the rubric's themes, not a list of answers.** Every
theme carries exactly one row, in exactly one of **four** states — the first three below, and a
fourth that has two ways in:

- `<decision> — <one line of rationale>` — the user answered it, or accepted a proposed default.
- `N/A because <reason> (as of <this-roadmap>)` — no feature decomposed so far touches it.
- `not decided — see the <theme> entry in <roadmap-path> ## Open Questions` — asked, left unanswered.
- ``deferred to feature `<name>` — see its `open questions``` — the theme's answer waits on a
  question a feature already carries. Two ways in: the promotion below replaces a `not decided` row
  with it, **and** it is written directly when some feature's `open questions` field already holds
  the question this theme turns on. Nothing else may be written directly in its place — a theme
  waiting on a feature-carried question has no `cross-cutting` entry for a `not decided` row to point
  at, and a row pointing at nothing fails the sanity check below.

The third state is what lets the block be complete without deciding anything, and completeness is the
block's whole value: the downstream skill reads it before every Discuss, so "not listed here" has to
mean "this project has no such theme" and never "we forgot". An unanswered theme that simply vanishes
reads as settled to a build that never sees the roll-up.

**No row in the decided state may presuppose the answer to a question that is still `status: open`.**
A row settling how two votes are recognised as duplicates, while the vote model itself is an open
question, is a decision nobody made — and it does more damage than a missing row would: the ledger is
what the build reads *instead of* re-deciding, so the guess inherits its authority and reaches every
feature the answer touches. Where a theme is part settled and part waiting, one row carries both: the
settled part as its decision, and the literal phrase ``deferred to feature `<name>``` for the rest.
That keeps what was legitimately decided instead of throwing it away with a whole-theme deferral.
Keep the phrase verbatim: `scripts/check-roadmap.py` matches it as a substring to classify the row,
and the seed's Blocker gate keys off the same wording ([handoff-seed.md](handoff-seed.md) Step 6). A
paraphrase leaves the row reading as a plain decision to both.

**An unanswered theme is written in two places, and neither of them is a decision.** It passed test 2,
so no feature carries it — the roll-up entry *is* its carrier, and it must say what it reaches:

- In this roadmap's `## Open Questions`: one entry tagged `cross-cutting`, `status: open`, naming its
  **rubric theme** where a feature-carried question names its feature, and carrying an **`affects:`**
  line listing the features the answer would reach.
- In `## Cross-Cutting Decisions`: that theme's `not decided` row, pointing back at the entry. Theme,
  state and path only — never the question text, never a proposed answer. A second copy is a second
  thing to keep in sync; the row exists so a reader who opens only the project-level block still sees
  the gap, and that is every reader the Handoff sends there.

**`affects:` has exactly two legal forms.** Feature names are globally unique and slug-prefixed
(rule 6), so no qualifier is needed and the notation is identical in both modes:

- `affects: <feature-name>, <feature-name>, …` — exactly those features, anywhere in the project.
- `affects: all` — every feature in the project, including sections not yet decomposed.

**`all` is the default; naming a subset is the positive claim.** Assert it here, with the whole
feature list in front of you, or not at all — the seed reads this line and never re-derives it, and a
later reader narrowing it with less information is deciding an ambiguity. Under-listing is the
expensive error: it lets a feature be built against a guess, the one thing rule 1 exists to prevent.

If `affects:` ends up naming most of the roadmap, use Step 3's "formalize a blocking open question as
its own feature" instead: a question that gates the backlog belongs in the dependency graph, where
the order already enforces it, not in a gate every seed re-reads. That move changes the theme's row
too: write ``deferred to feature `<name>` — see its `open questions``` in place of `not decided`. It
is the fourth row state listed above, exempt from the `cross-cutting` sanity check below, and the seed does
not block on it — after the promotion the question is feature-carried, so it has no `cross-cutting`
tag and no `affects:` line, and a `not decided` row left behind would block every target including
the feature created to answer it.

**Where the block lives — exactly one per project, like `## Status`:**

- Single-section mode → `## Cross-Cutting Decisions` in `docs/ROADMAP.md`.
- Multi-section mode → in `docs/ROADMAP-INDEX.md`. Section roadmaps reference it, never restate it.

Multi-section decomposition is lazy, so a later section runs this step against a ledger that already
exists. **Read it first, and treat its states differently:**

- A **decision** is settled — never re-ask it. A second answer to a settled theme is exactly how two
  sections end up built against contradicting rules.
- An **`N/A because` row is not an answer.** It records only that no roadmap decomposed *so far*
  touched the theme, which is why it carries the roadmap that wrote it. If this section touches that
  theme, ask it now and **replace** the row, noting which roadmap changed it. Leaving it is the same
  failure as re-answering a settled theme arriving from the other side: a project-wide invariant
  nobody ever decided, silently inherited by every feature that needs it.
- A **`not decided` row** is re-asked if this section touches the theme, but the outcome goes to the
  one entry the row already points at — an answer promotes the row; still unanswered, append this
  section's features to that entry's `affects:` line. Two entries for one theme is two `affects:`
  lines to keep in sync, and one will be wrong.
- A **`deferred to feature`** row needs nothing from this section: the question is feature-carried
  and the build order already enforces it. Do not re-ask the theme, do not rewrite the row, and
  create no `cross-cutting` entry for it.

If Phase 1 Step 5 listed project-level decision candidates, they are inputs here — a candidate that
passes the three tests becomes one of these rows.

### 7b — Everything else is recorded, not asked

A gray area that fails **test 1** is not asked here. It goes into an `## Expected Gray Areas`
roll-up: one line each, naming the feature that carries it, the rubric theme it belongs to, and
**where the answer already lives** — the code, the config, or an existing convention. That is the
only legal reason for a line to be in this block, and stating it is what makes the line auditable;
without it the block is indistinguishable from a list of things nobody got round to asking.

`feature-local` and `cheap to reverse` are **not** reasons to file something here. They are the
routing tests, and a user-only decision that fails them belongs in its feature's `open questions`
field (Step 7's gate). A line here whose stated reason is one of those two is misfiled, and the
sanity check below catches it.

**Record only what this sweep actually turned up.** This block is 7a's residue, not a forecast of
Discuss's agenda. Discuss generates its own gray areas per feature with the code in front of it —
predicting them here is invention, it restates what `implicit dimensions present` already flags, and
it scales the block at three or four lines per feature until the roadmap is mostly this block.

This block never blocks anything. It exists so the user can see, before building starts, the kind and
volume of implementation-shape calls that are coming — and so the loop path knows these are
deliberately not being asked ([handoff-seed.md](handoff-seed.md) Step 9).

**Each gray area gets one home, and the three blocks never overlap in form.** They answer different
questions about the same subject matter:

| Block | Form | Holds |
|---|---|---|
| `## Cross-Cutting Decisions` | a rule | the standing answer the build obeys — one row per rubric theme |
| `## Open Questions` | a question | what nobody has answered yet, `status:` tagged |
| `## Expected Gray Areas` | a forecast | what Discuss will decide later, and which test says it belongs there |

Routing is exclusive; form is not, and must not be. An unanswered theme is a question in
`## Open Questions` *and* a `not decided` row in the ledger — one gray area in two forms, not two
copies, and deleting either half loses a real reader something. Answering it turns the row into a
decision while the question stays, tagged `status: answered`, as the record of where the decision
came from ([handoff-seed.md](handoff-seed.md) Step 9 point 3).

**`## Open Questions` and `## Expected Gray Areas` are the pair that must stay strictly disjoint.**
The loop gate sweeps the first and deliberately skips the second, so an item in both gets asked after
this step decided not to ask it, and an item in the wrong one is either a re-asked question or a
genuine gap a loop runs straight past.

### 7c — This step never expands scope

Mirror the downstream skill's own Discuss guardrail: this pre-pass clarifies HOW, never WHETHER. If
an answer implies a capability no feature covers, it does not get quietly folded into a nearby
feature — it goes through Step 8's coverage table, and if it is genuinely new scope, through a
Phase 2 re-run under "When to re-run, and what is frozen". A cross-cutting sweep that grows the
backlog has stopped being a sweep.

## Step 8 — Close the roadmap

- **Coverage table:** one row per scope-unit → its disposition. Four dispositions are valid:
  - `<feature-name>` — built by that feature in this roadmap.
  - `covered by reference to <roadmap>/<feature>` — owned by another section (Step 4).
  - `deferred to <roadmap> — blocked on <dependency>` — cannot be built yet (Step 5).
  - `pre-existing — already built, verified in codebase` — from Phase 0c's
    `## Capabilities Already Built`; not new scope.

  Close with `uncovered: none (N deferred, N pre-existing, listed above)` — add a third count,
  `N covered by reference`, before `listed above` when any row carries that disposition. A genuinely
  uncovered unit means Step 3 is not finished.
- **`## Open Questions` roll-up:** the project's one authoritative list of unanswered points, and a
  **superset** of the per-feature fields. The block holds entries and nothing else — no bulleted
  preamble describing the section, because a bullet that carries a `status:` tag and names neither a
  feature nor a rubric theme is indistinguishable from an entry that forgot to. Two kinds of entry:
  - one per question in any feature's `open questions` field — same text, same `status:` tag, plus
    the name of the feature that carries it. A deliberate copy, not a summary: the agent specifying
    one feature reads that feature's entry and must not have to walk the whole roadmap, while the
    seed reads one flat list by name and must not have to walk every feature. Two indexes, one set.
  - one per Step 7a theme asked and left unanswered, tagged `cross-cutting`. These have **no carrying
    feature** — they name their rubric theme instead, and carry the `affects:` line. That tag is how
    a later reader tells a project-wide gap from a feature-local one, how the seed blocks a feature
    whose own field can never show it, and how [handoff-seed.md](handoff-seed.md) Step 9 knows to
    settle the ledger row when it is answered.

  **Keep the copy exact, in the same edit.** A field entry with no roll-up entry, or a roll-up entry
  answered while the feature's field still reads `status: open`, is the one failure this arrangement
  is exposed to. **Answered entries stay** — never deleted; the answer itself is the record, and it
  is what discharges a question-only feature. Omit the section only when there are no questions at
  all.
- **`## Expected Gray Areas` roll-up** (Step 7b): the decisions deliberately left to the downstream
  skill's own Discuss, one line each — feature, rubric theme, the test it failed. Never a blocker,
  never swept by the loop gate, and never overlapping `## Open Questions` or any feature's own
  `open questions` field. Omit the section when there are none.
- **`## Cross-Cutting Decisions`** (Step 7a): single-section mode only — in multi-section mode this
  block lives in `docs/ROADMAP-INDEX.md`, exactly one per project. One row per rubric theme, each in
  one of Step 7a's four states: the decision plus one line of rationale, `N/A because <reason>
  (as of <roadmap>)`, `not decided` pointing at its `## Open Questions` entry, or
  ``deferred to feature `<name>` — see its `open questions``` when the theme's answer waits on a
  question a feature already carries — whether the theme was promoted into its own question-only
  feature (Step 3) or the question already sat in that feature's field (Step 7a). One row per theme
  is both floor and ceiling — this is the block the build reads instead of re-deciding, so a missing
  row reads as "no such concern in this project".
- **Execution-order block:** a fenced list, one feature name per line, respecting every "depends on".
  When the source declares increments, mark their boundaries here with a comment line:
  `# --- end of increment 1: <what ships here> ---`.
- **Standalone `.txt`:** `docs/roadmap-<slug>.txt` (multi-section) or `docs/roadmap.txt` (single):
  **feature names only, one per line — no status markers, no comments, no increment lines.** Keep the
  increment markers in the markdown block above; this file is machine-read by two consumers — the
  seed counts its feature-name lines to compute progress, and `scripts/convert-to-multi.py` matches
  every one against the roadmap's `### ` entries and aborts on a name that has none. Both readers
  skip blank lines and `#` lines defensively, but a status marker or any other non-name line
  inflates the seed's total and trips the conversion. The seed never re-parses the markdown, so this
  file must stay trivially parseable.
- **Discharge Step 1's third part**, which writes nothing at all. Walk the inventory once more: every
  scope-unit whose unsaid part is not `—`, and every entity interaction that pass recorded, has to
  have reached one of this phase's three homes — the carrying feature's `open questions` field with
  its matching roll-up entry (rule 1); the `cross-cutting` pair, an entry with its `affects:` line
  plus that theme's ledger row (rule 8); or a gray-areas line naming the test it failed (Step 7b).
  The inventory stays working state: no fourth home, no new field, no new section, nothing a reader
  of the finished file could tell this pass from. What it catches is the gap that was visible while
  the whole source was open and then quietly dropped — rule 1 broken with nobody deciding anything.
  If discharging turns the gray-areas roll-up into a line per scope-unit, the marks were padding
  rather than gaps: re-read 7b's *"Record only what this sweep actually turned up"* and cut back to
  what the sweep found.

### Output shape of the roadmap file

`docs/ROADMAP.md` (single-section) or `docs/ROADMAP-<slug>.md` (multi-section):

1. H1 title. When the size question below was re-raised and answered, its one-line record sits here
   too — plain text between the H1 and `## Status`, never inside either (the size bullet under
   `Sanity checks` gives the wording and says why nowhere else works).
2. `## Status` — **single-section mode only.** Written and refreshed by the Handoff seed; leave the
   heading in place even before the first seed. (In multi-section mode this block lives in
   `docs/ROADMAP-INDEX.md` instead — exactly one `## Status` exists per project.)
3. `## Cross-Cutting Decisions` — **single-section mode only**, same reason: in multi-section mode it
   lives in `docs/ROADMAP-INDEX.md`, exactly one per project.
4. The feature entries, each with all ten fields (Step 6). **Each one is a `### <feature-name>`
   heading** — level three, the bare name, nothing else on the line. That form is not cosmetic: four
   consumers depend on it. The seed's Step 5 replaces the `## Status` body up to the next heading of
   any level, so a feature written at `##` would be swallowed by that block; `scripts/convert-to-multi.py`
   reads these entries to reconcile `docs/roadmap.txt` against the roadmap, and finds none if they
   are a table or a list; index-phase.md's conversion resolves the section slug against them; and a
   human reading the file navigates by them.
5. `## Open Questions` roll-up.
6. `## Expected Gray Areas` roll-up.
7. `## Coverage` — the coverage table, closing with the `uncovered:` line. Keep that exact heading:
   `scripts/check-roadmap.py` scopes its `uncovered:` read to this block, and says so instead of
   judging when the heading is missing.
8. `## Execution Order` — the execution-order block, a fenced list.

## When to re-run, and what is frozen

Re-running is normal — the source gains requirements as the project moves. **Never wholesale-
regenerate a roadmap that already covers the current scope; extend it.**

**Extending is one of two right answers, and the prohibition above rules out only the third.** Extend
for small, continuous growth — a few features arriving on top of scope this roadmap already
describes. **A distinct wave of work is better as its own section**, because the loop prompt names
one roadmap as the spec source for every feature it builds ([handoff-seed.md](handoff-seed.md)
Step 10), so an extended roadmap re-enters context once per feature in every wave it absorbed. That
choice is the user's and is made in Phase 0, never here — the full argument, and what a DONE section
does and does not still cost, is `New scope arriving at a project that already has a roadmap` in
[scope-phase.md](scope-phase.md).

Before rewriting anything, list every feature name that already has a `.specs/features/<name>/`
directory. Those names **and their relative order are frozen**:

- Never rename a feature that has been built or started. The seed identifies done work purely by
  name, so one rename makes verified work look unbuilt and points the downstream skill at something
  already shipped — while the old directory keeps existing, breaking rule 6's uniqueness.
- New scope appends after the frozen block.
- A feature that turned out obsolete is marked superseded in place, with a note; never deleted, never
  renamed.
- The `.txt` is append-mostly: reordering it only among not-yet-started features is fine.

## Sanity checks

**Run them, then read for what a command cannot see.**

```
python3 <skill-dir>/scripts/check-roadmap.py --root <project-root>
```

It covers the countable half of the list below — forward dependencies, duplicate names, the task
budget, the `discharge:` line verbatim, the two-way agreement between each feature's `open questions`
and the roll-up, one row per rubric theme, every `not decided` row having its `cross-cutting` entry
with an `affects:` line, `uncovered: none`, the derived `needs pre-written context.md` flag, the
`.txt` agreeing with the roadmap, the size thresholds, and global name uniqueness against every other
roadmap and every `.specs/features/` directory. A failure is a question, not a verdict: read the
detail before changing anything, and where a check reports `·` nothing was judged there — the detail
says why.

What it cannot check is whether a question is *phrased well enough to answer*, whether a slice is
genuinely vertical, whether the coverage table's dispositions are honest, and whether a ledger row
quietly assumes the answer to a question still tagged `status: open` (Step 7a) — that last one has no
structural signature to match on, only a semantic one, so no check is coming for it. Those stay a
read. If
the script is not on disk — an install predating it — do the whole list by hand and say so.


- No feature's "depends on" points to a feature listed after it in the same file.
- No name is used by two `### <feature-name>` entries in this roadmap, or listed twice in its
  `.txt`, and no feature name collides with one in any other `docs/ROADMAP-*.md`
  **or `docs/ROADMAP.md`**, or with any existing `.specs/features/*` directory name. On collision
  with an existing directory, stop and ask whether it is that same feature — do not rename
  around it.
- No feature's task estimate exceeds eight; over budget means Step 3's split was not applied.
- Every open question is phrased as a question with enough context to answer it, and the per-feature
  fields and the `## Open Questions` roll-up agree **in both directions**: every field entry has a
  roll-up entry with the same `status:` tag, and every roll-up entry either names a feature whose
  field carries it or is tagged `cross-cutting`. A question living in only one of the two is the
  exact failure this check exists for — the seed reads only the roll-up, the specifying agent reads
  only the field, so whichever half is missing is invisible to one of them.
- The coverage table accounts for 100% of the enumerated scope-units, each exactly once, and closes
  with `uncovered: none`.
- Every theme in the confirmed downstream skill's rubric (Step 7a — nine for `tlc-spec-driven` v3.x)
  has exactly one row in `## Cross-Cutting Decisions`, in one of its four states, plus any
  `project-specific` rows the sweep added (see Step 7a). No rubric theme absent,
  no theme with two rows.
- Every `not decided` row (a `deferred to feature` row is exempt) names an entry that exists in
  `## Open Questions` tagged `cross-cutting`, naming that same rubric theme, with an `affects:` line;
  and every `cross-cutting` question tagged `status: answered` has a decided row. A theme in only one
  of the two is either an answer that never reached the build, or a rule with no record of who
  decided it.
- Every feature whose objective is getting an open question answered carries Step 3's exact
  `discharge:` line, and no other feature carries it.
- Every feature's `needs pre-written context.md` reads `yes` exactly when an implicit dimension is
  present or one of its open questions reads `status: open`, and `no` otherwise. The field is
  derived (Step 6), so it is checkable — and the seed's Blocker gate reads the question, not this
  field, precisely so a wrong `no` cannot switch the gate off.
- Every `## Expected Gray Areas` line states where the answer already lives — the code, the config,
  or an existing convention. A line whose stated reason is `feature-local` or `cheap to reverse` is
  misfiled: those are Step 7's routing tests, and a user-only decision that fails them belongs in its
  feature's `open questions` field, not in the block nothing sweeps.
- Nothing appears in both `## Expected Gray Areas` and `## Open Questions` (or any feature's own
  `open questions` field). That pair is the one that must be disjoint — the loop gate sweeps one and
  deliberately skips the other.
- **Warn at roughly 2,000 tokens; act at roughly 3,000.** The threshold is arithmetic, not a feeling:
  the file carries roughly 900 tokens of fixed overhead (title, the section headings, the
  cross-cutting ledger, the coverage table's header) plus roughly 230 per feature — its ten-field
  entry (Step 6), its row in the coverage table, its lines in `## Expected Gray Areas`, and its
  matching entry in the roll-up under `## Open Questions`. That puts 3,000 tokens at about 9
  features and 2,000 at about 5 — measured against real roadmaps, not derived from the field list.
  The feature's line in the `.txt` is not in that sum: the limit measures the roadmap, and that line
  lives in another file. So at roughly 2,000 tokens say so and name **how many features are left**
  before a split is needed, instead of only reacting once the limit is crossed.
  **On a first decomposition, do that arithmetic on Step 1's inventory before writing anything.** The
  file goes from empty to final size in a single Write, so neither mark is ever crossed while
  writing and the script can only report them afterwards — too late to change the mode cheaply. From
  about 9 features, re-raise Phase 0's single-vs-multi question **before** the Write: an oversized
  roadmap is evidence the mode choice was wrong, and asked at that moment the question does not
  collide with rule 9's exception, because no `docs/ROADMAP.md` exists yet to have fixed the mode.
  **Record the answer either way** — one plain line immediately under the H1, above `## Status`:
  `size re-raised (as of <YYYY-MM-DD>): single-section confirmed — <reason>`. Anywhere else it is
  lost or misread: inside `## Status` the next seed replaces the body and it is gone, inside
  `## Open Questions` it reads as an entry belonging to no feature.
  `scripts/check-roadmap.py` reads that line and, past the 3,000 mark, reports the size as
  acknowledged instead of warning, so a mode that was re-raised and confirmed stops being
  indistinguishable from one that was never asked. The 2,000 mark still reports: it is the one that
  a re-run can still act on cheaply.
  Splitting renames **files, never features**: a feature's name and its relative order freeze the
  moment `.specs/features/<name>/` exists (the freeze rules above), and a split only moves entries
  between roadmap files, so a project can be converted at any point without touching work already
  built — see `Converting a single-section project to multi-section` in
  [index-phase.md](index-phase.md). Never drop coverage rows to hit a size target. Check Step 7's
  two blocks against their own scaling first, because they do not share one.
  `## Cross-Cutting Decisions` is scaled by *theme* and capped at one row each, so a
  longer one is padded and gets cut back to the rubric. `## Expected Gray Areas` is scaled by what
  the sweep found and indexed *by feature*, so it grows with the roadmap and is **never** consolidated
  by theme — merging its lines destroys the one thing its reader needs from it. If one theme recurs
  there across three or more features, re-test it against Step 7's three tests: recurrence is
  evidence it reaches beyond one feature and belongs in 7a.
