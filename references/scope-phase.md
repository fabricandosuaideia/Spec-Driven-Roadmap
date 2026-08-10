# Phase 0 — Locate or Create the Source, and Frame the Roadmap

## Contents

- [Preamble — settle these before branching](#preamble--settle-these-before-branching) — version and model, downstream skill, language, how to ask
- [Routing — pick 0a, 0b, or 0c](#routing--pick-0a-0b-or-0c)
- [0a — A scope document already exists](#0a--a-scope-document-already-exists) — single versus multi, new scope arriving at an existing roadmap
- [0b — Interview Mode (no source, no clear idea yet)](#0b--interview-mode-no-source-no-clear-idea-yet)
- [0c — Brownfield Mode (no source, but a codebase exists)](#0c--brownfield-mode-no-source-but-a-codebase-exists)
- [Closing checks](#closing-checks)

---

## Preamble — settle these before branching

These apply to all three paths, so resolve them **before** routing — not inside 0a, which 0b and 0c
run before reaching.

**Open the run with the version and the model recommendation.** In one short message, before the
first question: the version of this skill — the `metadata.version` value in `SKILL.md`'s
frontmatter, the only version stamp the installers put on disk — where to check the latest
published one (decided by the path you resolve that `SKILL.md` from: under a plugins directory →
`/plugin update`; under `.claude/skills/spec-driven-roadmap/`, project or home → re-running the
installer, which prints `installing <latest> (replacing <yours>)` before it touches anything and so
reports the comparison whether or not they go through with it — never the README, which the
installers do not copy; anywhere else, such as a repository checkout or a path the user
named → say where it is running from and that neither update route applies, so the comparison is
against the repository), and that a roadmap run is best done on the strongest available model at
the highest effort, which the user sets with `/model` and `/effort` **before** starting (SKILL.md,
"Version and model"). **Resolve that version exactly as that section prescribes** — it names the
file to open and forbids filling the number from memory. Do not restate that procedure here; it is
already in context, since `SKILL.md` is. **If the version cannot be read, announce `unknown`**
rather than dropping the line: the announcement exists to tell the user which release is
on disk, and a silent omission reads as if there were nothing to check. This is an **announcement,
not a question**: it asks for nothing and expects no answer, so it neither batches nor consumes a
turn, and the "One question at a time — never batch" cadence below is untouched. Do not wait for a
reply — continue straight into the first question.

**Confirm the downstream spec-driven skill.** Default assumption is `tlc-spec-driven`, but the seed
needs that skill's exact fresh-start trigger phrase and its exact `.specs/STATE.md` field schema, and
0b/0c need to know whose project-init output to reuse (rule 13). **Look for it on disk before
asking**, in the search order handoff-seed.md's Step 2 prescribes — a project install, then a global
one, then a plugin — and say which path answered. Concluding "none installed" without having looked
is what sends a run down the no-downstream-skill branch while the skill is sitting there. Ask only
when the search is genuinely empty, or when what you found is not evidently the project's choice.

*If nothing is installed yet:* **generate the roadmap anyway.** Phases 1 and 2 write only to `docs/`
and produce artifacts a human or any agent can use. The seed still runs — it just stops after its
`docs/` half and writes nothing under `.specs/` (handoff-seed.md Step 6's skip). Record the pending
seed on the `## Status` block's `**Handoff**` line, tell the user which skill to install, and say
that re-running the seed afterwards completes the chain without re-running Phase 2. Do not stop the
whole run.

**Fix the output language.** Write generated documents in the language of the source document if one
exists; otherwise the language the user is conversing in — this applies to prose and body text.

**Carve-out, always English regardless:** feature names, prefixes, slugs, filenames, the downstream
skill's Handoff field labels (`**Feature**`, `**Next step**`, …), **every generated section
heading** (`## MVP Scope`, `## Explicitly Out of Scope`, `## Capabilities Already Built`,
`## Gaps / Likely Next Work`, `## Status`, `## Open Questions`, `## Cross-Cutting Decisions`,
`## Expected Gray Areas`, `## Coverage`, `## Execution Order`), **and every literal
`scripts/check-roadmap.py` matches**: the per-feature field labels decompose-phase.md Step 6
defines, the `discharge:` line, the `status: open` / `status: answered` tags, the `cross-cutting`
tag and its `affects:` line, the ledger's `Theme` column header and the state words `not decided` /
`n/a because` / `deferred to feature`, and the `uncovered:` line — together with the sentinel values
those checks read (`none`, `yes`, `no`). Those are machine-read keys, path components, and literals
that later phases locate by exact name — translating any of them breaks the handoff, the
`.specs/features/<name>/` directories, or a cross-file lookup. Only the prose after the key is in
the source language.

**How to ask, in this phase.** One question at a time — never batch. Wait for each answer before
asking the next. (Phase 2's Step 7a deliberately batches its cross-cutting themes and says why; the
seed's loop interview goes back to one at a time. Three cadences, three reasons — this is Phase 0's.)
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

**Another contradiction — the half-finished conversion.** Section roadmaps
(`docs/ROADMAP-<slug>.md`) present with **no** `docs/ROADMAP-INDEX.md` beside them are not a mode
either: that is a single-to-multi conversion that stopped part-way, leaving orphaned section
roadmaps. Treat it exactly as SKILL.md's rule 9 treats an index and a `docs/ROADMAP.md` coexisting —
**stop and ask** whether a conversion was interrupted and which state is authoritative, before
writing anything. Never read such a project as having no roadmap: it would re-ask single-vs-multi,
and a "single" answer regenerates a `docs/ROADMAP.md` on top of features already built and verified.
The recovery is `--rollback` on the conversion script (index-phase.md), which reverses it exactly.

That glob is a filename pattern, not a proof. A `docs/ROADMAP-*.md` carrying no feature entries, no
coverage table and no execution-order block is some other document that happens to match the shape —
proceed, and record having checked rather than skipping the check silently.

Also locate the project's conventions doc if one exists (`CLAUDE.md`, README, contributing guide) —
Phase 2 loads it to keep naming and stack choices consistent with the rest of the project.

### New scope arriving at a project that already has a roadmap

Once a project is running, this is the ordinary case rather than the exceptional one: a wave of new
work — a fresh set of gaps from a 0c re-scan, a new epic, a batch of fixes — arriving at a roadmap
whose features are already built. Every wave after the first lands on this fork, so expect it to
recur.

**Two dispositions, and the choice is the user's — ask, never infer:**

1. **Extend the existing roadmap.** Right when the new scope is small and continuous with what is
   already there — a few features, same subject. Phase 2's "When to re-run, and what is frozen" then
   governs: new scope appends after the frozen block.
2. **Give the wave its own section.** Right when it is a distinct batch of work. Each wave becomes
   its own `docs/ROADMAP-<slug>.md`, with its own build order, its own coverage table and its own
   loop.

**Record the answer, whichever it is** — one plain line immediately under the H1 of the file the wave
lands in, above `## Status`, in the same place and shape as Step 8's size record:

```
wave recorded (as of <YYYY-MM-DD>): extended in place — <reason>
wave recorded (as of <YYYY-MM-DD>): own section `<slug>` — <reason>
```

**Why this line exists, and it is not bookkeeping.** Until it did, this was the only decision of its
weight that left no trace: the size question records its answer, this one did not, so a run that
*asked* and a run that *inferred* produced byte-identical output. Nobody could tell them apart
afterwards — not a reviewer, not the next run, not a test. Rule 1 forbids deciding an ambiguity in
silence, and a decision recorded nowhere is indistinguishable from one taken in silence, whatever
actually happened in the conversation.

It earns its line twice over: the next wave lands on this same fork and the previous answer is the
most useful thing to know, and a reader six months later opening a section roadmap can see why it is
a section at all.

**Why the choice matters — and this part has to be said, because it is not obvious.** A roadmap costs
what is *loaded*, not what is written, and the `/loop` prompt names one roadmap as the spec source
for **every** feature it builds (handover-prompt.md Step 10), so a roadmap of N features is re-opened N
times. A section already marked DONE is never loaded *whole* again: the seed's Step 3 counts it from
that section's `.txt` and from each feature's own `validation.md`, never by re-reading the roadmap
body. Point lookups into that body do still happen — Step 2 tests question-only features by their
`discharge:` marker and the `## Open Questions` roll-up, and Step 9 sweeps the target roadmap's
body — but a lookup is not a load. The economic point is what matters here: the body of a finished
roadmap never enters the per-feature context the loop builds. Extending forever therefore puts
every past wave inside the context of every future feature. The number: roughly 200-250 tokens per
feature, counting its entry, its coverage-table row, its `## Expected Gray Areas` lines and its
matching `## Open Questions` roll-up entry — so decompose-phase.md's ~3,000-token
sanity check fires at around 12-15 features. The loop path grows fastest of all: handoff-seed.md
Step 9 requires every open question closed before the loop is handed over, and answered entries
stay — never deleted (decompose-phase.md Step 8) — so every loop leaves a full set of them in the
file for good.

**If the project is single-section today, choosing (2) means converting it.** Follow index-phase.md's
"Converting a single-section project to multi-section" — and never leave `docs/ROADMAP-INDEX.md`
sitting beside a surviving `docs/ROADMAP.md`. SKILL.md's rule 9 treats the two coexisting as a
contradiction: the next run stops and asks which one is authoritative before touching anything.

This fork is one of **two** sanctioned exits from rule 9's "already fixed the mode — continue in it"
clause; the other is the user asking for the shape change outright, with no new wave, which the mode
exception above already allows and `index-phase.md`'s conversion section lists as its second trigger. The mode changes here because the user explicitly asked for it at this fork — never by
inference, and never because the roadmap grew large. Size is the argument *for asking*, never the
authority to switch on your own.

Conversion changes no feature name. Names and their relative order freeze on the **existence** of
`.specs/features/<name>/`, not on which file the feature is listed in
(decompose-phase.md, "When to re-run, and what is frozen") — so moving an entry into a section
roadmap leaves everything already built untouched. What the conversion *does* invalidate is the
Handoff pointer, which names files by path; index-phase.md's procedure carries the repair.

---

## 0b — Interview Mode (no source, no clear idea yet)

**Trigger:** the user has no document and says something like "I don't know what to build yet",
"help me plan this from scratch", or "plan product".

### Step 0 — Reuse and overwrite checks (interview)

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

### Step 0 — Reuse and overwrite checks (brownfield)

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
