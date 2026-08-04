# Phase 0 — Locate or Create the Source, Confirm the Target Workflow, and the Shape of the Roadmap

Three entry paths. Resolve them in this order:

1. **Is there already a scope document?** → **0a**.
2. **No document, and the user doesn't know what to build yet** (a blank project, an idea with no
   written-down shape) → **0b — Interview Mode**.
3. **No document, but a real codebase already exists** (features are already built, there's just
   nothing describing them as a roadmap source) → **0c — Brownfield Mode**.

0b and 0c each end by producing a file under `docs/` — `docs/PROJECT.md` or
`docs/CODEBASE-SUMMARY.md` — and then falling straight through to 0a using that file as the source.
Neither mode is a parallel track with its own rules; they exist only to *produce* what 0a needs when
nothing is there yet.

**Never guess which path applies.** If it isn't obvious from what the user already said, ask: "Do you
already have a document describing the scope (PRD, flowchart, ADRs, architecture doc), or should we
start from an interview / from mapping the existing code?" Only silence plus an explicit "there's
nothing written down" from the user (or an empty check for both a document and a meaningfully-sized
codebase) justifies 0b/0c — per rule 11, this is never inferred from an empty `docs/` folder alone.

---

## 0a — A scope document already exists

Ask if it isn't obvious: what document describes the system's scope? Common shapes: an
already-extracted flowchart/diagram inventory (sections, nodes with stable IDs, edges, as plain
text); a PRD or set of ADRs; a `CLAUDE.md`/README-style architecture description with a
component/module table; or, if 0b/0c just ran, the `docs/PROJECT.md` / `docs/CODEBASE-SUMMARY.md`
they produced.

If the source is a diagram file (`.excalidraw`, Figma export, etc.) with no structured text
extraction yet, extract it to a plain-text inventory first — never decompose straight from
eyeballing a visual. A visual read causes silent omissions that a coverage table can't catch
afterward, because the units of scope were never enumerated in the first place.

Also confirm which spec-driven skill the target project actually has installed — default
assumption is **tlc-spec-driven**, but the Handoff seed needs the exact fresh-start trigger phrase
(e.g. "specify feature `<name>`") and the exact `.specs/STATE.md` shape that skill uses (section
names, field format), so don't assume tlc-spec-driven's conventions hold if the project runs
something else. If nothing is installed yet, say so and stop before generating a roadmap that
nothing can consume — Phase 1/2 need a real downstream skill to hand off to.

**Single roadmap vs. multiple section roadmaps — ask explicitly, decide once per project.** Present
the trade-off plainly and let the user choose:

- **Single unified roadmap** (`docs/ROADMAP.md` + `docs/roadmap.txt`, no index, no sections): one
  flat, dependency-ordered feature list covering the whole source. Simpler to read and to hand off
  feature-by-feature; the right default for a small-to-medium scope, or when the user wants to build
  everything as one continuous backlog without splitting documents.
- **Multiple section roadmaps** (`docs/ROADMAP-INDEX.md` + one `docs/ROADMAP-<slug>.md`/
  `roadmap-<slug>.txt` per section): the source is split along its own real boundaries, each with its
  own feature list, cross-section boundary contracts, and independent build order. Worth it when
  sections are large enough, or independent enough, that the user wants to reason about — or build —
  them somewhat separately.

Do not infer this from how large the source looks — ask. Exception: if the project already has
`docs/ROADMAP-INDEX.md` **or** `docs/ROADMAP.md` on disk, the mode is already decided; don't re-ask,
just continue in whichever mode is already established (extending it, per Phase 1's/Phase 2's own
"when to re-run" rules) unless the user explicitly asks to change shape, which is a rare, disruptive
enough choice to confirm again before touching anything already written.

Also locate the project's conventions doc, if one exists (`CLAUDE.md`, `README`, contributing
guide) — Phase 2 loads it alongside each section (or the whole source, in single-section mode) to
keep naming, stack choices, and non-negotiables consistent with the rest of the project.

**Output location default:** `docs/`. If the project already keeps planning docs somewhere else,
confirm the target directory instead of assuming `docs/`.

**Language:** write generated roadmaps in the source document's dominant language — match it, don't
default to English.

---

## 0b — Interview Mode (no source, no idea yet)

**Trigger:** the user has no document and says something like "I don't know what to build yet",
"help me plan this from scratch", "plan product", or answers "nothing written down, and I'm not sure
what I want" to the entry-path question above.

**Before interviewing, check for existing project knowledge (rule 12):**

1. Does the downstream spec-driven skill already have its own project-init output (e.g.
   `tlc-spec-driven`'s `.specs/project/PROJECT.md`)? If so, read it and treat *that* as the source —
   skip straight to 0a, don't interview over something that already exists.
2. Otherwise, proceed with the interview below.

**Process — one question at a time, via `AskUserQuestion`.** Never batch multiple questions into one
message; wait for each answer before asking the next. Stop as soon as there's a clear enough picture
of vision, users, and MVP boundaries to decompose from — brief answers are fine, this doc can be
thin, Phase 2 is what does the heavy lifting.

Ask, in order (skip a question if the user already answered it earlier in the conversation):

1. **What are you building, in one or two sentences?**
2. **Who is it for, and what problem does it solve for them?**
3. **What's the smallest version that's actually useful (MVP)?** — this is what becomes the roadmap's
   feature list; press for concreteness if the answer is abstract ("a way to manage tasks" →
   "create/complete/delete tasks, one shared list per team").
4. **What's explicitly out of scope for now?** — anything the user is tempted to build later but not
   now; this keeps Phase 2 from silently including it.
5. **Any hard constraints?** (timeline, must-use tech, team size, compliance) — optional, skip if the
   user has none.
6. **What tech stack, if you already know?** — optional; if unknown, Phase 2 will flag stack choices
   as open questions per rule 1 instead of guessing one.

**Output: `docs/PROJECT.md`**

```markdown
# [Project Name]

**Vision:** [1-2 sentence description — from Q1]
**For:** [target users — from Q2]
**Solves:** [core problem — from Q2]

## MVP Scope

- [Capability 1 — from Q3]
- [Capability 2 — from Q3]
- [Capability N — from Q3]

## Explicitly Out of Scope

- [What is NOT being built now — from Q4]

## Constraints

- [Timeline / must-use tech / team / compliance, if any — from Q5. Omit section if none.]

## Tech Stack

- [If known — from Q6. Otherwise: "Not yet decided — flagged as open questions per feature in the
  roadmap."]
```

Once written, report the file to the user and fall through to **0a** using `docs/PROJECT.md` as the
source — same single-vs-multi ask, same target-skill confirmation, same everything from here on.
Interview Mode's job ends the moment this file is written; it does not re-run mid-roadmap, and it
never becomes the place features/specs get written (rule 9).

---

## 0c — Brownfield Mode (no source, but a codebase exists)

**Trigger:** the user has an existing, non-trivial codebase but no document describing its scope —
"map this codebase into a roadmap source", or the entry-path question above answered "there's code,
just nothing written about it."

**Before scanning, check for existing project knowledge, in this order (rule 12) — never skip ahead
to a native scan while an earlier option is available:**

1. **Downstream skill's own codebase-mapping output** — e.g. `tlc-spec-driven`'s `.specs/codebase/*`
   (`STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `STRUCTURE.md`, `TESTING.md`, `INTEGRATIONS.md`,
   `CONCERNS.md`) or whatever the confirmed target skill's equivalent is. If present, read those
   directly and skip straight to 0a using them as the source — do not write
   `docs/CODEBASE-SUMMARY.md` at all in this case; re-deriving what already exists would just drift
   out of sync with it.
2. **The `codenavi` skill**, if installed. Delegate exploration to it rather than reading files
   natively — it's built for exactly this and will be faster and more accurate than an ad-hoc scan.
3. **A light native scan**, only if neither of the above is available.

**What the native scan covers — deliberately lighter than a full brownfield map.** This skill only
needs enough to *decompose into features*, not to onboard someone onto the codebase (that depth is
the downstream skill's own "map codebase" job, and duplicating it here would go stale the moment the
real one runs). Look at:

- Dependency manifest(s) → tech stack, one line per layer (frontend/backend/database/other).
- Top-level directory structure (2-3 levels) → what areas/modules exist.
- Entry points, route/controller lists, or a README's own feature list, whichever exists → what
  capabilities are already built, in plain language, not file-by-file detail.

Sample representative files only (5-10), the same discipline the downstream skill's own mapping
uses — this is a summary, not an audit.

**Output: `docs/CODEBASE-SUMMARY.md`**

```markdown
# Codebase Summary — [Project Name]

**Purpose:** roadmap-decomposition source only — for implementation-depth conventions and
architecture, see the downstream spec-driven skill's own codebase mapping (run "map codebase" /
"analyze existing code" if it hasn't been run yet).

## Tech Stack

- Frontend: [detected, or "N/A"]
- Backend: [detected, or "N/A"]
- Database: [detected, or "N/A"]

## Existing Areas / Modules

- **[area name]** ([location]) — [one line: what it does]
- **[area name]** ([location]) — [one line: what it does]

## Capabilities Already Built

- [capability, in plain language — this is what Phase 2 must NOT re-list as new scope]

## Gaps / Likely Next Work

- [anything the user mentioned wanting to add, or an obvious missing piece next to what exists —
  phrase as a candidate for the roadmap, never a decided feature]
```

Once written, report the file to the user and fall through to **0a** using `docs/CODEBASE-SUMMARY.md`
as the source. Phase 2 treats "Capabilities Already Built" as already-covered scope (not to be
re-decomposed) and "Gaps / Likely Next Work" as the candidate feature list to actually decompose —
confirm that reading with the user before Phase 2 starts, since it's the one place this mode makes an
interpretive call rather than a direct extraction.
