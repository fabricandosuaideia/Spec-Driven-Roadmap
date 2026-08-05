# Phase 0 — Locate or Create the Source, and Frame the Roadmap

## Contents

- [Preamble — settle these before branching](#preamble--settle-these-before-branching) — downstream skill, language, how to ask
- [Routing — pick 0a, 0b, or 0c](#routing--pick-0a-0b-or-0c)
- [0a — A scope document already exists](#0a--a-scope-document-already-exists)
- [0b — Interview Mode (no source, no clear idea yet)](#0b--interview-mode-no-source-no-clear-idea-yet)
- [0c — Brownfield Mode (no source, but a codebase exists)](#0c--brownfield-mode-no-source-but-a-codebase-exists)
- [Closing checks](#closing-checks)

---

## Preamble — settle these before branching

These apply to all three paths, so resolve them **before** routing — not inside 0a, which 0b and 0c
run before reaching.

**Confirm the downstream spec-driven skill.** Default assumption is `tlc-spec-driven`, but the seed
needs that skill's exact fresh-start trigger phrase and its exact `.specs/STATE.md` field schema, and
0b/0c need to know whose project-init output to reuse (rule 13). Ask if it is not evident from the
project.

*If nothing is installed yet:* **generate the roadmap anyway.** Phases 1 and 2 write only to `docs/`
and produce artifacts a human or any agent can use. Only the Handoff seed needs a downstream skill.
Report the seed as pending, and tell the user which skill to install to complete the chain. Do not
stop the whole run.

**Fix the output language.** Write generated documents in the language of the source document if one
exists; otherwise the language the user is conversing in — this applies to prose and body text.

**Carve-out, always English regardless:** feature names, prefixes, slugs, filenames, the downstream
skill's Handoff field labels (`**Feature**`, `**Next step**`, …), **and every generated section
heading** (`## MVP Scope`, `## Explicitly Out of Scope`, `## Capabilities Already Built`,
`## Gaps / Likely Next Work`, `## Status`, `## Open Questions`). Those are machine-read keys, path
components, and literals that later phases locate by exact name — translating any of them breaks the
handoff, the `.specs/features/<name>/` directories, or a cross-file lookup.

**How to ask.** One question at a time — never batch. Wait for each answer before asking the next.
Use `AskUserQuestion` where a genuine small option set exists (single-vs-multi mode, which downstream
skill, stack known versus not-yet-decided). Ask open questions as free text with a short parenthetical
hint — do not fabricate 2-4 options for "what are you building?", since inventing candidate answers
anchors the user to something you made up.

---

## Routing — pick 0a, 0b, or 0c

Evaluate in order; the first match wins, so the paths never overlap:

1. **A scope document exists** (PRD, ADR set, architecture doc, flowchart export, or a
   `docs/PROJECT.md` / `docs/CODEBASE-SUMMARY.md` from a previous run) → **0a**.
2. **No document, but a substantial codebase exists** → **0c, Brownfield Mode** — regardless of
   whether the user knows what to build next. 0c asks them that directly, and what already exists
   constrains what to build next, so the codebase must be read either way.
3. **No document and no substantial codebase** → **0b, Interview Mode**.

**Substantial codebase** means: a dependency manifest plus at least one non-scaffold source
directory. A bare `create-*-app` skeleton is not substantial — that is a greenfield project, so it
routes to 0b.

**Never guess the route.** Enter 0b or 0c only when **both** hold: (i) a check for a source document
came back empty, **and** (ii) the user has explicitly confirmed there is none. An empty check alone
is never sufficient — ask, then wait. If it is not obvious, ask directly: *"Do you already have a
document describing the scope — a PRD, flowchart, ADRs, an architecture doc — or should we start from
an interview, or from mapping the existing code?"*

---

## 0a — A scope document already exists

Confirm which document describes the scope. Common shapes: an extracted flowchart inventory
(sections, nodes with stable IDs, edges, as plain text); a PRD or ADR set; a `CLAUDE.md`/README-style
architecture description with a component table; or the file 0b/0c just produced.

**If the source is a diagram file** (`.excalidraw`, Figma export) with no structured text extraction
yet, extract it to a plain-text inventory first. Never decompose straight from eyeballing a visual —
a visual read causes silent omissions the coverage table cannot catch afterward, because the units
were never enumerated in the first place.

### Single roadmap versus multiple section roadmaps — ask explicitly

Present the trade-off and let the user choose:

- **Single unified roadmap** (`docs/ROADMAP.md` + `docs/roadmap.txt`, no index): one flat,
  dependency-ordered list covering the whole source. Simpler to read and hand off; right for
  small-to-medium scope, or when the user wants one continuous backlog.
- **Multiple section roadmaps** (`docs/ROADMAP-INDEX.md` + one `docs/ROADMAP-<slug>.md` and
  `docs/roadmap-<slug>.txt` per section): split along the source's own boundaries, each with its own
  feature list, boundary contracts, and build order. Worth it when sections are large or independent
  enough to reason about, or build, separately.

Do not infer this from source size — ask. **Exception:** if `docs/ROADMAP-INDEX.md` or
`docs/ROADMAP.md` already exists, the mode is decided; continue in it (extending, per each phase's
"when to re-run" rules) unless the user explicitly asks to change shape, which is disruptive enough
to confirm again before touching anything already written.

Also locate the project's conventions doc if one exists (`CLAUDE.md`, README, contributing guide) —
Phase 2 loads it to keep naming and stack choices consistent with the rest of the project.

---

## 0b — Interview Mode (no source, no clear idea yet)

**Trigger:** the user has no document and says something like "I don't know what to build yet",
"help me plan this from scratch", or "plan product".

### Step 0 — Reuse and overwrite checks

1. **Does the downstream skill already have project-init output?** (e.g. `tlc-spec-driven` **v2's**
   `.specs/project/PROJECT.md` — v3.x has no such step, so detect rather than assume.) If present,
   read it and go to 0a with it as the source. Do not interview over something that already exists.
2. **Does `docs/PROJECT.md` already exist?** Show its current `## MVP Scope` and ask: use it as-is
   (go to 0a), update specific sections, or start fresh. Never silently overwrite it.

### Step 1 — Interview, one question at a time

Stop as soon as vision, users, and MVP boundaries are clear enough to decompose from. Brief answers
are fine — this document can be thin; Phase 2 does the heavy lifting. Skip any question the user
already answered earlier in the conversation.

1. **What are you building?** (one or two sentences)
2. **Who is it for, and what problem does it solve for them?**
3. **What is the smallest version that is actually useful?** Press for concreteness if the answer is
   abstract — "a way to manage tasks" becomes "create, complete and delete tasks; one shared list per
   team". Each item here becomes a scope-unit, so vagueness costs you at Phase 2.
4. **What is explicitly out of scope for now?**
5. **Any hard constraints?** (timeline, must-use tech, team, compliance) — skip if none.
6. **What tech stack, if you already know?** — if unknown, say so; Phase 2 will record stack choices
   as open questions rather than guessing.

### Step 2 — Write `docs/PROJECT.md`

Number the scope-units so Phase 2's coverage table can cite them stably. **IDs are permanent: append
new ones, never renumber existing ones.**

```markdown
# [Project Name]

**Vision:** [one or two sentences - Q1]
**For:** [target users - Q2]
**Solves:** [core problem - Q2]

## MVP Scope

- **M1** — [capability, concrete enough to become a feature - Q3]
- **M2** — [capability - Q3]

## Explicitly Out of Scope

- [not being built now - Q4]

## Constraints

- [timeline / must-use tech / team / compliance - Q5. Omit the section if none.]

## Tech Stack

- [if known - Q6. Otherwise: "Not yet decided - recorded as open questions per feature."]
```

Then go to **0a**, using `docs/PROJECT.md` as the confirmed source — you already know what it is, so
do not re-ask which document describes the scope. Continue at 0a's single-vs-multi question.

---

## 0c — Brownfield Mode (no source, but a codebase exists)

**Trigger:** a substantial codebase (see Routing) with no document describing its scope.

### Step 0 — Reuse and overwrite checks

**First, before anything else: does `docs/CODEBASE-SUMMARY.md` already exist?** If so, show its
`## Capabilities Already Built` and ask: use as-is (go to 0a), update specific sections, or start
fresh. Never silently overwrite it, and never run a scan whose output already exists.

Then resolve the source in this order; never skip ahead while an earlier option is available.

1. **The downstream skill's own codebase-mapping output** — e.g. `tlc-spec-driven` **v2's**
   `.specs/codebase/*`. Version matters: v3.x has no such step, so *check whether the confirmed
   downstream skill documents one* rather than assuming a path. If it exists, reuse it for stack,
   modules and existing capabilities — cite it by reference instead of copying, so it cannot drift.
2. **The `codenavi` skill**, if installed. Delegate exploration to it rather than reading files
   natively.
3. **A light native scan**, when neither is available.

**Branches 1 and 2 describe what exists — they never say what to build next.** So whichever branch
supplied the first three sections, you must **always** produce `## Gaps / Likely Next Work`, and its
only reliable source is the user. Ask them directly: *"What do you want to add or change in this
codebase?"* Never infer a backlog from tech-debt observations — rule 1 forbids inventing scope, so
without this question the run stalls with nothing to decompose.

### Step 1 — The light native scan (branch 3 only)

Deliberately lighter than a full brownfield map: enough to decompose into features, not to onboard
someone. Deep implementation context is the downstream skill's own job, and duplicating it here would
go stale the moment that runs.

- Dependency manifests → tech stack, one line per layer.
- Top-level directory structure, two or three levels → what areas exist.
- Entry points, route/controller lists, or a README's feature list → what capabilities already exist,
  in plain language.

Extract actual examples, not assumptions: every entry you write must trace to a file you actually
read, and each `## Capabilities Already Built` bullet records that file as its evidence anchor.

**Sample 5-10 representative files per category** — per category, not overall. A whole-repo cap of
ten files on a monorepo produces a module list that omits most of the system. If the repo is too
large to sample at that depth, say so and ask which areas matter for this roadmap.

### Step 2 — Confirm before writing

Present two lists in chat and get them corrected first: **Capabilities Already Built** and
**Gaps / Likely Next Work**. Offer confirm / move / add / remove. This matters because anything
mis-filed as already-built is excluded from the roadmap permanently, and the coverage table cannot
catch it — the unit was never enumerated. If the user corrects the reading after the file is written,
rewrite the file.

### Step 3 — Write `docs/CODEBASE-SUMMARY.md`

Number the gap units, same rule as 0b: permanent, append-only.

```markdown
# Codebase Summary — [Project Name]

**Purpose:** roadmap-decomposition source only. Implementation-depth conventions and architecture
are not covered here.

## Tech Stack

- Frontend / Backend / Database: [detected, or "N/A"]

## Existing Areas / Modules

- **[area]** ([location]) — [one line]

## Capabilities Already Built

- **C1** — [capability] (evidence: `path/to/file.ext`)
  [Phase 2 marks these `pre-existing` in the coverage table, not new scope.]

## Gaps / Likely Next Work

- **G1** — [what the user wants to add or change. This is what Phase 2 actually decomposes.]
```

If a reused branch-1/2 document supplied the upper sections, cite it by path in **Purpose** instead
of copying its content.

Then go to **0a** with this as the confirmed source, continuing at the single-vs-multi question.

---

## Closing checks

Before leaving Phase 0, confirm:

- **0b:** vision states a problem in one or two sentences; every `## MVP Scope` bullet is concrete
  enough to become a feature; out-of-scope is explicit.
- **0c:** every "already built" bullet traces to a file actually read; `## Gaps / Likely Next Work`
  is non-empty and came from the user, not inferred.
- **All paths:** the downstream skill is confirmed (or its absence recorded and the seed marked
  pending); the output language is fixed; the single-vs-multi mode is decided.
