# How Spec-Driven Roadmap Works

*A plain-language guide for humans. If you want the exact rules the skill follows, read
[`SKILL.md`](../SKILL.md) instead — this page is the friendly version.*

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

It writes your answers into `docs/PROJECT.md` for you — you never write this file by hand — and
then decomposes it, same as path A.

### C — "I have code, but nothing describing what it does"

Say *"map this codebase into a roadmap source"*. The skill checks whether your build skill (or the
`codenavi` skill) already has a codebase map it can reuse; if not, it does a light scan — just
enough to know what already exists and what's likely missing, not a deep architecture audit. It
writes `docs/CODEBASE-SUMMARY.md`, asks you what you actually want to add next, and decomposes
from there.

## One more question it asks, regardless of path

**One roadmap, or several?** For a small-to-medium project, one flat list
(`docs/ROADMAP.md`) is simpler. For a large system with real internal boundaries, splitting into
several roadmaps (`docs/ROADMAP-INDEX.md` + one file per section) lets you reason about — or build
— each part somewhat independently. The skill presents the trade-off and asks; you don't have to
decide this before you start.

## What you get, on disk

| File | When |
|---|---|
| `docs/ROADMAP.md` + `docs/roadmap.txt` | Always (single-roadmap mode) |
| `docs/ROADMAP-INDEX.md` + one `ROADMAP-<slug>.md`/`roadmap-<slug>.txt` per section | If you chose multiple roadmaps |
| `docs/PROJECT.md` | Only if you went through the interview (path B) |
| `docs/CODEBASE-SUMMARY.md` | Only if it mapped your codebase (path C) |
| `.specs/STATE.md` (one line updated) | Only if your build skill is confirmed/installed — this is the handoff |

The roadmap file itself contains, per feature: an objective, what it depends on, an honest task
estimate (≤8 tasks — if a feature needs more, it gets split), which "tricky" dimensions are
present (auth, persistence, external calls, etc.), and any open question it couldn't answer for
you. It closes with a coverage table proving nothing was missed.

## A real example

Given a two-paragraph PRD for a tiny shared task tracker with no auth details specified, one run
produced this (trimmed):

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

Notice it didn't guess how team membership works — the PRD never said, so it flagged it as an
open question and **refused to hand off the first feature** until that gets answered. That's by
design: it never decides something ambiguous on your behalf.

## What happens next

Once the roadmap is ready and your build skill is installed, the skill confirms that the planning
work is finished and asks **how you want to build it**. Two options:

**A — one feature at a time.** You get the command for the next feature only, run it, and come back
when it passes:

```
specify feature `tt-create-task` — spec source: docs/ROADMAP.md
```

**B — the whole roadmap in one loop.** You get a prompt that starts with `/loop` (your CLI's own loop
command — Claude Code, Cursor and OpenCode all have one) and doesn't stop until every feature in the
backlog is verified. Because a loop runs unattended with nobody to ask, this option requires a
roadmap with **zero open questions** — so the skill first reads the whole roadmap for gaps,
interviews you until every open question is answered, writes the answers back, then re-reads the
files from disk to confirm nothing is left open. Only then does it hand you the prompt.

⚠️ **Either way, run that prompt in a new chat session, with clean context** — not in the session
that generated the roadmap. The skill will tell you this too. The build skill re-reads everything it
needs from `.specs/STATE.md` and the roadmap files on disk; reusing the planning session just risks
it working from remembered conversation instead of the written files, and starts the build with the
context budget already spent.

That prompt is the last thing this skill does. From there, the whole build cycle — spec, design,
tasks, implementation, verification — belongs entirely to your build skill (`tlc-spec-driven` by
default). Even in loop mode, it's your CLI driving that skill; this one has already stopped. It
won't intervene again until you ask it to generate or refresh a roadmap.

## What it deliberately does *not* do

- It never writes `spec.md`, `design.md`, `tasks.md`, or application code.
- It never marches through features on its own — no auto-advancing. It can *write you* a `/loop`
  prompt, but running it is your CLI's job, in your session, after this skill has stopped.
- It never guesses an ambiguity — it asks, or records it as an open question and blocks the
  handoff until it's resolved.
- It never re-derives what another skill already mapped — if your build skill (or `codenavi`)
  already documented the codebase, it reuses that instead of scanning again.

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
Say so — "add this new section to the roadmap" or similar. It reuses what's there instead of
starting over, and never renames or reorders features that are already built.
