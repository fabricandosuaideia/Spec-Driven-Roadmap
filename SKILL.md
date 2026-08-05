---
name: spec-driven-roadmap
description: Generates a dependency-ordered feature backlog (a ROADMAP.md plus a machine-readable build-order .txt, or a ROADMAP-INDEX.md with one roadmap per section) and seeds the downstream spec-driven skill so it can start building feature one. Sources the scope from an existing PRD, architecture doc or flowchart export, from an interview when the user has no document, or from an existing codebase. Use when the user says "generate a roadmap", "create a roadmap", "plan product", "decompose this into features", "turn this PRD into a backlog", or "I do not know what to build yet". Do NOT use for writing a feature's spec, design, tasks or code, for driving construction, or for "resume work" - those belong to the downstream spec-driven skill.
license: MIT
metadata:
  author: Fabricando Sua Ideia - github.com/fabricandosuaideia
  version: "3.3.0"
---

# Spec-Driven Roadmap

Turn a system's scope into a dependency-ordered feature backlog, ready for a spec-driven workflow to
build one feature at a time. This skill **plans once and hands off once**: it locates or creates the
scope, decomposes it into vertical features, and seeds the downstream skill with the first feature to
build. It never builds anything itself.

```
PHASE 0            PHASE 1          PHASE 2            HANDOFF SEED
scope + ask   →    index       →    decompose     →    durable Status in docs/
0a doc exists      (multi-           (per section,      + one Handoff write to
0b interview        section           or all at once     .specs/STATE.md, then
0c codebase         mode only)        if single)         this skill is done
```

**Precedence: when this file and a reference file disagree, the reference file wins.** This file is
a map; the procedures live in `references/`. Read the relevant reference completely before acting.

| Phase | Reference | What it does |
|---|---|---|
| 0 | [references/scope-phase.md](references/scope-phase.md) | Locate a source doc (0a), interview to create one (0b), or derive one from the codebase (0c). Confirms the downstream skill, output language, and single-vs-multi mode. |
| 1 | [references/index-phase.md](references/index-phase.md) | Multi-section mode only: section map, dependency graph, boundary contracts. |
| 2 | [references/decompose-phase.md](references/decompose-phase.md) | Slice into vertical features with full coverage, open questions, and a build order. Then pre-empt the cross-cutting gray areas, and record the ones left to the downstream skill. |
| Seed | [references/handoff-seed.md](references/handoff-seed.md) | Write the durable `## Status` block, then one Handoff write to `.specs/STATE.md`. Then hand the user one implementation prompt — a single feature, or a `/loop` over the whole roadmap (which first requires every open question closed). |

## Non-negotiable rules

1. **Never decide a genuine ambiguity.** A missing technology choice, an undefined business rule, a
   source that just does not say — record it in the feature's `open questions` field, citing where
   it is unresolved. Never guess, never pick a silent default.
2. **Vertical slices only.** A feature is route + service + persistence + test for one coherent
   capability. Never slice by architectural layer. *One bounded exception:* a genuinely shared
   foundation consumed by three or more later features may be its own slice, and must name its
   consumers (see decompose-phase Step 3).
3. **Eight tasks per feature, maximum.** Over budget means split and say why. Never pad.
4. **No forward dependencies.** A feature may only depend on one listed earlier in the same roadmap.
   Cross-section needs are boundary contracts, never "depends on".
5. **Full coverage, exactly once.** Every scope-unit maps to exactly one feature, or to an explicit
   `deferred` / `pre-existing` disposition. The coverage table must close with `uncovered: none`.
6. **Globally unique feature names.** Check every `docs/ROADMAP-*.md`, `docs/ROADMAP.md`, and every
   existing `.specs/features/*` directory before naming anything.
7. **Flag implicit-requirement dimensions** per feature: persistence/state, external calls, auth,
   payments, concurrency, state transitions. Any present, or any open question, sets "needs
   pre-written context.md" to yes. These are the same dimensions that trigger the downstream skill's
   own Discuss step, which is what writes `context.md` — this field predicts that.
8. **Pre-empt only the gray areas that skill cannot see.** Flagging predicts *that* Discuss will
   fire; it says nothing about *what* it will demand. Phase 2's Step 7 closes that gap against the
   downstream skill's own dimensions rubric, and splits by a three-part test: only-the-user-decides,
   spans two or more features, expensive to reverse. All three → ask now, record in
   `## Cross-Cutting Decisions`. Any missing → record in `## Expected Gray Areas` and leave it to
   Discuss, which answers it better with the code in front of it. Never sweep everything: a question
   asked here that the built code would have answered later spends the user's attention twice.
9. **Ask how the scope is shaped.** Single unified roadmap versus multiple section roadmaps is the
   user's call, made explicitly in Phase 0. Never infer it from how big the source looks. Exception:
   an existing `docs/ROADMAP-INDEX.md` or `docs/ROADMAP.md` already fixed the mode — continue in it.
   If *both* exist, that is a contradiction: stop and ask which is authoritative.
10. **Delegate, never author, never loop.** Never write `spec.md`, `design.md`, `tasks.md`, or
    application code. Never re-invoke this skill to march through features. Phase 0's own modes write
    only to `docs/` — never into the downstream skill's namespace. Handing the user a `/loop` prompt
    at the seed is not an exception: this skill emits that text and stops. The loop is the user's CLI
    driving the downstream skill, never this skill running itself.
11. **Seed once per generation, and never clobber real work.** Write the durable backlog status to
    this skill's own `docs/` file, and only the downstream skill's own field schema to
    `.specs/STATE.md`'s `## Handoff` — never an entry under `## Decisions`. Stop if work is genuinely
    in flight — tested by evidence, not by whether the Handoff is empty.
12. **Interview and Brownfield modes need explicit confirmation.** Enter them only when a check for
    a source came back empty **and** the user confirmed there is none. An empty `docs/` folder alone
    is never sufficient.
13. **Reuse existing project knowledge before generating any.** Check for the downstream skill's own
    project-init or codebase-mapping output, and for `codenavi`, before interviewing or scanning.

## Where this writes

- `docs/PROJECT.md` — Phase 0b only, when an interview created the scope.
- `docs/CODEBASE-SUMMARY.md` — Phase 0c only, when the codebase was the source.
- `docs/ROADMAP-INDEX.md` — Phase 1, multi-section mode only. Carries the `## Status` and
  `## Cross-Cutting Decisions` blocks.
- `docs/ROADMAP.md` / `docs/ROADMAP-<slug>.md` — Phase 2 feature lists, coverage tables, the
  `## Open Questions` and `## Expected Gray Areas` roll-ups. In single-section mode `ROADMAP.md` also
  carries `## Status` and `## Cross-Cutting Decisions` — exactly one of each exists per project.
- `docs/roadmap.txt` / `docs/roadmap-<slug>.txt` — build order, one feature name per line.
- `.specs/STATE.md` `## Handoff` — one write per generation, in the downstream skill's schema.
  Never an entry under `## Decisions` (the empty header may be created once, only when creating
  `STATE.md` from scratch); never `.specs/features/*`.

Output directory is `docs/`. This is fixed, not configurable.

## Relationship to other skills

- **Downstream, always.** The project's spec-driven skill (default assumption:
  `tlc-spec-driven`) does all specify/design/tasks/execute/verify work and owns `.specs/`. This skill
  never substitutes for it, never appends an `AD-NNN` decision itself (Phase 1 only proposes
  candidates), and never re-invokes itself. After the seed, every "specify feature", "resume work",
  pause and verify is the downstream skill's own flow.
- **Complements its project-init and codebase-mapping triggers.** If the confirmed downstream skill
  has its own such step, Phase 0 reuses that output instead of running 0b or 0c (rule 13). Note these
  differ by version — `tlc-spec-driven` v2 had them, v3 does not; detect, do not assume.
- **Not a decomposition-planning skill.** Skills with similar names plan monolith-to-microservices
  extraction — sprints, story points, coupling analysis. Different domain entirely.
