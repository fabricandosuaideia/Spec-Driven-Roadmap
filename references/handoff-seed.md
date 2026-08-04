# Handoff Seed — One-Time, Not a Loop

## Goal

After a roadmap closes, write `.specs/STATE.md`'s `## Handoff` section **exactly once** so the
downstream spec-driven skill's own "resume work" already knows: every roadmap that exists, which ones
are done, which one is in progress and its remaining build order, and the exact next feature to open.
This is the entire extent of this skill's involvement in construction — no waiting for PASS, no
advancing to the next feature automatically, no re-invoking itself. Once this step reports, this
skill's job is done: every subsequent "specify feature", "resume work", pause, and verify belongs
entirely to the downstream skill's own normal flow, driven directly by the user or the general agent —
never routed back through this skill.

**This is not Phase 3 of a build loop.** There is no persistent phase here that re-triggers on every
"resume work", recomputes position on a schedule, or drives feature N+1 after feature N passes. It
runs once per trigger below, writes one section of one file, and stops. What makes the loop that
follows "simples e direto" isn't this skill watching over it — it's that the one write below already
carries everything the downstream skill needs to know before it even asks.

**Format precedent.** `.specs/STATE.md`'s `## Handoff` is free-form prose between its header and the
next `##`/EOF — the downstream skill reads it as a narrative snapshot, not a rigidly-parsed template.
The shape below (every roadmap listed with a DONE/IN-PROGRESS count, a "Remaining" build-order list
for the one in flight, and per-feature detail deliberately left out and pointed at
`.specs/features/<name>/validation.md` instead, to keep this section from growing unbounded) is what
this step writes up front, in one pass, rather than something that has to accrete one session at a
time by hand.

## When this runs

- Right after Phase 2 closes a roadmap (its coverage table reads "uncovered: none") — single-section
  or multi-section, either way.
- Right after Phase 1 extends an existing index with a brand-new section.

Never run it speculatively "just to check" — it's a write step, not a status query. If the user just
wants to know what the roadmap says is next without touching `STATE.md`, answer that by reading
`docs/roadmap*.txt` / `docs/ROADMAP-INDEX.md` and the relevant `validation.md` files directly instead
of going through this procedure.

## Step 1 — Check whether it's safe to write

Read `.specs/STATE.md` if it exists (the exact section format is the downstream skill's own — confirm
it at Phase 0 if the project uses something other than tlc-spec-driven's `## Decisions` / `## Handoff`
shape).

- **`## Handoff` names a feature with a non-empty "Next step" / "In-progress"** (real work is
  mid-flight) → **stop.** Do not touch `STATE.md` at all. Report to the user that a feature is
  already in flight and this roadmap update doesn't change the current position — the downstream
  skill's own resume will keep picking that feature up exactly as it already does, with no help
  needed from this skill.
- **`## Handoff` is empty, says "none", or the file doesn't exist yet** → safe to seed. Continue.

Never overwrite a non-empty Handoff to "fix" it into pointing at the roadmap — a real in-flight
feature always wins over a freshly-generated roadmap's opinion of what should be next.

## Step 2 — Build the full roadmap status list

Not just the next feature — every roadmap that exists gets one line, so the downstream skill (and
whoever reads `STATE.md`) sees the whole shape of the backlog, not a single disconnected pointer:

- **Single-section mode:** one line for `docs/roadmap.txt`: how many of its features already have a
  PASS `validation.md`, out of the total.
- **Multi-section mode:** walk `docs/ROADMAP-INDEX.md`'s section order top to bottom. For each section
  that has a `docs/roadmap-<slug>.txt`, count PASS features out of its total and classify:
  - **all PASS** → `DONE (X/X, all verified PASS)`.
  - **some PASS, not all** → `IN PROGRESS (N/M features done, verified PASS)` — this is also the
    section the target feature (Step 3) comes from.
  - **none PASS yet, file exists** → `NOT STARTED (0/M)`.
  - **no `docs/roadmap-<slug>.txt` yet** (Phase 2 hasn't decomposed it) → `NOT YET DECOMPOSED` — note
    what it depends on per the index, so it's clear why it's waiting.

There is at most one section in the `IN PROGRESS` or first-`NOT STARTED` state carrying an actual
target feature — everything after it in the index order is necessarily untouched yet.

## Step 3 — Find the target feature and its remaining order

- **Single-section mode:** walk `docs/roadmap.txt` top to bottom. The first name without a PASS
  `.specs/features/<name>/validation.md` is the target. The remaining build order is every name from
  the target to the end of the file, in order.
- **Multi-section mode:** within the section identified in Step 2 as `IN PROGRESS` or the first
  `NOT STARTED`, walk its `docs/roadmap-<slug>.txt` top to bottom the same way. The remaining build
  order is every name from the target to the end of *that section's* file — sections after it in the
  index are summarized by Step 2's status line only, not expanded here (their own turn to be expanded
  comes when the loop actually reaches them and this step runs again).

If every feature across every existing roadmap is already PASS (a refresh added no new buildable
work), there's nothing to seed — say so and stop. Don't write a Handoff pointing at nothing, and don't
invent a "next" feature that doesn't exist yet.

## Step 4 — Write the Handoff (section-scoped — never touch Decisions)

Following the downstream skill's own section-scoped write rule (locate the `## Handoff` header,
replace only the body between it and the next `##`/EOF; create both headers with an empty
`## Decisions` if the file doesn't exist yet), write:

```markdown
## Handoff

- **Roadmaps**:
  - `docs/ROADMAP-<slugA>.md` — DONE (X/X, all verified PASS)
  - `docs/ROADMAP-<slugB>.md` — IN PROGRESS (N/M features done, verified PASS)
    - **Remaining** (build order): `<feature-n+1>` → `<feature-n+2>` → … → `<feature-m>` (closes the roadmap)
  - `docs/ROADMAP-<slugC>.md` — NOT STARTED (0/K) — next after `<slugB>` per `docs/ROADMAP-INDEX.md`
  - `docs/ROADMAP-<slugD>.md` — NOT YET DECOMPOSED (depends on `<slugC>`)
- **Feature**: `<target feature name>`
- **Phase / Task**: not started
- **Completed**: none
- **In-progress**: none
- **Next step**: <the exact fresh-start trigger phrase confirmed at Phase 0, e.g. "specify feature `<target feature name>`">
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: <current branch, if known — omit the line if not>
```

Single-section mode: the **Roadmaps** list collapses to one line (`docs/ROADMAP.md — N/M features
done`) with its own **Remaining** sub-list — no DONE/NOT-STARTED siblings to enumerate.

Keep this compact the same way the real precedent does: counts and names, never a copy of each
feature's objective/tasks — that detail already lives in the roadmap file and, once built, in
`.specs/features/<name>/validation.md`. A Handoff that pastes full feature descriptions defeats its
own purpose (the downstream skill's own convention targets roughly 500 tokens per snapshot).

If the target feature has "needs pre-written context.md: yes" **and** a flagged open question
attached (from Phase 2, or from a boundary contract's marked-open item it consumes): put the exact
question in **Blockers** instead of "none", and set **Next step** to "answer the flagged question
before specifying" instead of the fresh-start trigger. Never seed a fresh-start pointer past an
unanswered question — that would hand the downstream skill a feature it can't actually start cleanly.

## Step 5 — Report and stop

Tell the user, plainly:

- the full roadmap status list from Step 2 (one line each),
- which feature was seeded as next, with its remaining build order (or that nothing was seeded, and
  why — already in flight / nothing left to seed / blocked on a question),
- that construction from here on is the downstream spec-driven skill's own job, through its own
  triggers, driven by the user or the general agent directly.

Then stop. Do not wait, do not poll `validation.md`, do not check back in. Moving from this feature to
the next — including from the last feature of one section to the first of the next, in multi-section
mode — is a decision the user (or the general agent, reading the roadmap files directly when asked)
makes when ready. Nothing in this skill schedules or drives that; if asked to seed again later (or if
the downstream skill's own pause naturally reaches the end of the section and its Handoff empties
out), this same procedure just re-runs from Step 1, and Step 1's safety check is what keeps it from
ever clobbering real progress.

## Why this makes the downstream loop simple

Once this seed exists, "resume work" on the downstream skill reads a Handoff that already answers
"what's the whole backlog, what's done, what's next, and why" in one place — the same shape this
project's own `.specs/STATE.md` grew into by hand, one session at a time. The two skills stay
decoupled (this one never authors spec/design/tasks/code, never loops), but the handoff between them
carries full context instead of a bare pointer, which is what keeps every subsequent "specify feature"
/ "resume work" call short and unambiguous instead of requiring someone to go re-read `docs/ROADMAP-
INDEX.md` from scratch each time.
