# Phase 1 — Building/Refreshing the Index

## Only in multi-section mode

Phase 0 must already have confirmed the project is using multiple section roadmaps, not the single
unified roadmap. If Phase 0 resolved to single-section mode, this entire phase is skipped — there is
no index, no per-section prefixes, and no cross-section boundary contracts to derive, because the
whole source is decomposed as one list in Phase 2 directly. Do not run this phase "just in case"; a
`docs/ROADMAP-INDEX.md` that exists alongside a single-section project contradicts the very choice
Phase 0 recorded.

## Goal

Produce `docs/ROADMAP-INDEX.md`: the one-level-above map of how many roadmaps exist, the order
they're written/executed in, and what each may assume about the ones before it. This phase does not
decompose any section into features — that is Phase 2, run once per `docs/ROADMAP-<slug>.md`, and
usually run lazily (see Phase 2's own doc) rather than all at once right after Phase 1.

## Step 1 — Enumerate sections

List every section/block the source of truth divides the system into (visual sections in a diagram,
chapters/epics in a PRD, top-level components in an architecture doc's inventory table, etc.). For
each, classify:

- **Buildable** — turns into a `ROADMAP-<slug>.md` with real feature work.
- **Pure foundation** — already built/inherited, nothing to plan (an "existing platform" or
  "already shipped infra" block). Exclude from roadmap generation, but keep it as reference —
  features in buildable sections will consume it and cite it in their boundary contracts.
- **Pure decision log** — a list of decisions/open-points/gaps with nothing to build directly (an
  appendix-style block of numbered decisions or open questions). Exclude from roadmap generation;
  route its content to whatever the project's decision-log mechanism is (an `AD-NNN` list, a
  `STATE.md`), or list it under Step 5 below if the project has no such mechanism yet.

Ask the user when a section is ambiguous between these categories — don't guess a section into
"pure foundation" just because it looks large or partially built already; a section can look mature
and still have real buildable work left in it.

## Step 2 — Assign file + prefix per buildable section

- One `docs/ROADMAP-<slug>.md` per buildable section.
- Each gets a short, mnemonic, kebab-case prefix (3–6 characters is a good target) used by every
  feature in that section: `<prefix>-<kebab-case>`.
- Prefixes must not collide with each other, and must not collide with prefixes already used by
  roadmaps elsewhere in the project — check existing `docs/ROADMAP-*.md` files before assigning.
- Record the mapping as a table: section → file → prefix → depends-on (filled in Step 3).

## Step 3 — Derive the dependency graph between sections

This is the part most likely to get invented if rushed. Resolve every edge in this strict order,
and record which source resolved it — that citation is what lets Phase 2, the Handoff seed, and
whoever builds from this roadmap later trust the order without re-deriving it:

1. **Explicit inter-section edges** in the source itself — an arrow/edge whose two ends fall in
   different sections; an explicit "depends on" field on a PRD epic.
2. **Explicit prose cross-references** inside a section's own content that name another section by
   name (a node's label says "→ block F"; a requirement says "after the X module exists").
3. **An existing build-order document** already in the project (a phased-rollout table, an ordering
   already written into a `CLAUDE.md`/README/ADR).
4. **Ask the user.** Never invent a dependency edge that isn't traceable to one of the above — a
   wrong edge here silently corrupts every downstream roadmap's ordering, and by extension whatever
   order the user or the downstream spec-driven skill actually builds sections in.

State plainly if the source's own edges never cross section boundaries (common with auto-extracted
diagrams, where drawn arrows rarely leave the section's own bounding box) — when that's the case,
say so up front, and be explicit that the cross-section order below comes entirely from (2)/(3)/(4),
not from any drawn edge.

Render the result as a DAG (a small textual diagram is enough) and as an ordered list, one line
each, top-to-bottom = build order. If two or more sections share the same set of predecessors and
have no edge between themselves, say so explicitly — they can be decomposed/built in either order
or in parallel, and forcing a fake tie-break order would misrepresent the graph.

## Step 4 — Write one boundary contract per inter-section edge

For every edge in the dependency graph, write a short contract block:

- **Producer exposes:** the concrete tables/modules/endpoints/functions the upstream section hands
  over (names are provisional — the actual `ROADMAP-<slug>.md` for that section confirms them when
  it's decomposed).
- **Consumer assumes:** exactly what the downstream section may rely on, and nothing beyond that.
- **Marked-open:** anything the source leaves ambiguous about this boundary — write it as a
  question, never as a decision. This is what lets Phase 2 skip re-deriving cross-section behavior
  each time — it just cites the contract instead of re-reading the sibling section, and it's also
  what the Handoff seed step surfaces to the user immediately if a feature depending on that
  contract turns out to need the open question answered before it can be specified.

When a unit of scope structurally sits inside one section but really needs to be built by another
(a table drawn inside section C that section A must actually create first because A depends on it),
make the call here and record it in the contract — see Phase 2's Step 3 for the full worked case.

## Step 5 — List project-level decisions found along the way (optional Part 4)

While reading the source, some things surface that are neither a boundary contract nor buildable
scope — genuine standing project decisions (a naming convention fixed here, an explicit call on
which section owns a shared module, an unresolved point that gates opening a specific roadmap).
List them for the record:

- **Step 3's derived section order is always one of these candidates** — propose it explicitly, even
  when every edge came cleanly from the source. The order isn't just a detail of `ROADMAP-INDEX.md`;
  it's a project-level constraint the downstream skill's Design phase should be able to re-confirm
  against later, worded as a decision record would be: the order itself, which source resolved each
  edge (Step 3), and the trade-off if any section's opening is gated on an open question. (If the
  downstream skill uses `tlc-spec-driven`'s `AD-NNN` convention, this is exactly the shape a
  cross-roadmap build-order decision takes there — e.g. "AD-003: sections build in order X → Y → Z,
  per `docs/ROADMAP-INDEX.md`'s dependency graph, because Y's `<table>` depends on X's `<module>`.")
- For any other candidate (naming convention, shared-module ownership call, a gating open question):
  if the project already has a decision log (an `AD-NNN` list in `.specs/STATE.md`, a
  `DECISIONS.md`), note these as **candidates** for it — do not write into that file directly
  unless the user explicitly asks to record them now. The downstream spec-driven skill's own Design
  phase (or an explicit "record decision" request) is what actually appends an `AD-NNN` entry;
  this skill only surfaces the candidate and cites where it came from.
- If the project has no such mechanism yet, keep the list in this same index document, as Part 4,
  until one exists.

## Output shape of `docs/ROADMAP-INDEX.md`

1. Table of roadmaps: section → file → prefix → depends-on. Note excluded sections
   (foundation/decision-log) and why.
2. Ordering: DAG + topological list, with each edge's resolving source cited (per Step 3).
3. Boundary contracts, one subsection per inter-section edge (Step 4).
4. Project-level decision candidates (Step 5), if any surfaced.

## When to re-run

Re-run Phase 1 only when the source scope changes (a new section appears, an edge changes) or a
section is missing from an existing index — never wholesale-regenerate an index that already covers
the current scope just because a new roadmap is about to be written or the user is ready to start a
new section. Extend it instead: add the new section's row, its edges, its contracts, and preserve
everything already resolved for existing sections. Adding a new section this way is also one of the
two triggers for the Handoff seed (see
[handoff-seed.md](handoff-seed.md)) — run it once after extending the index, so
`.specs/STATE.md` reflects the newly available section if nothing else is currently in flight.
