# Phase 1 — Building/Refreshing the Index

## Contents

- [Only in multi-section mode](#only-in-multi-section-mode)
- [Goal](#goal)
- [Step 1 — Enumerate sections](#step-1--enumerate-sections)
- [Step 2 — Assign file, slug and prefix per section](#step-2--assign-file-slug-and-prefix-per-section)
- [Step 3 — Derive the dependency graph](#step-3--derive-the-dependency-graph)
- [Step 4 — Write one boundary contract per edge](#step-4--write-one-boundary-contract-per-edge)
- [Step 5 — List project-level decision candidates](#step-5--list-project-level-decision-candidates)
- [Output shape](#output-shape-of-docsroadmap-indexmd)
- [Converting a single-section project to multi-section](#converting-a-single-section-project-to-multi-section)
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

**A section does not have to come from the source document's structure.** When a project accumulates
work in **waves** — a batch of gaps from Phase 0c, a new epic, a round of fixes — each wave is a
legitimate section, even though no box in the source draws it. This is what keeps each roadmap at a
size the loop can carry per feature: the `/loop` prompt names **one** roadmap as the spec source for
every feature it builds (handoff-seed.md Step 10's scope rule), so a single file that absorbed three
waves is re-opened, whole, once per feature in all three.

## Step 2 — Assign file, slug and prefix per section

- **slug** — the section's kebab-case identifier, used in filenames. **The slug and the prefix are
  the same string**, so there is exactly one identifier per section and nothing has to be
  reconstructed later.
- Each slug is short, mnemonic, kebab-case (3-6 characters is a good target) and used by every
  feature in that section as `<slug>-<kebab-case>`.
- Slugs must not collide with each other, or with any already used by roadmaps in the project —
  check existing `docs/ROADMAP-*.md` **and `docs/ROADMAP.md`** before assigning. **The check covers
  the prefixes already in use on disk, not just the roadmap files:** list `.specs/features/*` and
  read the prefix off each directory name. A slug *is* a feature-name prefix, so one that matches a
  prefix carried by features **belonging to another section** collides in the namespace rule 6
  actually protects, whatever the roadmap filenames say — and those names are frozen, so nothing can
  be renamed around it. **A section's own prefix is never a collision with itself.** That distinction
  is load-bearing: the conversion below *requires* a section to take the prefix its own built
  features already carry, so a check that ignored ownership would reject the only legal answer.
- Filenames are exact and case-sensitive: `docs/ROADMAP-<slug>.md` (uppercase ROADMAP) and
  `docs/roadmap-<slug>.txt` (lowercase).
- **For a wave-shaped section**, prefer a thematic slug when the wave has a theme (`auth`, `bill`);
  fall back to a wave number (`w3`) only when it genuinely has none. The slug is permanent and shows
  up in every feature name in that section, and those names freeze once a `.specs/features/<name>/`
  directory exists (decompose-phase.md, "When to re-run, and what is frozen") — so a thematic slug
  ages better than a counter, which says only when the work arrived.

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

**A wave-shaped section's edge is temporal, and no diagram ever drew it.** Wave N+1 was decomposed
later, against a codebase wave N had already changed — so **source (1)** is empty by construction,
not by oversight: there is no arrow and no "depends on" field waiting to be found, and do **not**
stall the run hunting for a drawn edge that cannot exist.

**Source (2) is not empty, and it is the one to check first.** The claim above is about diagrams
only. A wave's scope document is prose, and prose about a later wave routinely names the earlier one
— *"builds on the auth work"*, *"extends the billing flow"* — which is exactly an explicit
cross-reference inside a section naming another section. Read for it before asking: a citation the
user already wrote is stronger evidence than an answer given from memory, and it costs no question.
Only when (2) and (3) are genuinely silent does the edge resolve from (4), usually in one question.
Record that citation like any other edge.

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

**Partially built producer — the parenthetical above does not hold.** A section converted out of
single-section mode (see below) is a producer whose surface is half **already shipped** and half
still only planned, and *"names provisional until that section is decomposed"* is **false for the
shipped half**: those names are on disk, and they are not going to move. For every feature in that
producer with a verified PASS, read what actually shipped — its real modules, tables and endpoints —
and write **those** names into **Producer exposes**, marked as built. Keep `provisional` for the part
that is still only an objective in the roadmap, and say which half each name came from. Describing
shipped code from the roadmap's objectives writes a plan where a fact was available, and the consumer
gets built against it.

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
- If the project has no such mechanism yet, keep the list here, under **Project-level decision
  candidates** in the output shape below.

**These candidates feed Phase 2's Step 7a.** A candidate that passes that step's three tests stops
being a candidate and becomes a row in `## Cross-Cutting Decisions`, in this same file — a decision if
the user answers it, a `not decided` row plus a `cross-cutting` question in `## Open Questions` if
they do not. Listing one here is not deciding it — this phase still never answers anything.

## Output shape of `docs/ROADMAP-INDEX.md`

1. H1 title.
2. `## Status` — the backlog position block, written and refreshed by the Handoff seed. Leave the
   heading in place even before the first seed.
3. `## Cross-Cutting Decisions` — the project-wide ledger from Phase 2's Step 7a. **This phase does
   not fill it**; it leaves the heading in place, because in multi-section mode this is the block's
   only home and each section's Phase 2 extends it in turn. Exactly one exists per project, like
   `## Status`. **One exception, and it is movement rather than authorship:** in a conversion (below)
   this phase carries an **already-populated** ledger into this file from the roadmap that used to
   hold it, rewriting the paths inside it on the way. It still answers nothing, adds no row, and
   changes no row's state.
4. Table of roadmaps: section → roadmap file → build-order file → slug/prefix → depends-on, plus
   excluded sections and why.
5. `## Ordering` — DAG + topological list, each edge citing its resolving source. Keep that exact
   heading; the seed locates the section by name (handoff-seed.md Steps 3 and 4). **The ordered list
   carries buildable sections only** — it is build order, and an excluded section has none. An
   excluded section appears in the DAG where a boundary contract cites it, marked
   `(excluded — pure foundation)` or `(excluded — pure decision log)`, and never in the ordered
   list.
6. Boundary contracts, one subsection per edge.
7. Project-level decision candidates, if any.

Cite these sections by **name**, never by position — inserting one renumbers every reference to the
ones below it, silently, in another file.

## Converting a single-section project to multi-section

**When this applies.** The project is single-section today — it has a `docs/ROADMAP.md` — a new wave
of scope has arrived, and the user chose to give that wave **its own roadmap** instead of extending
the existing one (scope-phase.md, "New scope arriving at a project that already has a roadmap").
Nothing else triggers a conversion: a single-section project that is merely large stays
single-section until the user asks otherwise.

**The conversion is a script, and it is the only sanctioned way to perform it.**

```
python3 <skill-dir>/scripts/convert-to-multi.py --root <project-root> --dry-run
python3 <skill-dir>/scripts/convert-to-multi.py --root <project-root>
```

`<skill-dir>` is the directory holding this skill's own `SKILL.md` — the one holding `references/`
and `scripts/`, resolved from disk the same way Step 5 of handoff-seed.md resolves the version.

**If that file is not on disk, the conversion does not happen.** Say the install predates it and
point at the README's `## Install` section: a plugin install updates with `/plugin update`, and a
plain-skill one by re-running `install.sh --force` (`install.ps1 -Force` on Windows). **Never
perform these renames by hand instead.** That is not
caution for its own sake: this procedure was written as prose first, and three rounds of review found
paths that silently destroyed `## Cross-Cutting Decisions` — a rollback that restored nothing, a
rollback that recreated `docs/ROADMAP.md` and then overwrote it, and a prefix rule that split on the
first hyphen and so handed `auth-core-*` features the slug `auth`, permanently. A written procedure
cannot be executed against a test repository; a script can, and this one is.

### What the script does, and what it refuses

It renames `docs/ROADMAP.md` to `docs/ROADMAP-<slug>.md` and `docs/roadmap.txt` to
`docs/roadmap-<slug>.txt`, writes a **minimal** `docs/ROADMAP-INDEX.md` carrying the `## Status` and
`## Cross-Cutting Decisions` blocks with every path inside them rewritten, and removes both blocks
from the renamed roadmap. Exactly one of each block exists per project, and the script **verifies
that as a post-condition** before it reports success — each block must appear exactly once in the
index and not at all in the renamed roadmap, or the run fails and rolls itself back.

**The transient is a duplicate, never an absence.** The index is written before the roadmap is
rewritten, so between those two writes both files carry the blocks. That is deliberate: a duplicate
is on disk and reconcilable, while the inverse order would leave the ledger in nothing but the run's
own context, where an interruption destroys it. If a run is killed in that window, both copies exist
— `--rollback` reverses it.

`<slug>` is **derived, not chosen**: the longest leading hyphen-token run common to every name in
`docs/roadmap.txt`, backed off until it is not the whole of any one of them — `tt-list` beside
`tt-list-open-tasks` is a parent feature and its child, and the section they share is `tt`. Step 2 makes the slug and the feature-name prefix the same string, and those
names freeze once `.specs/features/<name>/` exists, so a slug that differs from the prefix is
irreparable. **The derivation is sometimes ambiguous, and then the script refuses rather than
guess:** `pay-invoice-create` and `pay-invoice-list` admit both `pay` and `pay-invoice`, and only the
project knows which Step 2 assigned. It lists the candidates and stops. Resolve it by listing
`.specs/features/*` — Step 2's own authority on prefixes in use — and by reading the roadmap's
`### ` entries; put it to the user, then re-run with `--slug <choice>`.

It aborts, touching nothing, when: `docs/` or `docs/ROADMAP.md` is missing; `docs/ROADMAP-INDEX.md`
already exists; a section roadmap sits there with no index (rule 9's interrupted-conversion
contradiction); a `.sdr-conversion-backup/` from an earlier run is still present; `docs/roadmap.txt`
is missing; either file is a symlink; a rename target already exists; the roadmap has an odd number
of ``` fences, or carries a moved-block heading twice or in a near-miss form (a trailing colon, a
different case) — either of which would leave the real block behind while a placeholder took its
place; `docs/roadmap.txt` names features the roadmap does not carry as `### ` entries; or the prefix
cannot be derived or is not valid kebab-case. **Every abort is a question for the user, not a
workaround.** Read the message out and let them decide.

It also reports whether work looks in flight, without acting on it — that decision is below.

Exit codes: `0` converted or dry run; `1` a pre-condition failed or a rollback refused, and nothing
was touched; `2` usage error; `3` the conversion failed part-way and rolled itself back.

### Rollback

`--rollback` reverses a conversion using the backup the run left at `.sdr-conversion-backup/`. It
removes the index **before** restoring `docs/ROADMAP.md`, because a restored roadmap beside a
surviving index is exactly what rule 9 stops on, and a rollback that halts the next run is not a
rollback. When the conversion used `git mv`, it also unstages the rename so the index matches `HEAD`
again; when it did not — the files were untracked or dirty — there is no git state to undo.

**It refuses when the index has been edited since.** "Afterwards" below sends you straight into
filling that index out, and that work is uncommitted and lives in exactly the files a rollback
removes. The script hashes what it wrote and stops if anything changed, naming the files.
`--rollback --force` proceeds and moves the changed versions to `.sdr-conversion-backup/discarded/`
rather than deleting them.

The backup — not git — is the safety net: git recovery would need the files tracked *and* clean,
which is exactly what a project is not right after Phase 0c wrote `docs/CODEBASE-SUMMARY.md`.
`git mv` is still used when it is safe, so history follows the rename, and a `git mv` that fails
aborts the run rather than falling back to a blind rename that would overwrite what git refused.

The run leaves the backup directory in place, and **its presence blocks the next conversion** — tell
the user it is there and that deleting it, once they are satisfied, is theirs to do.

### Work in flight — decide this before running the script

Apply handoff-seed.md Step 1's evidence test to `.specs/STATE.md` first. **The seed cannot repair its
own pointer while work is in flight:** Step 1 forbids writing `.specs/STATE.md` and skips Step 6, and
Step 6 is the only step that resolves `<ROADMAP-PATH>`, `<STATUS-PATH>` and `<BUILD-ORDER-TXT>`. So a
mid-build conversion refreshes the `## Status` block and nothing else — the Handoff goes on naming a
`docs/ROADMAP.md` that no longer exists.

If work is in flight, take one of these two exits and record which:

- **(a) Convert, let the user close that feature, then re-run this skill's seed.** Once it reaches a
  verified PASS, Step 1 stops firing, Step 6 runs, and all three placeholders resolve. **Nothing else
  repairs the pointer** — in particular the downstream skill does not: it overwrites `## Handoff`
  from its own session at the next `pause work` without ever learning about the rename. Exit (a) is a
  re-seed deferred, never a repair delegated.
- **(b) Convert anyway and declare the pointer dead** — in chat, and durably on the `**Handoff**`
  line of the `## Status` block (handoff-seed.md Step 5's work-in-flight state, in the conversion
  form that also names the pre-conversion path). The script already writes the
  conversion-in-progress form into the index it creates; leave it there until that seed runs.

### Afterwards

**Fill the index out through Steps 1-5**, with the existing scope as the first section and the new
wave as the second, and the edge between them resolved as Step 3's note on temporal edges prescribes.
Step 2 only has to assign the new wave's slug — the existing section's is already fixed. The script
wrote the converted section's row and a one-node `## Ordering`; extend both.

**Then say which section the build will actually attack next**, before the user assumes it is the new
one. The converted section keeps every feature it had not built yet, so seed Step 3 classifies it
`IN PROGRESS` (or `NOT STARTED`), and Step 4's precedence gives an `IN PROGRESS` section the win. The
new wave is `NOT YET DECOMPOSED` until a Phase 2 run covers it, and Step 4 can never pick a target
from that state — so either way the next seed points at the **old** section. Name it, name the
feature the build will start with, and say what has to happen before the new wave comes up.

**Then re-run the Handoff seed.** All three of Step 6's path placeholders changed. This does not
contradict `When to re-run` below: adding a section still never triggers the seed by itself — what
triggers it here is that an already-written pointer names a renamed file. And it repairs nothing
while work is in flight, per the two exits above.

### What does not change, and what does

**No feature name changes, and no relative order changes.** Names freeze on the existence of a
`.specs/features/<name>/` directory, not on the file that lists them
(decompose-phase.md, "When to re-run, and what is frozen"). A conversion renames **files**, never
**features** — every line of the old `.txt` carries over unchanged and in the same order.

**What an `affects:` line reaches does change**, and nothing re-derives it. A `cross-cutting` entry
whose `affects:` names a subset rather than `all` was asserted against a project that had exactly one
section (decompose-phase.md Step 7a), so it excludes the new wave *by construction*. The seed reads
that line as written and never re-derives it. **Do not widen it here.** The repair belongs to the new
section's own Step 7a, which re-asks a `not decided` theme that section touches and appends that
section's features to the same entry's `affects:` line. Say it is pending, and leave the line alone.

**And warn about what this skill does not control.** Several things outside `docs/` carry the
pre-conversion paths. This skill edits none of them; it names them:

- **`CLAUDE.md`**, if the user pasted the optional bridge lines into it (handoff-seed.md Step 10).
  Give them the new lines — but **never edit their `CLAUDE.md` yourself**.
- **Anything under `.specs/` that cites `docs/ROADMAP.md`** — an `AD-NNN` entry in `.specs/STATE.md`,
  or the provenance lines in the `spec.md` of features already written, which took that path from an
  earlier seed's **Next step** field. This skill writes only the `## Handoff` block (SKILL.md rule
  11), so none of that is its to correct.
- **Any `/loop` prompt the user already has pasted somewhere.** Step 10 resolves all three paths into
  that text when it is emitted, so every copy taken before this conversion names three paths that are
  gone. Tell them to take a fresh prompt from the next seed.

## When to re-run

Re-run only when the source scope changes (a new section appears, an edge changes) or a section is
missing from an existing index. **Never wholesale-regenerate an index that already covers the current
scope** — extend it: add the new section's row, edges and contracts, and preserve everything already
resolved.

Adding a section here does **not** trigger the Handoff seed. A brand-new section has no
`docs/roadmap-<slug>.txt` yet, so it is `NOT YET DECOMPOSED` — a state the seed can never pick a
target from. Just report the next action: *"decompose section `<slug>`"*, and leave `.specs/STATE.md`
alone. The seed runs when Phase 2 closes a roadmap — see [handoff-seed.md](handoff-seed.md).
