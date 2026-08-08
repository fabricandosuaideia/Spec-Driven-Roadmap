# Changelog

Every released version of **spec-driven-roadmap**, newest first, with the commit that carries it.

A release is one number declared in three places — `metadata.version` in `SKILL.md`, `version` in
`.claude-plugin/plugin.json`, and `plugins[0].version` in `.claude-plugin/marketplace.json`. From
3.5.0 on, `scripts/bump-version.sh` writes all three at once and refuses to run when they already
disagree. Before that they drifted — see **Two contents under one label** and **Version drift**.

---

## 3.6.0 — 2026-08-08

**A project built in waves now has somewhere to put the next wave.** Re-running the skill on a
project that already had a roadmap left exactly one written outcome — *extend it* — so a user coming
back weeks later with a fresh batch of scope appended it to the same `docs/ROADMAP.md`, wave after
wave. That file then competes with the very loop it feeds: the `/loop` prompt names one roadmap as
the spec source for every feature it builds, so the whole thing is re-read once per feature. The
remedy already existed inside the skill — in multi-section mode the seed walks each section's
build-order `.txt` and never opens the body of a section it is not targeting — it was simply never
offered when a new wave arrived. Now it is.

- **Phase 0 asks instead of assuming.** When new scope reaches a project that already carries a
  roadmap, the re-run rule now puts the choice to the user: extend the current roadmap, or let the
  new scope become its own section. Extension used to be the only written outcome, which is exactly
  what made a wave-built project accumulate into one file. The single-vs-multi call itself is
  unchanged and still the user's (rule 9).
- **Phase 1 gained a conversion step, and it is a script.** `scripts/convert-to-multi.py` renames
  `docs/ROADMAP.md` and `docs/roadmap.txt` to their section names, writes a minimal
  `docs/ROADMAP-INDEX.md` carrying the `## Status` and `## Cross-Cutting Decisions` blocks with
  every path inside them rewritten, and strips both blocks from the renamed roadmap — in one
  operation, with `--dry-run` and a real `--rollback`. The slug is **derived**, as the longest
  leading hyphen-token run common to every feature name, never chosen: the slug and the feature-name
  prefix are the same string and those names are frozen. It aborts, touching nothing, on an existing
  index, an orphan section roadmap, a missing `.txt`, or a prefix it cannot derive.

  This started as a written procedure and shipped as a script because three rounds of review kept
  finding catastrophic paths in the prose: a rollback that silently restored nothing (`git checkout`
  does not reverse a staged `git mv`), a rollback that recreated `docs/ROADMAP.md` and then
  overwrote it — losing `## Cross-Cutting Decisions` entirely — and a prefix rule that split on the
  first hyphen and so handed `auth-core-*` features the slug `auth`, permanently. Writing it as code
  surfaced a fourth in the first test run: the block extraction stopped at the next `## `, which
  swallowed every `### <feature>` entry into the index. A procedure cannot be run against a test
  repository; this is why the completion gate in `tlc-spec-driven` is a script too.

  The safety net is a backup directory, not git — git recovery needs the files tracked *and* clean,
  which is exactly what a project is not right after Phase 0c wrote `docs/CODEBASE-SUMMARY.md`.
  `git mv` is still used when it is safe, and `--rollback` unstages it.
- **Both installers now ship `scripts/`.** They copied only `SKILL.md` and `references/`, so a
  runtime script would never have reached a user's disk. Maintainer tooling (`bump-version.sh`)
  deliberately stays in the repository.
- **Rule 9 gained a third contradiction.** Section roadmaps present with no `docs/ROADMAP-INDEX.md`
  beside them are an interrupted conversion: stop and ask, rather than reading the project as having
  no roadmap and regenerating over verified features. This is the only change to a non-negotiable
  rule in three releases, and it is additive — the other twelve are byte-identical.
- **Wave-shaped sections are explicitly legitimate.** A section does not have to be an architectural
  boundary; a wave of work is a valid one. It takes a slug on the same rule as any other section —
  short, mnemonic, kebab-case, prefixing every feature in it — and the edge back to the previous
  wave is labelled for what it is: temporal, existing because one wave was built first, drawn in no
  source. Phase 1 records which source resolved each edge, so this one is not dressed up as a
  dependency the source never stated.
- **The size sanity check warns before it fires.** It now speaks up as a roadmap approaches roughly
  2,000 tokens instead of only reacting once it is past 3,000, and it publishes what one feature
  costs — roughly 200-250 tokens across its ten fields, its coverage row, its Expected Gray Areas
  lines and its entry in the Open Questions roll-up. That puts the threshold around 12-15 features
  and makes it something a reader can check rather than take on faith.
- **Step 8 now names the loop as the path that grows fastest.** Option B is gated on every open
  question in that roadmap being closed first, and an answered entry is never deleted — so every
  loop leaves a complete set of answered questions in the file, permanently. That is said where the
  user chooses between the two prompts, not discovered three waves later.

**No decomposition rule changed.** What a feature is, and how features are sliced, ordered, covered
and named, is identical to 3.5.0. What changed is where a new wave of scope is allowed to land, and
what the skill tells you about the size of the file it lands in.

## 3.5.0 — 2026-08-07 — `c33f658`

**The skill now tells you which version you are running.** It never did, and that turned out to
matter. A user on 3.1.0 concluded the skill produced nothing worth running unattended — an accurate
reading of *that* version, since the `/loop` prompt did not exist before 3.2.0 — but no installed
file carried a version number anywhere, so there was no way to tell a stale install from a broken
skill. Everything here exists to close that gap.

- The skill **announces its own version** when it runs and **stamps it** into what it generates, so
  an artifact on disk says which version produced it.
- A **model and effort disclaimer**: the depth of the output depends on the model and reasoning
  effort the skill is run with, which is now stated instead of left as an assumption.
- Both installers **report the version they are installing** and say plainly when they are
  **replacing** an existing install rather than adding a new one.
- `guide/HOW-IT-WORKS.md` and its `pt-BR` and `es` variants: **statements that had gone out of date
  corrected**, plus **two entirely new sections** — how the skill knows what is already built, and
  what shows up in the file and might surprise you. The guide had fallen behind the skill over
  3.2.0 → 3.4.0.
- Outputs produced **before Step 8** now mention that a loop option exists, so a user who stops
  reading at the roadmap still learns the unattended path is there. Step 8 is unchanged and remains
  where the choice is made — it asks, and never defaults to the loop.
- This `CHANGELOG.md`, and `scripts/bump-version.sh` to keep the three declarations in step.

## 3.4.0 — 2026-08-05 — `80debaf`

*Fix the defects the gray-area batch introduced, and the ones it exposed.*

Four audits and an adversarial verification pass over 3.2.0 and 3.3.0 found 29 defects, then 11 more
in the fixes themselves. The load-bearing ones:

- A cross-cutting question could pass the "reaches beyond one feature" test and land in no feature's
  `open questions` field, which is the only place the Blockers gate looked — so the highest-stakes
  class of question could sit unanswered while the seed wrote `Blockers: none`. The Cross-Cutting
  Decisions block became a ledger with one row per rubric theme, and Blockers now checks three
  ordered sources.
- **The loop prompt could not terminate.** `<name>` read as a placeholder to resolve, pinning every
  iteration to feature one; the stop condition demanded a PASS that question-only features can never
  earn. The prompt now defines `<current-feature>` as a per-iteration variable and every consumer
  keys off a literal `discharge:` line.
- **A loop covers exactly one roadmap**, in both modes. Boundary contracts stay provisional until
  the producing section is built, so a loop crossing that seam builds against an invalidated plan.
- `install.ps1` globbed `-Path` on paths it built itself — a project path containing brackets was
  enough to delete an unrelated install while the script printed success. Every call is
  `-LiteralPath` now.
- `.claude-plugin/marketplace.json` was bumped 3.1.0 → 3.4.0, ending the drift described below.

## 3.3.0 — 2026-08-05 — `7954214`

*Pre-empt the gray areas the downstream Discuss cannot see.*

An unattended loop stalls on `tlc-spec-driven`'s Discuss, which fires for any feature with an
implicit dimension and is interactive by design with no "skip all". Phase 2 gained a step that
sweeps the downstream skill's dimensions rubric once at project scope, with a mandatory "N/A
because" escape. Answers land in a Cross-Cutting Decisions block; what fails the three-part test
lands in an Expected Gray Areas block, which blocks nothing. The seed's re-read pass became a
propagation check, capped at three rounds.

`.claude-plugin/marketplace.json` was **not** bumped and still read 3.1.0 after this release.

## 3.2.0 — 2026-08-04 — `d94aae5`

*Offer a loop prompt at handoff, gated on a gap-free roadmap.*

**This is the release that introduced the `/loop` prompt.** If you are on anything earlier, this is
the entry that matters: before it, the seed ended with a single `specify feature <target>` command,
and the word "loop" appeared in the skill only in the negative — *"never author, never loop"*,
*"Handoff Seed — One-Time, Not a Loop"*, *"no build loop, no auto-advancing"*. There was nothing to
run unattended, and no version number anywhere to reveal that.

The old Step 7 was split into four:

- **Step 7** reports the outcome and stops early only when there is genuinely nothing to hand over.
- **Step 8** asks which prompt the user wants. The choice is theirs; the loop is never the default.
- **Step 9** runs only for the loop path: a loop has nobody to ask, so every open question is
  interviewed closed first, written back to both the per-feature field and the roll-up, and re-read
  from disk before the roadmap is called clean.
- **Step 10** hands over the prompt and warns, on both paths, to run it in a **fresh session**.

`.claude-plugin/plugin.json` was bumped here; `.claude-plugin/marketplace.json` was not. That is
where the drift starts.

## 3.1.0 — 2026-08-04 — `c0d4fcd`

*Fix skill registration, align handoff with tlc-spec-driven v3.3.0, harden installer.*

- **Registration was completely broken.** The `SKILL.md` frontmatter was invalid YAML — an unquoted
  scalar containing `"Triggers: "` terminated the value early, so `name`, `description` and
  `metadata` were all discarded and the skill could never auto-trigger. The description was also
  1370 characters against a 1024 hard limit.
- The handoff was written against `tlc-spec-driven` v2's contract rather than the v3.3.0 that
  actually consumes it. Durable status moved to a Status block in `docs/`, since v3 overwrites its
  own Handoff section on every pause.
- The installer's overwrite prompt read from the pipe carrying the script, so every re-install
  silently printed "Installation cancelled" and exited 0.

**See the note below — two different contents were published under this number.**

## 3.0.0 — 2026-08-03 — `f5f836b`

*Add Interview Mode, Brownfield Mode, and a curl installer.*

Phase 0 became a router with three entry paths, so the skill no longer required a pre-existing scope
document. **Interview Mode** covers the greenfield case and produces `docs/PROJECT.md`; **Brownfield
Mode** covers an existing codebase and produces `docs/CODEBASE-SUMMARY.md`. Both feed the existing
pipeline unchanged. Adds `install.sh` for a curl-pipeable, git-free install.

---

## Two contents under one label — the 3.1.0 caveat

`c0d4fcd` set the version to 3.1.0. Three commits later, `7948cb1` — *"Fix regressions found by
verification, add Windows installer and plugin manifest"* — rewrote `SKILL.md`, all four files in
`references/`, and both installers (`install.sh` modified, `install.ps1` added), and **left the
label at 3.1.0**. `.claude-plugin/plugin.json` was created in that same commit already carrying
3.1.0.

`SKILL.md` plus `references/` is exactly what `install.sh` copies, so **two materially different
skills were published as 3.1.0**. The later one fixes, among other things, a backwards
`validate_state.py` contract that made the seed classify every feature as already verified. The six
other commits under the 3.1.0 label — `5479ce5`, `5f5e83b`, `e90b767`, `1d2c718`, `a590fa1`,
`8d9c789` — touched only the README files, `guide/`, `.gitignore` and the marketplace manifest, and
left the installed payload alone.

If you are comparing 3.1.0 against anything, compare commits, not version numbers.

## Version drift across 3.2.0 and 3.3.0

`.claude-plugin/marketplace.json` was added in `5479ce5` declaring 3.1.0, and was then the only one
of the three declarations that `d94aae5` (3.2.0) and `7954214` (3.3.0) forgot to touch. The
marketplace listing therefore advertised **3.1.0 through two entire releases** — including the one
that first shipped the `/loop` prompt — until `80debaf` corrected it straight to 3.4.0.

`scripts/bump-version.sh` exists for this. It reads all three declarations, **aborts when they
already disagree** instead of bumping over the evidence, rejects a version that is not valid semver
or not greater than the current one, and otherwise rewrites all three together.

## Tag policy

From 3.5.0 forward, every release gets exactly one **annotated** tag on the commit that carries the
bump:

```
git tag -a v3.5.0 -m "spec-driven-roadmap 3.5.0"
```

**A heading's hash is backfilled, never guessed.** An entry is written in the same working tree as
the release it describes, so the commit that carries it does not exist yet — the newest heading
carries its date and no hash, and the preamble's promise is kept one commit later. Filling it is
the first step of the next edit to this file: read the hash with
`git log --format='%h %cI' -1 <ref>`, append it to that heading after an em-dash exactly as 3.4.0
and below already do, then tag it. 3.5.0's `c33f658` was backfilled this way; 3.6.0's heading is
unhashed for the same reason and comes due next.

**Earlier releases are not tagged retroactively, and will not be.** 3.1.0 names two different
contents, so any tag placed on either commit would assert a one-to-one mapping between number and
content that does not exist for this repository's history. Use the commit hashes listed above to
compare anything at or before 3.4.0.
