# How Spec-Driven Roadmap Works

*A plain-language guide for humans. If you want the exact rules the skill follows, read
[`SKILL.md`](../SKILL.md) for the map and [`references/`](../references/) for the procedures
themselves — where those two disagree, the reference file wins. This page is the friendly version.*

*Not sure which version you have installed? See
[**Which version do I have?**](../README.md#which-version-do-i-have) in the README.*

Other languages: [Português](HOW-IT-WORKS.pt-BR.md) · [Español](HOW-IT-WORKS.es.md)

## In one sentence

This skill figures out **what to build and in what order** — it never writes code, specs, or
tests. Think of it as the step that happens *before* you hand a feature to your build skill
(`tlc-spec-driven` by default): it turns whatever you have — a document, an idea, or an existing
codebase — into an ordered backlog, then gets out of the way.

## How to trigger it

Two ways, and both work the same:

**1. Just talk to Claude in plain language.** No special syntax needed. Any of these will trigger it:

- "generate a roadmap from docs/PRD.md"
- "plan product"
- "I don't know what to build yet, help me figure it out"
- "map this codebase into a roadmap source"
- "decompose this architecture into features"

**2. Use the slash command**, if you'd rather be explicit:

- Installed as a plain skill (the `curl`/`install.ps1` method): `/spec-driven-roadmap`
- Installed as a plugin (`/plugin install`): `/spec-driven-roadmap:spec-driven-roadmap`

Either way, once it starts, you're just having a conversation — answer its questions and it does
the rest.

## The three ways to start (pick based on what you already have)

You never need to prepare a file in advance. Say what's true for you, or just start talking and it
will ask.

### A — "I already have a document"

You have a PRD, an architecture doc, a set of ADRs, or a flowchart export. Say something like
*"generate a roadmap from docs/PRD.md"*. The skill reads it, asks a couple of confirming questions
(which build skill you're using, whether you want one roadmap or several), and decomposes it.

### B — "I have nothing written down, and I'm not even sure what to build"

Say *"plan product"* or *"I don't know what to build yet"*. The skill interviews you — one
question at a time, never a wall of questions at once:

1. What are you building?
2. Who is it for, and what problem does it solve?
3. What's the smallest useful version?
4. What's explicitly out of scope for now?
5. Any hard constraints? *(optional)*
6. What tech stack, if you already know? *(optional)*

**It stops as soon as your vision, your users and the MVP boundaries are clear enough to decompose
from** — so not every run asks all six, and it skips anything you already answered earlier in the
conversation. Brief answers are fine; this document is allowed to be thin. It writes your answers
into `docs/PROJECT.md` for you — you never write this file by hand — then decomposes it, same as A.

### C — "I have code, but nothing describing what it does"

Say *"map this codebase into a roadmap source"*. The skill checks whether your build skill (or the
`codenavi` skill) already has a codebase map it can reuse; if not, it does a light scan — just
enough to know what already exists and what's likely missing, not a deep architecture audit.

Then, in this order: it asks you directly what you want to add or change — a backlog is never
inferred from tech-debt observations, so that answer is its only source — puts two lists **in chat**
for you to correct (**Capabilities Already Built** and **Gaps / Likely Next Work**), and only once
you confirm them writes `docs/CODEBASE-SUMMARY.md`. Correcting those lists is worth the minute:
anything mis-filed as already built is excluded from the roadmap permanently, and the coverage table
can't catch it — the unit was never enumerated in the first place.

## One more question it asks, regardless of path

**One roadmap, or several?** For a small-to-medium project, one flat list
(`docs/ROADMAP.md`) is simpler. For a large system with real internal boundaries, splitting into
several roadmaps (`docs/ROADMAP-INDEX.md` + one file per section) lets you reason about — or build
— each part somewhat independently. The skill presents the trade-off and asks; you don't have to
decide this before you start. One exception: if the project already has a `docs/ROADMAP-INDEX.md`
or a `docs/ROADMAP.md`, the mode was fixed earlier and the run continues in it — it is not re-asked
at the start of the run. It comes back only if you ask to change shape (the FAQ below covers that
fork), or if the roadmap has grown big enough that the skill raises the question again; either way
the answer is yours, and "keep it as it is" is a valid one. If *both* files exist, that is a
contradiction — the run stops and asks you which one is authoritative.

## What you get, on disk

| File | When |
|---|---|
| `docs/ROADMAP.md` + `docs/roadmap.txt` | Always (single-roadmap mode) |
| `docs/ROADMAP-INDEX.md` + a `ROADMAP-<slug>.md`/`roadmap-<slug>.txt` pair per decomposed section | If you chose multiple roadmaps |
| `docs/PROJECT.md` | Only if you went through the interview (path B) |
| `docs/CODEBASE-SUMMARY.md` | Only if it mapped your codebase (path C) |
| `.specs/STATE.md` (`## Handoff` body rewritten) | Only with something to seed *and* a confirmed build skill whose schema is readable — four skip cases, below |

The roadmap file itself contains, per feature: an objective, what it depends on, an honest task
estimate (≤8 tasks — if a feature needs more, it gets split), which "tricky" dimensions are
present (auth, persistence, external calls, etc.), and any open question it couldn't answer for
you. It closes with a coverage table proving nothing was missed.

**Decomposition is lazy.** In multi-section mode only the section you asked for gets its
`.md`/`.txt` pair; the others sit in the index as `NOT YET DECOMPOSED`, and the skill just reports
the next action — *"decompose section `<slug>`"*. That's deliberate: a section decomposed weeks
before it's built goes stale. Adding a section to the index never triggers a handoff either, because
a section with no `.txt` has no build order to pick a target from. And if you run the project in
waves, each wave can be its own section — the skill asks which way to go as the new scope arrives.

**Four things skip that last write**, and the skill records which one on the `Handoff` line of its
own Status block: no downstream skill installed; one confirmed but its handoff schema unreadable;
real work in flight; or nothing left to seed because every decomposed feature is done.

**`docs/` is fixed, not configurable.** And the `.txt` files are machine-read: feature names only,
one per line, no comments and no status markers. The seed counts those lines to compute progress, so
anything else there would inflate the total and never match a feature. The human-readable build
order — increment markers and all — lives in the roadmap `.md` beside it.

## An illustrative example

Given a two-paragraph PRD for a tiny shared task tracker with no auth details specified, an
illustrative run produces something shaped like this (trimmed):

```markdown
# TinyTasks — Roadmap

### tt-create-task
- Objective: Let a team member create a task with a title and an assignee.
- Depends on: —
- Task estimate: 5
- Open questions:
  - How are teams and users (task assignees) identified for v1 — is there a
    pre-existing auth/team system, or does one need to be built here? — status: open

### tt-complete-task
- Depends on: tt-create-task
...

## Coverage
| Scope-unit | Disposition |
|---|---|
| S1 | tt-create-task |
| S2 | tt-complete-task |
| S3 | tt-list-open-tasks |
`uncovered: none (0 deferred, 0 pre-existing, listed above)`
```

Notice it didn't guess how team membership works — the PRD never said, so it recorded it as an open
question instead. That's by design: it never decides something ambiguous on your behalf.

**The handoff still gets written** — whenever there was one to write at all (see below). That
question is copied into the Handoff's `Blockers` field, the `Next step` field points at answering it
rather than at specifying the feature, and the run reports this as **seeded but blocked**, never as
"not seeded". What's held back is only the copy-and-paste start command, so you aren't handed one
that would start a feature that can't start cleanly.

## The questions it asks before finishing

Before closing the roadmap, it runs one short sweep of **project-wide decisions** — the ones that
would otherwise get re-decided, differently, inside every feature: soft or hard delete, the auth
model, what happens on a partial failure, retry and idempotency policy, what must never be logged.
It only asks about themes your roadmap actually touches, and each comes with a recommended default
you can accept in a word. The outcome goes into a `## Cross-Cutting Decisions` block that every
feature is then built against.

**Expect a ledger, not a list of answers.** That block carries exactly one row per theme in the
rubric — none absent, none twice — and a row reads in one of four ways: the decision plus a line of
reasoning; `N/A because <reason> (as of <roadmap>)` when nothing decomposed so far touches it; `not
decided`, pointing at the open question it became; or `deferred to feature <name>` when the question
got its own feature in the build order. So `N/A` rows are the block working, not something missing —
completeness is its whole value, since your build skill reads it before every gray-area discussion,
so "not listed here" has to mean "this project has no such theme" and never "we forgot".

An unanswered theme lands in two places — the `not decided` row, plus an open question carrying an
`affects:` line naming what the answer would reach. That pair holds up the start command for the
features it actually reaches; answering it releases them.

It deliberately **does not** ask about everything. Decisions that live inside a single feature —
layout, response shape, error wording — are left to your build skill, which asks them later with
the actual code in front of it and answers them better for it. Those are listed in an
`## Expected Gray Areas` block so you can see what's coming without having to decide it now.

## What happens next

**The "how do you want to build it" question only comes up when something was actually seeded and
your build skill is confirmed.** Otherwise the run ends with the report and the reason. Six endings
stop before the question: only Phase 1 ran, so a section is indexed but not decomposed; a roadmap
name drifted from a directory already on disk; real work is in flight; every decomposed feature is
already done; no build skill is installed; or one is, but its handoff schema couldn't be read. In
all six the roadmap is finished and usable as it stands — what's missing is the handoff, not the
plan.

**If no build skill is installed, it generates the roadmap anyway.** Phases 1 and 2 write only to
`docs/`, so you get the whole thing, and **nothing at all is created under `.specs/`** — not even an
empty `STATE.md`, since a guessed shape is worse than an absent file: your build skill's resume
would treat it as a stale snapshot to reconcile. The reason goes durably onto the `Handoff` line of
the Status block, so a later run can tell "never seeded" from "seeded and since overwritten".
Install the skill, ask for the seed again, and the chain completes **without re-running Phase 2**.

When there is a target and a confirmed skill, it says the planning work is finished and asks **how
you want to build it**. Two options:

**A — one feature at a time.** You get the command for the next feature only, run it, and come back
when it passes:

```
specify feature tt-create-task — create it at `.specs/features/tt-create-task/` using that exact
directory name. Spec source: docs/ROADMAP.md. Read docs/ROADMAP.md `## Cross-Cutting Decisions`
before Discuss and treat it as settled — do not re-decide what it answers.
```

**B — a whole roadmap in one loop.** You get a prompt that starts with `/loop` (your CLI's own loop
command — Claude Code, Cursor and OpenCode all have one) and doesn't stop until every feature in that
roadmap is verified. Because a loop runs unattended with nobody to ask, this option requires a
roadmap with **zero open questions** — so the skill first reads the whole roadmap for gaps,
interviews you until every open question is answered, writes the answers back, then re-reads the
files from disk to confirm nothing is left open. Only then does it hand you the prompt. Those
answers stay in the file for good, as the record of what was decided and why — worth having, and
also the single biggest reason a roadmap grows from one wave to the next.

**What option B trades away is not "no questions left".** The loop doesn't eliminate the gray areas
the skill deliberately left to your build skill — it decides each one with the default and **writes
it down**, with the rationale, in that feature's `.specs/features/<name>/spec.md`, under its
assumptions and open questions section; reviewing those sections afterwards is the expected step,
not extra work. The count in that roadmap's `## Expected Gray Areas` block sizes the trade up front,
and it's a **floor, not a ceiling** — it holds only what the planning sweep turned up, while each
feature's own discussion generates more on top of it. Nor is this a workaround: routing a declined
gray area into the spec with the agent's default and rationale is `tlc-spec-driven`'s own
documented fallback.

**One loop covers one roadmap.** If you split your product into section roadmaps, the loop builds the
section you're on — not the whole product. That's deliberate: what one section hands another stays
provisional until that section is actually built, so the gap between two sections is where the plan
meets what shipped. It's a checkpoint worth keeping a human in. When a section finishes, you come
back, the skill re-seeds, and the next section gets its own loop.

⚠️ **Either way, run that prompt in a new chat session, with clean context** — not in the session
that generated the roadmap. The skill will tell you this too. In a fresh session **the prompt itself
is the channel**: your build skill re-derives what it needs from the paths in that prompt and the
roadmap files on disk. `.specs/STATE.md` is read on a later `resume work` — that's what the Handoff
is for, not a fresh start — which is why the prompt must be pasted intact, exact directory name and
all. Reusing the planning session just risks the agent working from remembered conversation instead
of the written artifacts, and starts the build with the context budget already spent.

That prompt is the last thing this skill does. From there, the whole build cycle — spec, design,
tasks, implementation, verification — belongs entirely to your build skill (`tlc-spec-driven` by
default). Even in loop mode, it's your CLI driving that skill; this one has already stopped. It
won't intervene again until you ask it to generate or refresh a roadmap.

## How it knows what's already built

It never takes anyone's word for it, and the presence of a file proves nothing. For each name in the
build order it reads `.specs/features/<name>/validation.md`, running your build skill's gate script
if that skill actually ships one **on disk** — it checks the disk, not the documentation, because a
skill's script set changes between releases and an install lags them — and otherwise reading the
report by exactly the same rules. A **PASS with no `path.ext:NN` evidence citation counts as not
done**, as does an unfilled `[PASS | FAIL]` template. Question-only features are the one exception:
producing no code, they're discharged by their question being answered — or by a `context.md`
existing for them. And when real work is in flight — something completed or in progress in the
Handoff, or the feature named in the Handoff has a `spec.md` on disk and no real PASS — it **does
not rewrite `.specs/STATE.md` at all**: it refreshes its own Status block, names the feature in
flight, and stops there. None of that fires once the feature the Handoff names has a real PASS —
finished and then paused is not work in flight.

## What shows up in the file and might surprise you

- **A feature that builds nothing.** When one unresolved question gates several later features, it
  can get a small feature of its own whose only job is getting that answer. It carries the literal
  line `discharge: no code — answered open question or context.md`, verbatim, because three separate
  consumers key off it: the seed's done-test, its target pick, and the loop prompt's skip list.
- **A Status block at the top of your roadmap** (or of the index, in multi-section mode): counts,
  the remaining build order, the next feature, and whether the handoff was written — or why not.
  Regenerated on every seed, so never hand-edit it.
- **English inside a non-English roadmap.** Prose comes out in the language you're working in, but
  feature names, prefixes, slugs, filenames and **every generated heading** stay English: they're
  machine-read keys, path components and directory names, and translating one breaks the handoff,
  the `.specs/features/<name>/` directories, or a cross-file lookup.

## What it deliberately does *not* do

- It never writes `spec.md`, `design.md`, `tasks.md`, or application code.
- It never marches through features on its own — no auto-advancing. It can *write you* a `/loop`
  prompt, but running it is your CLI's job, in your session, after this skill has stopped.
- It never guesses an ambiguity — it asks, or records it as an open question. That question holds
  back the **target feature's** start command, not the backlog: a feature's own question blocks that
  feature, and a project-wide one blocks only when its `affects:` line reads `all` or names the
  target. Blocking wider would freeze the whole backlog behind one project-wide question.
- It never re-derives what another skill already mapped — if your build skill or `codenavi` already
  documented the codebase, it reuses that instead of scanning again. Whether your build skill has
  such a step is **version-dependent** (`tlc-spec-driven` v2 had one, v3.x does not), so it detects
  what's actually installed rather than assuming a path.

## FAQ

**Do I need to create any file before using this?**
No. Not even the roadmap — that's what it produces. If you already have a document, it's optional
but helpful; if not, it interviews you instead.

**Is the roadmap the only required file?**
It's the only one the whole chain actually needs to get moving — and even that isn't strictly
required by your build skill (it can specify a feature from a plain conversation with no prior
file). The roadmap's value is deciding *what* and *in what order* upfront, instead of improvising
feature by feature.

**How do I know whether this skill or my build skill is currently active?**
By what it's doing: if it's deciding what to build and in what order, that's this skill. The
moment you see `spec.md`, `design.md`, `tasks.md`, or actual code being written, that's your build
skill — this one has already stepped back.

**What if I already have a roadmap and just want to add more to it?**
Say so — "add this new section to the roadmap" or similar; it never regenerates what's there. Two
ways to land new scope exist, and the skill puts the choice to you as that scope arrives.

**Extend the roadmap you have** — right for a small, continuous addition. Feature names **and their
relative order freeze the moment a `.specs/features/<name>/` directory exists** — not at a passing
verification, so a half-written spec or a failed run freezes its feature too. New scope appends after
that frozen block; an obsolete feature is marked superseded in place, never deleted, never renamed.

**Give the new wave its own section** — right when the new work is a distinct batch rather than a few
more items. The project converts to multi-section: what you have becomes one section roadmap, the new
wave becomes the next, and an index orders them. The exact procedure is
`Converting a single-section project to multi-section`, in `references/index-phase.md`. The
conversion is done by a small Python 3 script that ships with the skill, so a machine with no
`python3` cannot run it.

Why the choice matters: a roadmap only costs you what gets loaded, and in loop mode that one file is
named as the spec source for **every** feature the loop builds — so one that grows wave after wave is
read back into the context of all future work, waves that closed months ago included. A finished
section is never loaded whole again: progress is counted from its `.txt` and each feature's
`validation.md`, while pinpoint reads into its body — the `discharge:` test, the `## Open Questions`
roll-up — still happen. What never happens is the whole body landing in the context of every feature
the loop builds. Concretely: one feature costs the roadmap roughly 200-250 tokens, so the skill
flags the size at around 2,000 — naming how many features are left before a split is needed — and
re-raises the one-or-several question past roughly 3,000, about 12-15 features. Converting renames
**files, not features**, so nothing already built is affected — with one caveat: the handoff pointer
in `.specs/STATE.md` names files by path, so it goes stale and the skill re-runs its seed to repair
it. If a feature is mid-build when you convert, that repair has to wait until it passes, and the
skill tells you so.
