# Phase 2 — Decomposing Into Features

## Single-section mode vs. multi-section mode

Phase 0 already fixed which mode the project is in — this phase behaves differently depending on it:

- **Multi-section mode:** run per section, lazily, right before the user is ready to start building
  that section — not necessarily for every buildable section immediately after Phase 1. Decomposing a
  section that won't be built for weeks risks staleness (the source or an upstream boundary contract
  may shift before then); decomposing it just-in-time keeps every `ROADMAP-<slug>.md` close to what's
  actually about to be built. If the user explicitly wants the whole backlog visible upfront, that's a
  fine reason to run this for every section right away — just don't make it the default assumption.
- **Single-section mode:** run this once, directly against the whole source — there is no per-section
  laziness to have, since there's only one feature list for the entire scope. There is no
  `docs/ROADMAP-INDEX.md`, no per-section prefix table, and no boundary contracts; assign one
  project-level `<prefix>` up front (confirm it doesn't collide with any existing roadmap's prefix)
  and every "external contract consumed" field is simply "none" — there are no sibling sections to
  produce one.

## Inputs to load (and nothing else)

- **Multi-section mode:** `docs/ROADMAP-INDEX.md` (for this section's prefix, its dependencies, and
  the boundary contracts that apply to it, both as consumer and producer), the target section's own
  content from the source of truth (only this section, not siblings), and the project's conventions
  doc (`CLAUDE.md`/README/etc.), if any.
- **Single-section mode:** the whole source of truth, and the project's conventions doc, if any.
  There is no index to load.

Multi-section mode only: do not load sibling sections in full. If something looks like it needs a
sibling section's detail, that need should already be captured as a boundary contract in the index
(Phase 1, Step 4) — cite it, don't go re-read the sibling to re-derive it.

## Step 1 — Derive the feature execution order

- If the section's own content has internal structure (a sequence of steps, edges between its own
  units, an explicit pipeline), derive the order from that and show the derivation — a small
  dependency diagram is enough.
- If it doesn't, order features by natural build dependency: schema/foundational persistence first,
  shared/internal modules next, the things that consume them after, cross-cutting extras (export,
  admin tooling, toggles) last.
- A section's internal graph is sometimes just one long linear pipeline (each stage feeds the next
  and nothing branches) — when that's the case, say so; don't force an artificial fan-out just to
  make the graph look richer than it is.

## Step 2 — Slice into features (vertical, ≤8 tasks)

For every unit of scope in this section (whatever the source's atomic unit is — a diagram node, a
requirement ID, a table row; call it a "unit" below), assign it to exactly one feature. A feature
typically groups several related units (e.g. a table + the module that reads/writes it + the rule
that governs it) and never re-declares a unit already claimed by another feature.

Common slicing moves, roughly in order of how often they come up:

- **Shared foundation first.** When several downstream features all read/write the same schema or
  reuse the same interface, give that schema/interface its own feature ahead of them (a `-schema` or
  `-registry` style feature), even if no single edge in the source points to it first — persistence
  must exist before anything writes to it, regardless of how the source's edges are drawn.
- **One feature per swappable adapter.** When the section defines an abstract interface with
  multiple concrete implementations (multiple integration providers, multiple channel types), each
  concrete implementation is its own feature sitting behind the shared interface's foundation
  feature — they usually carry independent "confirm the technology" open questions and shouldn't be
  bundled together.
- **Correction/gap-only features are legitimate.** Not everything buildable has a matching unit in
  the source. A corrections doc, a later addendum, or a "we realized afterward we need X" note often
  produces a whole feature with zero scope-units to cite. Write it anyway, marked "no scope-unit —
  originated from `<the correction/addendum>`" — never force a fake citation, and never drop it
  silently just because it has no ID to point to.
- **Formalize a blocking open question as its own feature.** When the source has a genuine
  unresolved architectural question that gates several downstream features (which mechanism exposes
  an internal capability, whether a component is AI-driven or fully deterministic, which of two
  vendors to integrate), give it its own small feature whose first task is literally "get this
  answered by the user". Every feature that needs the answer depends on this feature — never on a
  guessed answer. The downstream spec-driven skill's own gray-area/Discuss step will stop and ask
  when it reaches this feature — and the Handoff seed (see
  [references/handoff-seed.md](handoff-seed.md)) refuses to point a fresh start at this feature while
  the question is unanswered, surfacing it instead.
- **Split at 8 tasks.** When honest task counting for a natural feature exceeds 8, split along the
  clearest internal seam (read-path vs. write-path; core happy-path vs. an add-on capability) and
  state the reason in both halves.

## Step 3 — Handle shared ownership across section boundaries (multi-section mode only)

Doesn't apply in single-section mode — there are no section boundaries to cross when the whole
source is one roadmap.

Sometimes the source's own structural placement of a unit conflicts with which section should
actually build it (a unit visually/structurally sits inside section C, but the real build order — or
an explicit note elsewhere in the source — means section A must create it first because C depends on
it). Resolve by:

1. Checking whether `docs/ROADMAP-INDEX.md` already made a call on this in its boundary contracts
   (Phase 1, Step 4) — if so, follow it.
2. If the index is silent, decide based on genuine build necessity (whichever section needs the unit
   to exist first, per the dependency graph, is the natural owner) and **record the decision in both
   roadmaps**: the owning roadmap's feature lists the unit as covered, with a short note on why it
   lives there despite where the source placed it; the consuming roadmap's coverage table marks the
   unit "covered by reference to `<owning-roadmap>`/`<feature>`, not re-declared here". Never build
   the same schema/module twice, and never let a unit vanish from every coverage table because each
   side assumed the other already claimed it.

## Step 4 — Defer work that structurally can't be built yet (multi-section mode only)

Doesn't apply in single-section mode — there is no downstream section to defer work to; everything
belongs in the one roadmap, ordered by Step 1's dependency derivation instead.

A correction or requirement may apply to this section but require a mechanism that only exists in a
section built *later* in the index's order (e.g. a reconciliation job that needs a queue/events
table owned by a downstream section). Don't invert the build order to satisfy it. Instead:

- Leave it out of the current roadmap's feature list.
- Add a short note in the current roadmap explaining what's deferred, to which future roadmap it
  belongs, and why (cite the missing dependency).
- When that later roadmap is actually decomposed, add the deferred feature there for real, with a
  cross-reference back to the note that originally deferred it — don't let a deferred item become a
  permanent, silent gap. This skill does not track this itself (there is no build loop keeping a
  to-do list); the note in the roadmap file is the only record until that later roadmap is decomposed.

## Step 5 — Write each feature with all nine fields

- **name** — `<prefix>-<kebab-case>`, unique across the whole project.
- **objective** — one sentence.
- **scope-units covered** — the source's own IDs/references (or "none — originated from `<X>`", per
  Step 2's correction/gap-only case).
- **depends on** — features from *this section only* (or the whole roadmap, in single-section mode);
  empty/"—" for the first feature(s).
- **external contract consumed** — an item from `docs/ROADMAP-INDEX.md`'s boundary contracts, or
  "none" (always "none" in single-section mode — there is no index to consume from).
- **size** — Small / Medium / Large / Complex, consistent within the roadmap. A feature landing on
  Complex is usually a signal it should have been split back in Step 2.
- **task estimate** — a number, target ≤8 (see Step 2's split rule).
- **implicit dimensions present** — any of: persistence/state, external calls, auth, payments,
  concurrency, state transitions. List "none" if genuinely none apply (a pure function with no I/O,
  for instance).
- **needs pre-written context.md** — yes if any dimension is present or any open question was
  flagged for this feature; no otherwise. The Handoff seed step reads this field directly to decide
  whether to surface a question instead of seeding a fresh-start pointer (see
  [references/handoff-seed.md](handoff-seed.md)).

## Step 6 — Close the roadmap

- **Coverage table:** one row per scope-unit → feature. End with an explicit "uncovered: none" line
  (or the actual list — which means Step 2 isn't finished yet).
- **Execution-order block:** a fenced list, one feature name per line, in the order features should
  be built (respecting every "depends on").
- **Standalone `.txt` file:** `docs/roadmap-<slug>.txt` (multi-section mode) or `docs/roadmap.txt`
  (single-section mode), the exact same list, one name per line — this is the file the Handoff seed
  step reads to find the first not-yet-built feature, and what anyone manually sequencing features
  should read too; it never re-parses the markdown.

## Sanity checks before calling a roadmap done

- No feature's "depends on" points to a feature listed after it in the same file.
- No feature name collides with one in any other `docs/ROADMAP-*.md` in the project.
- Every open question is phrased as a question with enough context to answer it — never resolved
  inline as if it were settled.
- The coverage table accounts for 100% of the section's scope-units, each exactly once.
