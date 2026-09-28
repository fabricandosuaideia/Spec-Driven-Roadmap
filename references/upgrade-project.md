# Upgrading a Project That Already Uses This Skill

A project whose roadmap an older version generated gets nothing from a newer one until two things
happen: the newer version is installed there, and its seed runs again. This file is the route for the
second, and everything around it an agent can do by itself — so the user can ask for it in one
sentence (*"upgrade this project"*, *"bring this project up to date with the skill"*, or
`/spec-driven-roadmap upgrade this project`) instead of following a checklist.

## What this route does not do

**It does not install this skill.** A run cannot replace the files it is reading. If the user asked
to reinstall, that happens before this route, outside it — re-running the installer for a plain
install, `/plugin update` for a plugin — and an agent may run the installer command itself when the
user asked for it. The version this run announces (SKILL.md, "Version and model") is what is on
disk; when the user expected a newer one, say so and stop, rather than upgrading a project with the
old rules.

**It never regenerates the roadmap.** Feature names, their order and every answer already recorded
are frozen (decompose-phase.md, "When to re-run, and what is frozen"). A roadmap written before a
field existed stays valid: `scripts/feature-brief.py` derives what is missing, the risk tier included.

**It never edits a file the user owns** — their `CLAUDE.md` above all — without a yes in this
conversation.

## Precondition

The project has `docs/ROADMAP.md` or `docs/ROADMAP-INDEX.md`. Without either there is nothing to
upgrade: say so, and offer the normal first run (Phase 0).

## Steps

1. **Baseline the cost, before anything changes.** If `docs/process/cost-baseline.json` does not exist,
   run `python3 <this-skill-dir>/scripts/measure-agents.py --project <project-root> --save-baseline
   docs/process/cost-baseline.json` and report its headline in two or three lines: the token-class
   shares, the three most expensive roles, the retry share. If it exists, run the same script with
   `--baseline docs/process/cost-baseline.json` instead and report the comparison. Exit `2` means the
   project has no Claude Code transcripts: say so and continue — there is simply nothing to compare
   against later. This is the only step that makes a later saving provable, which is why it comes
   first.
2. **Lint what is there.** Run `python3 <this-skill-dir>/scripts/check-roadmap.py --root <project-root>`
   and report failures and warnings as questions for the user, as SKILL.md's "Checking an existing
   roadmap" says. Fix nothing here.
3. **Note the size of what agents are pointed at**: the bytes of `<STATUS-PATH>` (handoff-seed.md Step
   6's table) and of each `docs/ROADMAP*.md`. The report compares them afterwards.
4. **Run the seed** — handoff-seed.md Steps 1-7, entering by its third trigger (artifacts brought up to
   date). It rewrites `## Status` through `scripts/status-block.py`, which moves whatever older runs
   wrote into it — narrative, `###` sub-headings — to `docs/roadmap-history.md`, verbatim; and it
   rewrites the Handoff in the confirmed downstream skill's schema unless work is in flight.
5. **The bridge lines.** Read the project's `CLAUDE.md` (or the file its agent auto-loads). If it holds
   bridge lines an earlier version offered — lines that send an agent to read a `docs/ROADMAP*.md`
   section before specifying a feature — show the current lines (handover-prompt.md, "Optional
   bridge", with its paths resolved for this project's mode) beside them and offer to replace the
   old block with the current one as a whole; the number of lines differs between versions. Edit only on the user's yes; otherwise leave the
   file alone and say what the old lines cost: every agent in the project loads that file on every
   turn, and they send each builder to a whole roadmap file.
6. **Continue into Steps 8-10** when Step 7's exit list allows — the user chooses A, B or C as on any
   seed; B writes the sub-agent definitions, C writes and confirms `docs/process/pipeline.json`.
   When Step 7 ends the procedure (work in flight, nothing left to build), end there too.

## Report

In the user's language, short: the version now on disk; the baseline's headline (or that none could
be taken); what the lint asked; `<STATUS-PATH>` bytes before and after, and that the old text is in
`docs/roadmap-history.md`; what happened to the bridge lines; which option they chose, if any. Then
the one step that is theirs: once the next features are built, ask *"measure my agent cost"* again —
the comparison against the baseline is the only evidence the upgrade saved anything. When Step 10
ran, its own output — the prompt block and the session warning — closes the report verbatim; the
report never replaces it with a paraphrase.
