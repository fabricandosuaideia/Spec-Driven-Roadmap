# Changelog

Every released version of **spec-driven-roadmap**, newest first, with the commit that carries it.

A release is one number declared in three places — `metadata.version` in `SKILL.md`, `version` in
`.claude-plugin/plugin.json`, and `plugins[0].version` in `.claude-plugin/marketplace.json`. From
3.5.0 on, `scripts/bump-version.sh` writes all three at once and refuses to run when they already
disagree. Before that they drifted — see **Two contents under one label** and **Version drift**.

---

## 3.9.0 — 2026-08-08

**The fourth net had no callers.** An analysis of the one remaining gap — two statements that must
agree and do not — measured the corpus first and then found something more embarrassing than the gap
itself: `check-consistency.py` shipped in 3.6.1 and was never wired to anything. Not in the
installers, not named in `SKILL.md` or any reference, and there is no CI here. It ran only because
someone remembered to, and unaided memory missing a drifted fact is precisely what it exists to
catch. A checker nobody invokes is worse than none: it produces the belief in a net without the net.

Worse, two declarative tables shipped with **zero readers** — this repository's own version of the
disease. `COUNTED_FACTS` in `check-consistency.py` and `DIMENSIONS` in `check-roadmap.py` were each
declared once and consulted never, and `DIMENSIONS` listed seven entries where rule 7 names six. A
wrong fact, sitting in the tree, inside a table nobody read.

- **`bump-version.sh` is now the release gate.** It runs the consistency check after bumping and
  exits non-zero when it fails. This is the one place a release cannot route around — you cannot cut
  one without bumping. The checker stays out of the installers deliberately: it audits this
  repository's internal agreement, which is a maintainer's concern, not a roadmap author's. It caught
  a case on its first run that nobody had thought to check: a version bumped with no `CHANGELOG`
  entry for it.
- **Both dead tables deleted, and a meta-check added so a third cannot appear**: every module-level
  constant must be read somewhere in its own file. It is the only check here aimed at the disease
  rather than a symptom, and it reproduces on demand — reintroduce either table and it fails.
- **`<file> Step N` pointers are now resolved.** The class a registry cannot cover, because nobody
  has to have written the fact down first: it is what a moved definition leaves behind. Namespaces
  are per-file — each reference numbers its own steps from 1 — with the seed's pair sharing one,
  derived from its forwarding stub rather than hardcoded. Remove that stub and two checks fail
  instead of none.
- **Scope is derived from disk, never a typed list.** The old `REFERENCES`/`GUIDES`/`READMES`
  constants silently excluded 38% of the prose corpus, including `guide/`, the one place in this
  repository's history where drift was actually recorded (`c33f658`, *"correct the guide it drifted
  from"*).

Twenty-three checks now. **What this does not close:** four of the seven known contradiction cases
stay uncovered, and the analysis says so with the reasons. Two never reached git at all — adversarial
review caught them before commit. One lives in a repository we do not control and cannot be checked
from inside, so it stays documented in prose. One is a composition of two individually-true
statements, which comparing copies cannot reason about. And roughly 198 normative sentences that
name something defined elsewhere remain unsupervised: the eighth case will arrive from outside any
registry, because nobody enumerates what they have not yet thought of.

## 3.8.1 — 2026-08-08

**The human guide never learned that you can ask it to check a roadmap.** 3.7.0 shipped the linter
and 3.8.0 gave it a trigger phrase, but `guide/HOW-IT-WORKS.md` and its two translations still said
nothing about it — a grep for the phrase returned zero in all three. The README had it; the document
a person actually reads to understand the skill did not.

All three now carry *"check my roadmap"* in the trigger list and a section explaining it: that it is
a read and writes nothing, that it is the same list Phase 2 runs when it closes a roadmap so this is
for asking **later**, what it looks at, and the two things worth knowing — a failure is a question
rather than a verdict, and it says when it could not judge something instead of guessing.

It also states what it cannot check: whether an open question is phrased well enough to answer,
whether a feature is genuinely a vertical slice, whether a coverage disposition is honest. Naming
that boundary is the point — a linter that seems to cover everything is worse than one whose limits
are written down.

Fourteen sections in each language now, anchors resolving, and a sweep confirms every behaviour
change from 3.6.0 onward reached the guides and the READMEs.

## 3.8.0 — 2026-08-08

**Checking a roadmap had no way to ask for it, and the seed's procedure was five times the size it
holds its own output to.** Both were mine, and 3.7.0 shipped the first one.

- **`check-roadmap.py` now has a trigger.** 3.7.0 added the linter, wired it into Phase 2's sanity
  checks, and then told the user to type `python3 …` in the README. The skill's `description` listed
  no phrase that reaches it, so *"check my roadmap"* invoked nothing — a capability with no door.
  The description now carries it, `SKILL.md` has a short section saying **the skill runs it, not the
  user**, and the READMEs ask a question instead of handing over a command. It is a read: no phase
  runs and nothing is written.
- **`handoff-seed.md` split at the Step 7/8 seam.** It was 1,010 lines / ~15,300 tokens, and
  `SKILL.md` tells the agent to read the relevant reference completely — while the skill caps the
  roadmap it *generates* at ~3,000. Steps 1-7 are the seed and run every time; Steps 8-10 emit an
  implementation prompt and run only when Step 7 did not end the procedure, which its own exit list
  does whenever nothing was seeded or Step 6 was skipped. Two triggers, two readers, one file. Steps
  8-10 moved to `references/handover-prompt.md`:

      common path   15,300 → 7,624 tokens
      handover       8,082 tokens, loaded only when a prompt is actually handed over

  Nothing was renumbered — the numbering stays continuous across the two files because it is one
  procedure, and the new file states that convention rather than qualifying thirty-eight bare `Step
  N` references one at a time. The `/loop` and option-A templates are byte-identical; they changed
  file, not content.
- **`check-consistency.py` gained the check that a split gets wrong**: steps 1-10 must exist exactly
  once across the two files. Verified by breaking it deliberately — renumbering Step 8 to Step 7
  produces `duplicated: Step 7 in handoff-seed.md and handover-prompt.md / missing: 8`. Twenty-one
  checks now, and both installers ship the new reference.

## 3.7.0 — 2026-08-08

**The skill's own sanity checks became a command.** `decompose-phase.md` closes with eleven checks on
the roadmap it just wrote, and every one of them was applied by reading. The 3.6.0 review named the
pattern: the checks that exist cover what is countable and skip what is derived, and the derived ones
are where the cheapest mistakes live precisely because nothing catches them.

`scripts/check-roadmap.py` runs them. Forward dependencies, duplicate names, the eight-task budget,
the `discharge:` line verbatim, the two-way agreement between each feature's `open questions` and the
roll-up, one ledger row per rubric theme, every `not decided` row having its `cross-cutting` entry
with an `affects:` line, `uncovered: none`, the derived `needs pre-written context.md` flag, the
build-order `.txt` agreeing with the roadmap, the size thresholds, and name uniqueness across every
roadmap and every `.specs/features/` directory — including the reverse: a built feature that no
roadmap names any more, which is what a rename looks like after the fact.

Three properties, chosen deliberately:

- **It is a linter, not a gate.** It never edits, and it says so in its own output: a failure is a
  question for whoever owns the roadmap, not a verdict.
- **It skips rather than guesses.** A check that cannot parse a file with confidence reports `·` and
  judges nothing. A false failure on a real backlog costs more than a missed one.
- **It states what it cannot see.** Whether a question is phrased well enough to answer, whether a
  slice is genuinely vertical, whether a coverage disposition is honest — those stay a read, and
  `decompose-phase.md` now says which half is which.

Both installers ship it. This is the fourth time a rule became a script in this repository, and the
reason is the same each time: a written procedure cannot be run against a test case.

## 3.6.2 — 2026-08-08

**The other 34 findings, triaged before being applied — and two grave defects that 3.6.1 shipped.**
Every remaining finding was put through two questions before any edit: is it still true at HEAD, and
is its proposed remedy correct? Three were dropped — two already closed by 3.6.1, one whose remedy
was worse than the defect it fixed. The rest were applied, twenty-six of them with a corrected
remedy, which is the number that matters: the original review had already had six remedies refuted,
and this pass caught twenty-six more that would have introduced defects had they been applied as
written.

- **`--rollback`'s guards fired on the auto-rollback path.** 3.6.1 added three checks for a human
  running `--rollback` later: refuse a backup describing files that are not here, refuse when
  `docs/ROADMAP.md` already exists, and refuse when the journal has no hashes. The in-run recovery
  path shares that function, and for it all three are wrong — it created the backup seconds ago,
  hashes are absent because the run never reached the step that writes them, and no product has
  existed long enough to be edited. The result: **every failed conversion left its backup behind,
  and a surviving backup aborts the pre-conditions — so the project could not be re-converted at
  all.** A failure in the first rename compounded it, exiting 1 with "this backup describes files
  that are not here" instead of rolling back and exiting 3. `rollback()` now takes `auto`, and the
  three guards are scoped to the manual path. Verified by injecting failures at both stages: exit 3,
  originals restored, backup removed, re-conversion works.
- **The prefix derivation refused a legal shape.** `tt-list` beside `tt-list-open-tasks` is a parent
  feature and its child; the common run is the whole of one name, and the script aborted with no way
  forward — the abort fired before `--slug` could override it. It now backs off a token at a time,
  which yields `tt`, the section they actually share.
- The rest is text: the Blockers gate, the ledger's fourth state reaching Step 8's list, the guide's
  definition of work-in-flight, the READMEs' handoff prompt brought level with Step 10's template,
  and `python3` declared as the prerequisite it became in 3.6.0. Two docstrings that justified
  themselves with a bug that never existed were rewritten to say what the code does.

## 3.6.1 — 2026-08-08

**A full review of 3.6.0 found 47 confirmed defects; three were grave, and this release closes them
plus the pattern behind fifteen of the rest.** Eight independent lenses read the skill, an adversarial
pass refuted six of their findings — and six of their proposed *remedies*, which is why nothing here
was applied without re-reading the passage it changes.

- **The seed's Step 5 cut the `## Status` block at the next `##`.** In a roadmap the feature entries
  are bare `### <feature-name>` sections with no `##` container, so on a legacy roadmap — one from
  3.1.0-3.2.0, where `## Status` exists and `## Cross-Cutting Decisions` does not yet — re-seeding
  deleted every feature entry. `docs/roadmap.txt` survives, so the next seed still finds targets and
  nothing surfaces until someone opens the file. The cut is now "next heading of any level", the same
  one `scripts/convert-to-multi.py` documents and for the reason documented there. Phase 2 now also
  *declares* the `### <feature-name>` form, which four consumers depended on and no producer stated.
- **`convert-to-multi.py` wrote absolute paths into its rollback journal.** Reached by a different
  absolute path — a move, another container mount, a copied worktree — every existence check returned
  false, so `--rollback` restored the originals *beside* the index it had failed to remove, deleted
  the backup, and reported success. Paths are now relative to the root, journals from 3.6.0 still
  load, and a journal describing files that are not present is a hard error. Also fixed there: the
  journal is written atomically, a backup this run did not create is never removed, and the
  work-in-flight report no longer misreads the colon inside `**In-progress** (file:line):`.
- **The "real PASS" test reached no verdict line.** `validate_state.py` selects only `Validation`
  headings and `Result:` lines, and in the persisted template the two lines that say whether the
  feature passed — `**Status**: ❌ Gaps present` and `**Overall**: ❌ Not Ready` — carry neither. The
  only selected verdict is the Discrimination Sensor's, which reports whether mutants died. A feature
  that killed every mutant while leaving an acceptance criterion without `file:line` evidence read as
  done. This skill's own test now selects those lines too and treats a ❌ or ⚠️ on them as not-done,
  which makes it deliberately stricter than that gate: exit 0 from the script is documented as
  necessary but not sufficient. The defect originates upstream and is described here rather than
  worked around silently.
- **`scripts/check-consistency.py`** — 19 checks over the invariants that keep duplicated facts in
  step: version declarations, cited section names resolving, no section name split across a newline,
  generated-block names never starting a line in `references/`, enumerated counts agreeing, both
  installers requiring the same payload, prose about that payload matching it, and trilingual parity
  of guides and READMEs. On its first run it independently found two of the review's confirmed
  findings: four places still saying the ledger has "three states" after 3.4.0 added a fourth, and
  `SKILL.md` still saying the installers copy only `SKILL.md` and `references/` after 3.6.0 added
  `scripts/`. Both fixed. The skill duplicates facts on purpose so each reference is self-sufficient;
  until now nothing kept the copies in sync but the maintainer's memory, and it had failed on at
  least five distinct facts across two releases.

The remaining 34 findings — fourteen medium, twenty light — are recorded and not yet applied.

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
