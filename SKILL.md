---
name: spec-driven-roadmap
description: Use when the user wants to turn a system's scope into a dependency-ordered features backlog for a spec-driven workflow (e.g. tlc-spec-driven) to build — whether that scope already exists (a flowchart, PRD, ADR set, or architecture/CLAUDE.md-style doc), needs to be created from scratch through an interview because the user has no document and isn't sure what to build yet, or needs to be derived from an existing codebase that has no scope doc. Triggers: "generate a roadmap", "decompose this architecture into features", "create a ROADMAP-INDEX", "split this system into buildable features", "help me plan a new project from scratch", "I don't know what to build yet", "map this codebase into a roadmap source", "plan product" — either as a single unified roadmap or split into multiple dependency-ordered section roadmaps (the user picks which, explicitly, before either is generated). Produces docs/PROJECT.md or docs/CODEBASE-SUMMARY.md when no source exists yet, docs/ROADMAP-INDEX.md + one docs/ROADMAP-<slug>.md/roadmap-<slug>.txt per section in multi-section mode, or a single docs/ROADMAP.md/roadmap.txt in single-section mode — then seeds `.specs/STATE.md`'s Handoff ONCE, pointing the downstream spec-driven skill at the first feature to build. Stack-agnostic, source-agnostic, adaptive to whichever spec-driven skill is installed — reusable across projects.
metadata:
  version: 3.0.0
---

# Spec-Driven Roadmap

Turn a system's scope into a dependency-ordered features backlog, ready for a spec-driven workflow
to build one feature at a time. This skill **plans once and hands off once** — it locates or creates
the scope (interviewing the user when nothing exists yet, or mapping an existing codebase when there's
no scope doc), indexes it (only if the user wants multiple section roadmaps), decomposes it into
vertical features, and seeds the downstream skill's own Handoff with the first feature to build. It
never drives construction itself.

```
┌───────────────────┐     ┌────────────────────┐     ┌───────────────────────┐     ┌──────────────────┐
│ PHASE 0:          │ ──▶ │ PHASE 1:           │ ──▶ │ PHASE 2:              │ ──▶ │ HANDOFF SEED:     │
│ SCOPE + ASK       │     │ INDEX              │     │ DECOMPOSE             │     │ one-time write to │
│                   │     │ (skipped entirely  │     │ (per section, or the  │     │ .specs/STATE.md   │
│ 0a source exists  │     │  in single-section │     │  whole source once    │     │ Handoff — points  │
│ 0b Interview Mode │     │  mode)             │     │  in single-section    │     │ at feature #1,    │
│    (no source,    │     │                    │     │  mode)                │     │ then this skill's │
│    no idea yet)   │     │                    │     │                       │     │ job is done       │
│ 0c Brownfield Mode│     │                    │     │                       │     │                   │
│    (no source,    │     │                    │     │                       │     │                   │
│    codebase does) │     │                    │     │                       │     │                   │
│ + target skill,   │     │                    │     │                       │     │                   │
│ single vs. multi  │     │                    │     │                       │     │                   │
└───────────────────┘     └────────────────────┘     └───────────────────────┘     └──────────────────┘
```

This skill **plans and hands off; it never specs, designs, implements, tests, or builds a feature,
and it never runs a build loop** — every one of those is always delegated to the target project's
spec-driven workflow (default assumption: **tlc-spec-driven**; confirm at Phase 0 if the project uses
a different one), invoked **directly by the user or the general agent** from the seed onward, through
that skill's own normal triggers ("specify feature `<name>`", "resume work", etc.). That holds even
when Phase 0 itself had to *produce* the scope (0b/0c below, not just 0a) — interviewing the user or
mapping a codebase is still scoping, not building. It also **never decides a genuine open question**
and **never decides single-section vs. multi-section on its own** — every ambiguity found while
indexing or decomposing becomes a flagged question in the output, and the section-shape decision is
asked explicitly in Phase 0, exactly like the source-of-truth document and the target spec-driven
skill are. Those refusals are what make this skill safe to reuse across projects without babysitting:
it either produces something traceable back to the source, asks, or stops — it never guesses, and it
never keeps running after the handoff.

## Non-negotiable rules (apply across every phase)

1. **Never decide a genuine ambiguity.** A missing technology choice, an undefined business rule, a
   source that just doesn't say — becomes a question with the exact reference to where it's
   unresolved. Never a guess, a default, or a "sensible pick" made silently.
2. **Vertical slices only.** A feature is route + service + persistence + test for one coherent
   capability. "The whole schema", "the whole API layer", "all the UI" is not a feature — slice by
   capability, never by architectural layer.
3. **≤8 tasks per feature.** Honest estimation over budget means split the feature and say why —
   never pad a large feature into one entry just to keep a list short.
4. **No forward dependencies.** A feature may only depend on a feature listed earlier in the same
   roadmap. A cross-section need is a boundary contract (Phase 1, Step 4), never a "depends on" —
   and doesn't exist at all in single-section mode (there are no sections to cross).
5. **Full coverage, exactly once.** Every unit of scope (node, requirement, epic — whatever the
   source's atomic unit is) maps to exactly one feature. Every roadmap ends with a coverage table
   and an explicit "uncovered" line that must read "none".
6. **Globally unique feature names.** `<prefix>-<kebab-case>`, unique across every roadmap in the
   project — check existing `docs/ROADMAP-*.md` / `docs/ROADMAP.md` before naming anything.
7. **Flag implicit-requirement dimensions.** Per feature, name which of `persistence/state`,
   `external calls`, `auth`, `payments`, `concurrency`, `state transitions` are present. Any
   dimension present, or any open question, sets "needs pre-written context.md" to yes.
8. **Ask, never assume, how the scope is shaped.** Single unified roadmap vs. multiple dependency-
   ordered section roadmaps is a real trade-off (one flat backlog is simpler for a small/linear
   scope; splitting by section pays off when sections have real boundaries and might be built by
   different sessions or people) — resolve it in Phase 0 by asking, the same way the source document
   and the target spec-driven skill are confirmed, never inferred from how big the source looks.
9. **Delegate, never author, never loop.** This skill never writes `spec.md`/`design.md`/`tasks.md`/
   application code itself, and never re-invokes itself to march through features one by one — the
   downstream skill's own trigger phrases (invoked by the user or the general agent) are what drive
   construction, from the very first feature onward. This also bounds Phase 0's own Interview and
   Brownfield modes: they produce `docs/PROJECT.md` / `docs/CODEBASE-SUMMARY.md` — this skill's own
   namespace — never the downstream skill's project-init or codebase-mapping output (e.g.
   `tlc-spec-driven`'s `.specs/project/PROJECT.md` or `.specs/codebase/*`). If the project already
   has those, Phase 0 reads them instead of interviewing or scanning again (see rule 12).
10. **Seed the Handoff once, never clobber it, and seed the whole picture.** After a roadmap closes
    (Phase 2) or a new section is added to an existing index (Phase 1), this skill may write
    `.specs/STATE.md`'s `## Handoff` section exactly once, and only if no feature is currently in
    flight there. The seed cites **every roadmap's status** (DONE/IN PROGRESS/NOT STARTED/NOT YET
    DECOMPOSED, with counts) and the **remaining build order** for the one in progress, not just a
    bare pointer to one feature — see [references/handoff-seed.md](references/handoff-seed.md) for
    the exact shape and a full worked example. It never touches `## Decisions`, never rewrites the
    whole file, and never writes Handoff a second time for the same generation.
11. **Interview Mode and Brownfield Mode are Phase 0 entry points only, never a guess.** They trigger
    on an explicit "there's no source yet" confirmation (the user says so, or Phase 0's own check
    for a source document comes back empty and the user confirms there isn't one) — never inferred
    silently from an empty `docs/` folder or a repo that merely looks new. Full procedure, including
    exactly what "no source yet" means for each mode: [references/scope-phase.md](references/scope-phase.md).
12. **Reuse existing project knowledge before generating any.** Before Interview Mode or Brownfield
    Mode write anything, check for what already exists: the downstream spec-driven skill's own
    project-init output, its own codebase-mapping output, or the `codenavi` skill if installed.
    Delegate or reuse first — never re-interview or re-scan what's already there, and never produce
    a competing copy of the downstream skill's own brownfield docs.

## Where this reads and writes

```
docs/
├── PROJECT.md               # Phase 0, Interview Mode ONLY (0b) — produced when no source exists
│                            # and the user doesn't know what to build yet. Becomes the source of
│                            # truth for Phase 2, same as any PRD would.
├── CODEBASE-SUMMARY.md       # Phase 0, Brownfield Mode ONLY (0c) — produced when no source exists
│                            # but a codebase does. Light, roadmap-sized — not a replacement for the
│                            # downstream skill's own deep codebase mapping.
├── ROADMAP-INDEX.md        # Phase 1 — ONLY in multi-section mode. Section map, dependency order,
│                            # boundary contracts.
├── ROADMAP-<slug>.md       # Phase 2, one per section (multi-section mode) — feature list + coverage
│                            # table. In single-section mode this is instead the single docs/ROADMAP.md.
└── roadmap-<slug>.txt      # Phase 2, same features, one name per line, build order. In single-section
                             # mode this is instead the single docs/roadmap.txt.

.specs/                     # owned by the downstream spec-driven skill — this skill only reads it to
│                            # check safety and to reuse existing project-init/codebase-mapping output
│                            # (rule 12), and writes Handoff exactly once (see rule 10).
├── STATE.md                # Decisions: this skill never writes here — Phase 1 Step 5 only proposes
│                            # candidates for the downstream skill's own Design phase to record
│                            # (including the derived cross-section build order itself — see
│                            # index-phase.md Step 5).
│                            # Handoff: written ONCE per roadmap generation/refresh — every roadmap's
│                            # status (DONE/IN PROGRESS/NOT STARTED/NOT YET DECOMPOSED) plus the
│                            # remaining build order for the one in progress, and the exact next
│                            # feature — but only if no feature is already in flight. After that
│                            # single write, this skill does not touch STATE.md again until asked to
│                            # generate/refresh a roadmap.
└── features/<name>/
    ├── context.md           # authored entirely by the downstream skill's own Discuss step — this
    │                        # skill never writes it, though it surfaces a flagged open question so
    │                        # Discuss starts already-answered
    └── validation.md        # PASS/FAIL — read-only here, used only to find "first pending feature"
                              # when seeding the Handoff
```

## Phase 0 — Locate or create the source, confirm the target workflow, and the shape of the roadmap

Three entry paths, resolved in this order: **0a** if a scope document already exists (the default
case, e.g. a PRD, ADR set, flowchart export, architecture doc); **0b — Interview Mode** if nothing
exists and the user doesn't yet know what to build; **0c — Brownfield Mode** if nothing exists but a
real codebase does. 0b and 0c both end by producing a `docs/` file that 0a then treats exactly like
any other source. Full procedure for all three paths, plus the single-vs-multi ask, target-skill
confirmation, output location, and language rules that apply regardless of which path produced the
source: [references/scope-phase.md](references/scope-phase.md).

## Phase 1 — Build/refresh the index (multi-section mode only)

Skip this phase entirely in single-section mode — there is no index, no per-section prefixes, and no
cross-section boundary contracts when the whole source is one roadmap.

In multi-section mode: skip straight to Phase 2 if `docs/ROADMAP-INDEX.md` already exists and covers
the section about to be decomposed; re-run Phase 1 only when the source scope changed or a section is
missing from the index — never wholesale-regenerate an index that already covers the current scope.
Full procedure: [references/index-phase.md](references/index-phase.md).

## Phase 2 — Decompose into features

Multi-section mode: run this for a section **right before the user is ready to start building it**,
not necessarily for every section upfront — a project only needs as much of the roadmap decomposed as
work has actually reached, which is what keeps this adaptive to scope that's still settling elsewhere.

Single-section mode: run this once, directly against the whole source (there's no per-section
laziness to have, since there's only one list).

Full procedure, including the per-feature field template, the single-section variant, and worked edge
cases (shared ownership across sections, gap-only features, features blocked on a not-yet-built
sibling section): [references/decompose-phase.md](references/decompose-phase.md).

**Context discipline (multi-section mode):** load only `docs/ROADMAP-INDEX.md`, the target section's
own content, and the project's conventions doc. Never load a sibling section's full content —
cross-section needs are already captured in the index's boundary contracts from Phase 1.

## Handoff seed — one-time, not a loop

Right after Phase 2 closes a roadmap (coverage table reads "uncovered: none") — or right after Phase 1
adds a brand-new section to an already-built index — write `.specs/STATE.md`'s `## Handoff` section
**once**, pointing the downstream spec-driven skill at the first not-yet-built feature. This is the
entire extent of this skill's involvement in construction: no waiting for PASS, no advancing to the
next feature automatically, no re-entering the picture on "resume work" (that trigger belongs fully
to the downstream skill from here on — it reads the Handoff this step wrote). Full procedure,
including the safety check that refuses to overwrite a feature already in flight:
[references/handoff-seed.md](references/handoff-seed.md).

## Relationship to other skills

- **Downstream, always — and the only driver from the seed onward.** The project's spec-driven skill
  (e.g. `tlc-spec-driven`) does all actual specify/design/tasks/execute/verify work and owns
  `.specs/features/*` + `.specs/STATE.md`. This skill never substitutes for it, never writes into
  `.specs/features/*` directly, never appends an `AD-NNN` entry on its own (only proposes candidates
  for the downstream skill's own Design phase or an explicit "record decision" to confirm), and —
  critically — **never re-invokes itself to march through the roadmap.** Once the Handoff is seeded,
  every subsequent "specify feature", "resume work", pause, and verify is the downstream skill's own
  normal flow, driven by the user or the general agent directly, not by this skill.
- **Complements, never replaces, the downstream skill's own project-init and codebase-mapping
  triggers.** If the target project's spec-driven skill has its own "initialize project" or "map
  codebase" trigger (e.g. `tlc-spec-driven` v2's `.specs/project/PROJECT.md` / `.specs/codebase/*`),
  Phase 0 reuses that output instead of running Interview Mode or Brownfield Mode (rule 12) — this
  skill's own `docs/PROJECT.md` / `docs/CODEBASE-SUMMARY.md` only get produced when nothing like that
  exists yet, and they live in this skill's own namespace, not the downstream skill's.
- **Not the same as a "decomposition planning roadmap" skill, if one is installed.** A skill by that
  kind of name typically plans monolith-to-microservices *extraction* — sprints, story points,
  component-coupling patterns. Different domain entirely, even though both outputs are called a
  "roadmap" — don't reach for the wrong one.
- **Supersedes ad-hoc index generation.** If a project has been hand-rolling its own
  `ROADMAP-INDEX.md` from a one-off prompt each time, this skill is the reusable, adaptive version
  of that same pattern — point future projects at this skill instead of re-deriving the structure
  from scratch.
