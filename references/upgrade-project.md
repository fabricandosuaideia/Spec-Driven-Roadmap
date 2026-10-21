# Upgrading a Project That Already Uses This Skill

A project whose roadmap an older version generated gets nothing from a newer one until two things
happen: the newer version is installed there, and its seed runs again. This file is the route for the
second, and everything around it an agent can do by itself — so the user can ask for it in one
sentence (*"upgrade this project"*, *"bring this project up to date with the skill"*, or
`/spec-driven-roadmap upgrade this project`) instead of following a checklist.

## What this route does not do

**It does not install this skill from inside the run.** A run cannot replace the files it is reading.
The reinstall happens before the steps below — re-running the installer for a plain install,
`/plugin update` for a plugin — and an agent may run the installer command itself once the user has
said yes to Step 0. The version this run announces (SKILL.md, "Version and model") is what is on
disk; when the user expected a newer one, say so and stop, rather than upgrading a project with the
old rules.

**It never reinstalls over a local change without a yes in this conversation.** A project that needed
something before a release existed sometimes patched its own copy of the skill (a key that nothing else
reads, a prompt it tightened). A plain install replaces that copy and the setting that depended on it
stops working with no message. Step 0 finds those files first.

**It never regenerates the roadmap.** Feature names, their order and every answer already recorded
are frozen (decompose-phase.md, "When to re-run, and what is frozen"). A roadmap written before a
field existed stays valid: `scripts/feature-brief.py` derives what is missing, the risk tier included.

**It never edits a file the user owns** — their `CLAUDE.md` above all — without a yes in this
conversation.

## Precondition

The project has `docs/ROADMAP.md` or `docs/ROADMAP-INDEX.md`. Without either there is nothing to
upgrade: say so, and offer the normal first run (Phase 0).

## Steps

0. **Look before replacing.** The first command changes nothing: run the installer in check
   mode, from the project root (`curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh
   | bash -s -- --check --diff`; on Windows download `install.ps1` and run it with `-Check -Diff`). It prints
   the version installed, the version available and, when the installed copy is not the release it claims to
   be, one line per file the project changed (`modified` or `added`) and, for each modified one, what it changed
   against that release. Three outcomes:
   - **The copy is unchanged and already current.** Nothing to install; go to Step 1.
   - **The copy is unchanged and older.** There is nothing in it to lose, so the person's request to upgrade is
     the yes: say which version it goes to, and run the installer with `--force` before Step 1. Then re-read
     SKILL.md's version: it is the new one. (The "Next steps" the installer prints are for a first install: do not
     relay them.)
   - **The installer lists local changes.** Stop and show them. For each file, find out what it was for
     — the diff the installer printed is the evidence (`git log -p` on the file rarely helps: a project usually
     commits the whole copy at once), and a `grep` of the installed copy for the key or name the patch touched
     says whether anything in it ever read that value — and say, in the user's language, whether this version covers it: `references/upgrade-notes.md` names the keys that
     came from such patches (`postMerge`, `models`) and the one that did not (`manager.passes`). Then ask:
     reinstall and lose the rest, keep their copy and stop, or bring what is missing into the skill's own
     repository first. **Reinstall only on a yes** (then run the same installer with `--force`; `-Force` for
     `install.ps1`; the "replaces them" warning it prints is not an approval, only the person's yes to *those
     files* is), and say what was lost in the report. After a reinstall, `<this-skill-dir>` is the project's installed copy
     (`.claude/skills/spec-driven-roadmap`), whose files are now the new version.
   When the installer could not compare (no network, no archive of that version), say so and treat the copy as
   possibly changed: ask before replacing it. If the project tracks its copy of the skill in git, the reinstall
   leaves those files modified: offer to commit them on their own, and leave the commit to the person.
1. **Baseline the cost, before the project's agents run again.** (It reads the project's transcripts, not the skill,
   so doing it after Step 0's reinstall is right: only the new script reports time.) If `docs/process/cost-baseline.json` does not exist,
   run `python3 <this-skill-dir>/scripts/measure-agents.py --project <project-root> --save-baseline
   docs/process/cost-baseline.json` and report its headline in two or three lines: the token-class
   shares, the three most expensive roles, the retry share. If it exists, run the same script with
   `--baseline docs/process/cost-baseline.json` instead and report the comparison. Exit `2` means the
   project has no Claude Code transcripts: say so and continue — there is simply nothing to compare
   against later. This is the only step that makes a later saving provable, which is why it comes
   first.
2. **Check `docs/process/pipeline.json` and tell the person what changed.** Skip it when the project has no
   `pipeline.json` (it never ran option C or manager mode). Otherwise:
   - run `python3 <this-skill-dir>/scripts/plan-pipeline.py --root <project-root> --check-config`. It lists every
     problem at once — a key this version does not read, a value it refuses — and what the file sets, and
     warns (without failing) about a script the config runs that is not in the project, with what that would do.
     Show each problem with the row of [upgrade-notes.md](upgrade-notes.md) that explains it (a warning has no
     row: explain it, and note when this upgrade is what turns an inert key into one that can stop a run), and fix a problem only with
     the person's word (a key from a patch is theirs to delete or to keep by asking for it upstream);
   - read upgrade-notes.md for the versions after the one in the `## Status` header, up to the one on disk: say what
     changes by itself, only the rows that have something to say, and **offer each new key once** with the price
     Step 10 of [handover-prompt.md](handover-prompt.md) gives it. When an offer depends on something you cannot
     measure here (the gate's length for `gateOrder`), say so and offer it with its condition. Offer `verifier` as
     `sensor` and `rounds`; name `survivor` only if the person asks to stop surviving mutants from refusing.
     Write into `pipeline.json` only the keys they say yes to. Never write `"confirmed"`, `"mergeGate"` or
     `"verifier.survivor"` on your own initiative.
3. **Lint what is there.** Run `python3 <this-skill-dir>/scripts/check-roadmap.py --root <project-root>`
   and report failures and warnings as questions for the user, as SKILL.md's "Checking an existing
   roadmap" says. Fix nothing here.
4. **Note the size of what agents are pointed at**: the bytes of `<STATUS-PATH>` (handoff-seed.md Step
   6's table), of `.specs/STATE.md` and of each `docs/ROADMAP*.md`. The report compares them afterwards.
5. **Run the seed** — handoff-seed.md Steps 1-7, entering by its third trigger (artifacts brought up to
   date). It rewrites `## Status` through `scripts/status-block.py`, which moves whatever older runs
   wrote into it — narrative, `###` sub-headings — to `docs/roadmap-history.md`, verbatim; and it
   rewrites the Handoff in the confirmed downstream skill's schema unless work is in flight, through
   the same script — which moves every older copy of the Handoff that runs kept in that file
   (`Handoff (superseded …)`, `Handoff addendum …`) to the same history, verbatim.
6. **The bridge lines.** Read the project's `CLAUDE.md` (or the file its agent auto-loads). If it holds
   bridge lines an earlier version offered — lines that send an agent to read a `docs/ROADMAP*.md`
   section before specifying a feature — show the current lines (handover-prompt.md, "Optional
   bridge", with its paths resolved for this project's mode) beside them and offer to replace the
   old block with the current one as a whole; the number of lines differs between versions. Edit only on the user's yes; otherwise leave the
   file alone and say what the old lines cost: every agent in the project loads that file on every
   turn, and they send each builder to a whole roadmap file.
7. **Continue into Steps 8-10** when Step 7's exit list allows — the user chooses A, B or C as on any
   seed; B writes the sub-agent definitions, C writes and confirms `docs/process/pipeline.json`.
   When Step 7 ends the procedure (work in flight, nothing left to build), end there too.

## Report

In the user's language, short: the version now on disk, and what the installer found (local changes and what
became of them); the baseline's headline (or that none could be taken); the config problems and the new keys
offered, with the answers; what the lint asked; `<STATUS-PATH>` and `.specs/STATE.md` bytes before and after, and that
the old text is in `docs/roadmap-history.md`; what happened to the bridge lines; which option they chose, if any. Then
the one step that is theirs: once the next features are built, ask *"measure my agent cost"* again —
the comparison against the baseline is the only evidence the upgrade saved anything. When Step 10
ran, its own output — the prompt block and the session warning — closes the report verbatim; the
report never replaces it with a paraphrase.
