# Phase 1 — Building/Refreshing the Index

## Contents

- [Only in multi-section mode](#only-in-multi-section-mode)
- [Step 1 — Enumerate sections](#step-1--enumerate-sections)
- [Step 2 — Assign file, slug and prefix per section](#step-2--assign-file-slug-and-prefix-per-section)
- [Step 3 — Derive the dependency graph](#step-3--derive-the-dependency-graph)
- [Step 4 — Write one boundary contract per edge](#step-4--write-one-boundary-contract-per-edge)
- [Step 5 — List project-level decision candidates](#step-5--list-project-level-decision-candidates)
- [Output shape](#output-shape-of-docsroadmap-indexmd)
- [When to re-run](#when-to-re-run)

## Only in multi-section mode

Phase 0 must already have confirmed multiple section roadmaps. In single-section mode this phase is
skipped entirely — there is no index, no per-section prefix, and no cross-section boundary contract,
because the whole source is decomposed as one list in Phase 2. Do not run this "just in case": a
`docs/ROADMAP-INDEX.md` alongside a single-section project contradicts the choice Phase 0 recorded.

## Goal

Produce `docs/ROADMAP-INDEX.md`: the map of how many roadmaps exist, the order they execute in, and
what each may assume about the ones before it. This phase decomposes nothing — that is Phase 2, run
once per roadmap and usually lazily.

## Step 1 — Enumerate sections

List every section the source divides the system into (visual sections, chapters/epics, top-level
components). Classify each:

- **Buildable** — becomes a `ROADMAP-<slug>.md` with real feature work.
- **Pure foundation** — already built or inherited, nothing to plan. Excluded from generation, but
  kept as reference: buildable sections consume it and cite it in boundary contracts.
- **Pure decision log** — decisions, open points, gaps with nothing directly buildable. Excluded;
  route its content to the project's decision-log mechanism, or list it under Step 5.

Ask when a section is ambiguous between these. Never classify a section as "pure foundation" just
because it looks large or partly built — a section can look mature and still hold real work.

## Step 2 — Assign file, slug and prefix per section

- **slug** — the section's kebab-case identifier, used in filenames. **The slug and the prefix are
  the same string**, so there is exactly one identifier per section and nothing has to be
  reconstructed later.
- Each slug is short, mnemonic, kebab-case (3-6 characters is a good target) and used by every
  feature in that section as `<slug>-<kebab-case>`.
- Slugs must not collide with each other, or with any already used by roadmaps in the project —
  check existing `docs/ROADMAP-*.md` **and `docs/ROADMAP.md`** before assigning.
- Filenames are exact and case-sensitive: `docs/ROADMAP-<slug>.md` (uppercase ROADMAP) and
  `docs/roadmap-<slug>.txt` (lowercase).

Record the mapping as a table, including the `.txt` path explicitly so the Handoff seed reads it
rather than guessing:

| Section | Roadmap file | Build-order file | Slug / prefix | Depends on |
|---|---|---|---|---|
| Payments ingestion | `docs/ROADMAP-pay.md` | `docs/roadmap-pay.txt` | `pay` | — |

Note excluded sections (foundation / decision-log) and why.

## Step 3 — Derive the dependency graph

This is the part most likely to get invented if rushed. Resolve every edge in this strict order, and
**record which source resolved it** — that citation is what lets Phase 2 and the seed trust the order
without re-deriving it:

1. **Explicit inter-section edges** in the source — an arrow whose ends fall in different sections;
   an explicit "depends on" field on an epic.
2. **Explicit prose cross-references** inside a section naming another section.
3. **An existing build-order document** already in the project (a phased-rollout table, an order
   written into a `CLAUDE.md`/README/ADR).
4. **Ask the user.** Never invent an edge that is not traceable to one of the above — a wrong edge
   silently corrupts every downstream roadmap's ordering.

State plainly if the source's own edges never cross section boundaries (common with auto-extracted
diagrams, where arrows rarely leave their bounding box). When that is the case, say so up front and
be explicit that the order comes from (2)/(3)/(4), not from any drawn edge.

Render the result as a small textual DAG and as an ordered list, top-to-bottom = build order. If two
sections share predecessors and have no edge between them, say so — they can be built in either
order or in parallel, and a fake tie-break would misrepresent the graph.

## Step 4 — Write one boundary contract per edge

For every edge:

- **Producer exposes:** the concrete tables/modules/endpoints the upstream section hands over (names
  provisional until that section is decomposed).
- **Consumer assumes:** exactly what the downstream section may rely on, and nothing more.
- **Marked-open:** anything the source leaves ambiguous about this boundary, written as a question,
  never as a decision. Phase 2 cites these instead of re-reading the sibling, and the seed surfaces
  them as blockers when a feature depends on one.

When a unit structurally sits in one section but must be built by another, make the call here and
record it — see Phase 2's Step 4 for the worked case.

## Step 5 — List project-level decision candidates

While reading the source, some things surface that are neither boundary contracts nor buildable
scope — standing project decisions.

- **Step 3's derived section order is always a candidate.** Propose it explicitly even when every
  edge came cleanly from the source: the order is a project-level constraint the downstream skill's
  Design phase should be able to re-confirm later. Word it as a decision record would be: the order
  itself, which source resolved each edge, and the trade-off if any section is gated on an open
  question. (With `tlc-spec-driven`'s `AD-NNN` convention this reads as: *"sections build X → Y → Z
  per the index's dependency graph, because Y's `<table>` depends on X's `<module>`."*)
- For any other candidate (naming convention, shared-module ownership, a gating question): if the
  project has a decision log, note these as **candidates** for it — do not write into it directly
  unless the user explicitly asks. The downstream skill's own Design phase, or an explicit "record
  decision", is what appends the entry.
- If the project has no such mechanism yet, keep the list here as Part 4.

## Output shape of `docs/ROADMAP-INDEX.md`

1. `## Status` — the backlog position block, written and refreshed by the Handoff seed. Leave the
   heading in place even before the first seed.
2. Table of roadmaps: section → roadmap file → build-order file → slug/prefix → depends-on, plus
   excluded sections and why.
3. Ordering: DAG + topological list, each edge citing its resolving source.
4. Boundary contracts, one subsection per edge.
5. Project-level decision candidates, if any.

## When to re-run

Re-run only when the source scope changes (a new section appears, an edge changes) or a section is
missing from an existing index. **Never wholesale-regenerate an index that already covers the current
scope** — extend it: add the new section's row, edges and contracts, and preserve everything already
resolved.

Adding a section here does **not** trigger the Handoff seed. A brand-new section has no
`docs/roadmap-<slug>.txt` yet, so it is `NOT YET DECOMPOSED` — a state the seed can never pick a
target from. Just report the next action: *"decompose section `<slug>`"*, and leave `.specs/STATE.md`
alone. The seed runs when Phase 2 closes a roadmap — see [handoff-seed.md](handoff-seed.md).
