---
name: spec-driven-roadmap
description: Generates a dependency-ordered feature backlog (a ROADMAP.md plus a machine-readable build-order .txt, or a ROADMAP-INDEX.md with one roadmap per section) and seeds the downstream spec-driven skill so it can start building feature one. Sources the scope from an existing PRD, architecture doc or flowchart export, from an interview when the user has no document, or from an existing codebase. Use when the user says "generate a roadmap", "create a roadmap", "plan product", "decompose this into features", "turn this PRD into a backlog", or "I do not know what to build yet". Do NOT use for writing a feature's spec, design, tasks or code, for driving construction, or for "resume work" - those belong to the downstream spec-driven skill.
license: MIT
metadata:
  author: Fabricando Sua Ideia - github.com/fabricandosuaideia
  version: "3.6.1"
---

# Spec-Driven Roadmap

Turn a system's scope into a dependency-ordered feature backlog, ready for a spec-driven workflow to
build one feature at a time. This skill **plans once and hands off once**: it locates or creates the
scope, decomposes it into vertical features, and seeds the downstream skill with the first feature to
build. It never builds anything itself.

```
PHASE 0            PHASE 1          PHASE 2            HANDOFF SEED
scope + ask   →    index       →    decompose     →    durable Status in docs/
0a doc exists      (multi-           (per section,      + a Handoff write to
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
| Seed | [references/handoff-seed.md](references/handoff-seed.md) | Write the durable `## Status` block, then — only when Phase 0 confirmed a skill whose schema is readable — a Handoff write to `.specs/STATE.md`. Then hand the user one implementation prompt — a single feature, or a `/loop` over one roadmap (which first requires every open question in it closed). |

## Version and model

**The canonical version of this skill is the `metadata.version` value in this file's frontmatter.**
There is no top-level `version` field in a `SKILL.md` — the [Agent Skills
spec](https://agentskills.io/specification) defines six keys (`name`, `description`, `license`,
`compatibility`, `metadata`, `allowed-tools`), and its own example nests `author` and `version`
under `metadata`, which is what this file does. The installers copy `SKILL.md`, `references/` and
the runtime `scripts/`, so this frontmatter is the single version stamp that ever reaches the
user's disk.

**Announce that version before the first question of any run.** State the version read from this
file's frontmatter, and where to check the latest published one: `/plugin update` for a plugin
install, or the comparison command the README documents for a standalone install. One line,
delivered as an announcement — never as a question, so it costs no turn (scope-phase.md, preamble).

**Model and effort are a recommendation this skill states and never applies itself.** A run here
freezes build order, scope boundaries and feature names into files the whole downstream build cycle
then obeys, and rule 1 turns on recognising a genuine ambiguity instead of filling the gap. Running
on the best available model, at the highest effort level, is therefore recommended. The user sets
both with `/model` and `/effort` **before** starting. This skill never switches them on its own: a
frontmatter `model` would hold for the current turn only — *"The override applies for the rest of
the current turn and is not saved to settings; the session model resumes on your next prompt"* — and
this skill is multi-turn by design. And any field outside the spec's six breaks packaging and upload
for claude.ai and the Skills API: *"If you include any field the spec doesn't allow, packaging or
upload fails with a hard error instead of ignoring the field"*, with the documented error naming the
allowed set — *"Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are:
allowed-tools, compatibility, description, license, metadata, name"*. All three quotations from the
[Claude Code skills documentation](https://code.claude.com/docs/en/skills), consulted 2026-08-07 —
the `model` one from its frontmatter reference table, the two on packaging from its
`Using skill frontmatter outside Claude Code` section.

## Non-negotiable rules

1. **Never decide a genuine ambiguity.** A missing technology choice, an undefined business rule, a
   source that just does not say — record it in the feature's `open questions` field, citing where
   it is unresolved. Never guess, never pick a silent default. An ambiguity belonging to no single
   feature has a home too: the `## Open Questions` roll-up, tagged `cross-cutting` and carrying an
   `affects:` line naming the features it reaches (Phase 2 Step 7a). "There was no feature to put it
   in" is never a reason it goes unrecorded.
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
   payments, concurrency, state transitions. Any present, or any open question still `status: open`,
   sets "needs pre-written context.md" to yes — an *answered* question does not, which is what lets
   the field flip back after an interview closes one. These six are the downstream skill's Discuss
   **trigger** list, and Discuss is what writes `context.md` — this field predicts that. They are not
   rule 8's rubric; the two lists overlap but are not interchangeable.
8. **Pre-empt only the gray areas that skill cannot see.** Flagging predicts *that* Discuss will
   fire; it says nothing about *what* it will demand. Phase 2's Step 7 closes that gap against the
   downstream skill's **rubric** — a different, longer list than rule 7's six triggers — and splits
   by a three-part test: only-the-user-decides, spans two or more features, expensive to reverse.
   Three destinations, exactly one each: all three tests **and answered** → that theme's row in
   `## Cross-Cutting Decisions`; all three but left **unanswered** → a `cross-cutting` question in
   `## Open Questions` plus a `not decided` row in that same ledger, because silence never promotes
   a proposed default into a decision; any test missing → `## Expected Gray Areas`, left to Discuss,
   which answers it better with the code in front of it. Never sweep everything: a question asked
   here that the built code would have answered later spends the user's attention twice.
9. **Ask how the scope is shaped.** Single unified roadmap versus multiple section roadmaps is the
   user's call, made explicitly in Phase 0. Never infer it from how big the source looks. Exception:
   an existing `docs/ROADMAP-INDEX.md` or `docs/ROADMAP.md` already fixed the mode — continue in it.
   If *both* exist, that is a contradiction: stop and ask which is authoritative. Section roadmaps
   (`docs/ROADMAP-<slug>.md`) present with **no** `docs/ROADMAP-INDEX.md` beside them are the same
   class of contradiction — a single-to-multi conversion that stopped half-way, leaving orphaned
   section roadmaps: stop and ask before writing anything. That glob is a filename pattern, not a
   proof: a `docs/ROADMAP-*.md` carrying no feature entries and named by no index is some other
   document that happens to match, so proceed and record having checked.
10. **Delegate, never author, never loop.** Never write `spec.md`, `design.md`, `tasks.md`, or
    application code. Never re-invoke this skill to march through features. Phase 0's own modes write
    only to `docs/` — never into the downstream skill's namespace. Handing the user a `/loop` prompt
    at the seed is not an exception: this skill emits that text and stops. The loop is the user's CLI
    driving the downstream skill, never this skill running itself.
11. **Seed one surface, and never clobber real work.** Write the durable backlog status to this
    skill's own `docs/` file, and only the downstream skill's own field schema to `.specs/STATE.md`'s
    `## Handoff` — never an entry under `## Decisions`. That section is always a full overwrite of
    its own body, never an append, so re-writing it is safe and sometimes required: the seed's loop
    interview can move the target, and the Handoff must not contradict the prompt handed over. Stop
    if work is genuinely in flight — tested by evidence, not by whether the Handoff is empty.
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
- `.specs/STATE.md` `## Handoff` — the only write into that namespace, in the downstream skill's
  schema, always a full overwrite of that section's body, and **only when Phase 0 confirmed a skill
  whose schema is readable**; otherwise nothing under `.specs/` is created at all. Never an entry
  under `## Decisions` (the empty header may be created once, only when creating `STATE.md` from
  scratch); never `.specs/features/*`.

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
