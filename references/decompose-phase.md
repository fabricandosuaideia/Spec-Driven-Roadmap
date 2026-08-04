# Phase 2 — Decomposing Into Features

## Contents

- [Mode differences and inputs](#mode-differences-and-inputs)
- [Step 1 — Enumerate the scope-units first](#step-1--enumerate-the-scope-units-first)
- [Step 2 — Derive the feature execution order](#step-2--derive-the-feature-execution-order)
- [Step 3 — Slice into features](#step-3--slice-into-features)
- [Step 4 — Shared ownership across sections](#step-4--shared-ownership-across-sections) (multi-section only)
- [Step 5 — Defer work that cannot be built yet](#step-5--defer-work-that-cannot-be-built-yet) (multi-section only)
- [Step 6 — Write each feature with all ten fields](#step-6--write-each-feature-with-all-ten-fields)
- [Step 7 — Close the roadmap](#step-7--close-the-roadmap)
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
  no boundary contracts. Assign one project-level prefix up front (confirm it does not collide) and
  every "external contract consumed" is "none".
  *Load:* the whole source and the conventions doc.

## Step 1 — Enumerate the scope-units first

**Build a compact inventory before decomposing anything:** one line per scope-unit — its ID and a
short label. Whatever the source's atomic unit is (a diagram node, a requirement ID, a table row, an
`M1`/`G1` bullet from Phase 0b/0c), it gets a line.

Decompose from that inventory, re-reading the full text only for the unit you are currently writing
a feature for. This is what keeps a large source tractable and what makes the coverage table
trustworthy — a unit that was never enumerated cannot be noticed as missing later.

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

Assign every scope-unit to exactly one feature. A feature typically groups several related units (a
table + the module that reads it + the rule that governs it) and never re-declares a unit already
claimed elsewhere.

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
  or when `.specs/features/<name>/context.md` exists. Say so in the feature's own entry.
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

Never build the same schema twice, and never let a unit vanish because each side assumed the other
claimed it.

## Step 5 — Defer work that cannot be built yet

*Multi-section mode only.*

A requirement may apply here but need a mechanism only a later section provides. Do not invert the
build order. Instead: leave it out of this feature list; add a note naming what is deferred, to which
roadmap, and why (citing the missing dependency); mark the unit `deferred` in the coverage table
(Step 7). When that later roadmap is decomposed, add the feature there with a cross-reference back.
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
- **task estimate** — a number, target ≤8.
- **implicit dimensions present** — any of: persistence/state, external calls, auth, payments,
  concurrency, state transitions; or "none". These are the dimensions that trigger the downstream
  skill's own Discuss step.
- **open questions** — one line per unresolved point, phrased as a question, citing the exact place
  in the source that leaves it open, each tagged `status: open` or `status: answered`; or "none".
  **This is where rule 1's refusal to guess actually lands** — without this field there is nowhere to
  put an ambiguity, and it gets silently resolved or dropped.
- **needs pre-written context.md** — yes if any dimension is present or any open question is
  `status: open`; no otherwise.

## Step 7 — Close the roadmap

- **Coverage table:** one row per scope-unit → its disposition. Four dispositions are valid:
  - `<feature-name>` — built by that feature in this roadmap.
  - `covered by reference to <roadmap>/<feature>` — owned by another section (Step 4).
  - `deferred to <roadmap> — blocked on <dependency>` — cannot be built yet (Step 5).
  - `pre-existing — already built, verified in codebase` — from Phase 0c's
    `## Capabilities Already Built`; not new scope.

  Close with `uncovered: none (N deferred, N pre-existing, listed above)`. A genuinely uncovered unit
  means Step 3 is not finished.
- **`## Open Questions` roll-up:** every feature's `status: open` questions in one list, each naming
  the feature that carries it. The Handoff seed reads this to decide whether to block. Omit the
  section only when there are genuinely none.
- **Execution-order block:** a fenced list, one feature name per line, respecting every "depends on".
  When the source declares increments, mark their boundaries with comment lines the seed ignores:
  `# --- end of increment 1: <what ships here> ---`.
- **Standalone `.txt`:** `docs/roadmap-<slug>.txt` (multi-section) or `docs/roadmap.txt` (single),
  the same list, one name per line, no status markers and no comments other than the increment lines
  above. This is what the Handoff seed walks; it never re-parses the markdown.

## When to re-run, and what is frozen

Re-running is normal — the source gains requirements as the project moves. **Never wholesale-
regenerate a roadmap that already covers the current scope; extend it.**

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

- No feature's "depends on" points to a feature listed after it in the same file.
- No feature name collides with one in any other `docs/ROADMAP-*.md` **or `docs/ROADMAP.md`**, or
  with any existing `.specs/features/*` directory name. On collision with an existing directory,
  stop and ask whether it is that same feature — do not rename around it.
- Every open question is phrased as a question with enough context to answer it, and appears in the
  `## Open Questions` roll-up.
- The coverage table accounts for 100% of the enumerated scope-units, each exactly once, and closes
  with `uncovered: none`.
- If the roadmap is growing past roughly 3,000 tokens, say so and re-raise Phase 0's single-vs-multi
  question — an oversized roadmap is evidence the mode choice was wrong. Never drop coverage rows to
  hit a size target.
