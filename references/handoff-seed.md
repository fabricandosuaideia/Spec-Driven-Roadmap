# Handoff Seed — One-Time, Not a Loop

## Contents

- [Goal](#goal) — what this step writes and where
- [Two surfaces, two lifetimes](#two-surfaces-two-lifetimes) — why status lives in `docs/`, not in `## Handoff`
- [When this runs](#when-this-runs)
- [Step 1 — Determine whether real work is in flight](#step-1--determine-whether-real-work-is-in-flight)
- [Step 2 — Determine which features are actually done](#step-2--determine-which-features-are-actually-done)
- [Step 3 — Build the roadmap status list](#step-3--build-the-roadmap-status-list)
- [Step 4 — Find the target feature and its remaining order](#step-4--find-the-target-feature-and-its-remaining-order)
- [Step 5 — Write the durable Status block (this skill's own file)](#step-5--write-the-durable-status-block-this-skills-own-file)
- [Step 6 — Write the Handoff (downstream skill's file, its exact schema)](#step-6--write-the-handoff-downstream-skills-file-its-exact-schema)
- [Step 7 — Report the outcome](#step-7--report-the-outcome)
- [Step 8 — Ask which implementation prompt to hand over](#step-8--ask-which-implementation-prompt-to-hand-over)
- [Step 9 — Loop option only: close every open question first](#step-9--loop-option-only-close-every-open-question-first)
- [Step 10 — Hand over the prompt, warn about the session, stop](#step-10--hand-over-the-prompt-warn-about-the-session-stop)

## Goal

After a roadmap closes, make the downstream spec-driven skill able to start the first feature
without re-deriving anything. That takes **up to two writes to two different files**, because they
have two different lifetimes:

1. **`## Status` in this skill's own roadmap file** — the durable backlog picture (every roadmap,
   what's done, remaining build order). Rewritten freely on every seed; nothing else owns it.
2. **`## Handoff` in `.specs/STATE.md`** — the downstream skill's own pause snapshot, in **its**
   exact schema, carrying a pointer back to (1).

**Write (1) is unconditional. Write (2) is not.** (2) is expressed in a schema this skill does not
own, so it happens only when Phase 0 confirmed a downstream skill *and* that skill's field list is
readable. When it did not, Step 6 is skipped and (1) alone is the seed — scope-phase's "generate the
roadmap anyway" is exactly this: Phase 2's output stands on its own for a human or any agent, and
nothing about it depends on which skill builds from it.

Then it hands the user **one prompt** to start construction with — either one feature, or a `/loop`
run across one roadmap — and stops.

This is the entire extent of this skill's involvement in construction — no waiting for PASS, no
advancing to the next feature automatically, no re-invoking itself. Once this step reports, every
subsequent "specify feature", "resume work", pause, and verify belongs entirely to the downstream
skill's normal flow, driven by the user or the general agent.

## Two surfaces, two lifetimes

**Do not put the backlog picture in `## Handoff`.** For `tlc-spec-driven` (the default downstream
assumption), `references/memory.md` defines that section as a *"pause snapshot (~500 tokens,
overwritten each pause)"*, with this row in its read/write trigger table:

    | Pause work / end of session | ## Handoff | Replace - overwrite Handoff section only |

and a pause procedure that replaces "everything between `## Handoff` and the next `##` or EOF". Its
template is **eight fixed fields**. Anything extra written there survives exactly until the first
`pause work` and is then gone, with no mechanism that ever restores it.

That row is an indented code block on purpose. **Never let a literal `##` start a line in these
reference files** — block parsing beats inline code spans, so a wrapped quotation turns into a real
heading, and this is the file that tells an agent to find `## Handoff` and overwrite everything after
it.

The durable half therefore lives in a file this skill owns and the downstream skill never rewrites:

- **Multi-section mode** → a `## Status` block at the top of `docs/ROADMAP-INDEX.md`.
- **Single-section mode** → a `## Status` block at the top of `docs/ROADMAP.md`.

That location is reachable by the downstream skill, but nothing addresses it. `tlc-spec-driven`'s
Knowledge Verification Chain Step 2 is *"Project docs → README, docs/, inline comments,
`.specs/STATE.md` (Decisions)"*, and the chain says *"Never skip steps"* — so `docs/` is in scope and
this skill's files are not off-limits. What is missing is the pointer: the chain names a directory
and no file, it fires only while that skill is *"researching, designing, or making any technical
decision"*, and its Context Loading Strategy — the list of what it actually loads — names
`.specs/STATE.md`, `spec.md`, `context.md`, `design.md` and `tasks.md`, and nothing under `docs/`.
Whether a given run opens `docs/ROADMAP*.md` is therefore a bet on a directory-level mention, not
documented behaviour, and not a bet the handoff should rest on. That is why Step 6's **Next step**
names the exact path, and why Step 10 offers the `CLAUDE.md` bridge.

**Confirm the schema before writing.** The eight-field shape below is `tlc-spec-driven` v3.x's. If
Phase 0 confirmed a different downstream skill, read that skill's own memory/handoff reference and
match its schema instead — write only fields it defines, and put the durable half in `docs/`
regardless.

## When this runs

Only after Phase 2 closes a roadmap (its coverage table reads "uncovered: none", counting the
`deferred`/`pre-existing` dispositions as covered).

**Phase 1 does not trigger this step.** A newly indexed section has no `docs/roadmap-<slug>.txt`
yet, so it is `NOT YET DECOMPOSED` — a state Step 4 can never pick a target from, which would burn a
write on nothing. After Phase 1 extends an index, just report: *"next action: decompose section
`<slug>`"*, and do not touch `.specs/STATE.md`.

**One exception — the single-to-multi conversion.** Renaming the roadmap of a project whose
`## Status` block or `## Handoff` names the pre-conversion paths invalidates them, so
the seed re-runs to repair those pointers — not to seed new work. That re-run is mandatory:
`Converting a single-section project to multi-section` in `index-phase.md` is what orders it, and
Step 1's work-in-flight test still applies in full. When it fires, Step 6 is skipped and the
pointers are **not** repaired — which is what that section's pre-condition tells you to settle
before renaming anything.

Never run this speculatively "just to check" — it is a write step, not a status query. To answer
"what's next?" without writing, read `docs/roadmap*.txt` and the relevant `validation.md` files
directly.

## Step 1 — Determine whether real work is in flight

Read `.specs/STATE.md` if it exists. The question is **not** "is the Handoff non-empty?" — this
skill's own prior seed always leaves it non-empty, and so does every downstream pause, so an
emptiness test would permanently block every later seed and no section after the first would ever
get one. Test for **evidence of actual work** instead:

Work is in flight if **any** of these hold:

- `## Handoff`'s `**Completed**` field is present and is not `none`.
- `## Handoff`'s `**In-progress**` field is present and is not `none`.
- The feature named in `## Handoff` has a `.specs/features/<name>/spec.md` on disk **and** does not
  have a real PASS (per Step 2's test).

**All three are scoped to the feature `## Handoff` names, and none of them fires once that feature
has a real PASS.** A downstream skill that finished a feature and then paused leaves `**Completed**`
populated, which reads as in-flight on the first bullet alone — but the work it describes is done,
and treating it as in flight would block every later seed on a snapshot of finished work. Test the
named feature first: PASS means not in flight, whatever the first two fields say. This is the same
"stale snapshot naming a feature that is already verified PASS" the paragraph below already exempts,
stated where the bullets are read.

If work is in flight → **do not write `.specs/STATE.md`.** Everything else still runs: Steps 2-5 are
what produce a truthful `## Status`, so run them — Step 5's block needs Step 3's counts and Step 4's
remaining order and target, and that file is this skill's own and reflects the roadmap, not the
session. Skip only Step 6. Then go to Step 7 and report which feature is in flight and that the
current position is unchanged — **except after a single-to-multi conversion**, where the paths the
Handoff names no longer exist: report the pointer as dead, name the deleted path, and say the repair
is a second seed once that feature passes (index-phase.md, exit (a)). Step 7's own exit list ends the
procedure there, so no prompt is
handed over.

If none hold — including when the Handoff is a stale snapshot naming a feature that is already
verified PASS, or is this skill's own earlier seed — it is safe to write. Continue.

## Step 2 — Determine which features are actually done

"Done" means a **real PASS**, not the presence of a file. A `validation.md` can exist while being
empty, still holding the unfilled `[PASS | FAIL]` placeholder, reporting FAIL, or asserting PASS with
no evidence. Worse, a genuine FAIL report normally contains per-criterion rows reading `| ✅ PASS |`,
so **never substring-match `PASS` across the whole file** — that reports failed work as done and
makes the seed skip past it.

**Precondition for the PASS test — check the directory exists.** If `.specs/features/<name>/` is not
on disk, the feature is **not done** by that test. Stop there; run no gate script. This precondition
does **not** reach the question-only exception below: that feature normally has no directory at all,
and its own test is the `discharge:` marker.

This is not a formality. `tlc-spec-driven` v3.3.0's `validate_state.py` returns **exit 0 when
`.specs/features/` does not exist at all** (it prints "nothing to check" and exits before it ever
looks at the feature argument). A fresh project — the normal state when this skill runs, since it is
a prequel to the build cycle — would therefore report *every* feature as verified, and the seed would
conclude the whole backlog is finished and seed nothing.

**Then apply the completion test.** It has two runners and they are the same test: a gate script if
the confirmed downstream skill actually ships one, otherwise your own read of the report. Neither is
a lesser version of the other.

**Check the disk, never the documentation.** Resolve `<skill-dir>` — the directory containing the
confirmed skill's own `SKILL.md`, not the project root — and list its `scripts/`. Use a script only
if the file is there **and** that skill's own reference documents it as the completion gate. **Never
construct that path from this file, from a version number, or from memory.** A skill's script set
changes between releases and an install lags them: `tlc-spec-driven` v3.3.0 ships `validate_state.py`,
while v3.2.0 ships only `lessons.py` and documents no validation script at all, so on a v3.2.0
install the command below resolves to nothing. That failure is worse than having no script: the run
either errors in the middle of a write procedure, or records a gate it never ran.

**When `tlc-spec-driven`'s `validate_state.py` is present:**

```
python3 <skill-dir>/scripts/validate_state.py <feature> --root <project-root>
```

Read the result as: exit `0` **and** the feature directory existed = real PASS. Exit `1` = not done
(missing report, FAIL, unfilled placeholder, or PASS with no `file:line` evidence). Exit `2` = usage
error, most often the feature directory is missing — also not done. **Those exit codes are that one
script's.** Another downstream skill's gate, or a later `tlc-spec-driven` one, has its own; read them
from that skill's reference before trusting an exit status, and if it does not document them, read
the report instead.

**Read the report as well, whenever its consolidated verdict lines are present** — and always when
there is no gate script, its codes are undocumented, or no code-execution tool is available.

**The script is a floor, not an equivalent, and this is a deliberate divergence.** `validate_state.py`
v3.3.0 selects only lines that are a `Validation` heading or contain `Result:`. In that skill's own
persisted template the two lines that actually say whether the feature passed carry neither marker:
`**Status**: … ❌ Gaps present` and `**Overall**: … ❌ Not Ready`. The only selected line that carries
a verdict word is the Discrimination Sensor's `**Result**: [N/N killed] - [PASS ✅ | FAIL ❌]` — which
reports whether mutants died, not whether the feature is done. So a feature that killed every mutant
while leaving an acceptance criterion without `file:line` evidence reads as **done** to that script.
Exit `0` from it is therefore **necessary but not sufficient**; where these lines exist, the report
decides. Say so in the Step 7 report when the two disagree, and never record a PASS the report
contradicts.

Collect the lines that are a heading (1-4 `#`) whose text *starts with* `Validation`, or that contain
`Result:`, `Overall:` or `Status:` (with or without the `**`) — that selection is
case-**in**sensitive — then judge the joined text **case-sensitively**, on the whole words `PASS` and
`FAIL`, plus this rule first:

- a `❌` or a `⚠️` on an `Overall:` or `Status:` line → **not done**, whatever any `PASS` says
  elsewhere. Those are the consolidated verdicts; the sensor's `Result:` is scoped to mutants.

- both `PASS` and `FAIL` present → unfilled template → **not done**
- `FAIL` only → **not done**
- `PASS` only, with no `path.ext:NN` citation anywhere in the file → **not done**
- `PASS` only, with at least one such citation → **done**
- no line matched either pattern → judge the **whole file's** text by these same rules; that is the
  script's own fallback, and skipping it disagrees with the gate on exactly the reports that do not
  follow the template
- no `validation.md` at all, or no `PASS`/`FAIL` anywhere → **not done**

Two traps in that file, both verified against `tlc-spec-driven` v3.x's `references/validate.md`. Its
persisted report is titled `# <feature> Validation` — the word comes *last*, so it fails a naive
heading test; `## Validation: <feature> — PASS/FAIL` is the Verifier's **chat** summary and is never
written to disk. And the report carries two `Result:` lines, the Discrimination Sensor's verdict and
Gate Check's `[X] passed, [Y] failed` counts. Judge them together — lower-case `failed` in a count is
not a `FAIL` verdict.

**One exception — question-only features.** Phase 2 may formalize a blocking open question as its own
feature (decompose-phase Step 3). It produces no code, so it can never earn a PASS report and would
block the seed forever. Such a feature is **done** when the roadmap's `## Open Questions` shows its
question `status: answered`, or when `.specs/features/<name>/context.md` exists. Its roadmap entry carries the literal line
`discharge: no code — answered open question or context.md` (decompose-phase Step 3) — that marker,
and nothing else, selects this test instead of the PASS test. A feature without it takes the PASS
test, whatever its objective says.

**Reading a `.txt`, always:** one feature name per line. Skip blank lines and any line starting with
`#`. Count and target only feature-name lines.

## Step 3 — Build the roadmap status list

One line per roadmap, so the whole backlog shape is visible — not a single disconnected pointer.

- **Single-section mode:** one line for `docs/ROADMAP.md`: how many of its features are done
  (Step 2's test) out of the total in `docs/roadmap.txt`.
- **Multi-section mode:** walk the topological list in `docs/ROADMAP-INDEX.md`'s **Ordering** section
  — that is build order; the roadmaps table is not necessarily sorted. Locate it by that name, never
  by its position in the output shape: inserting one block renumbers every later one. For
  each section, read its **Build-order file** column to get the exact `.txt` filename (never
  reconstruct it from the slug), then classify:
  - all done → `DONE (X/X, verified PASS)`
  - some done → `IN PROGRESS (N/M verified PASS)`
  - none done, `.txt` exists → `NOT STARTED (0/M)`
  - no `.txt` yet → `NOT YET DECOMPOSED` — note what it depends on per the index. A section the
    index marks excluded (pure foundation / pure decision log) is not this state and is not
    reported at all: Phase 1 excluded it from generation by design, so there is no roadmap for it
    to be waiting on.

## Step 4 — Find the target feature and its remaining order

**Pick the section first (multi-section mode), with an explicit precedence — do not assume only one
section can be active.** A user who builds out of index order produces several:

1. Any section marked `IN PROGRESS` wins. If more than one is, take the earliest in the index's
   Ordering list — and say in the report that others are also in progress.
2. If none is in progress, the first `NOT STARTED` in that same order.
3. If neither exists, every decomposed section is done → nothing to seed (see below).

Then walk that section's `.txt` (or `docs/roadmap.txt` in single-section mode) top to bottom. **The
target is the first name that is not done per Step 2** — not merely the first without a file. The
remaining build order is every name from the target to the end of that file.

**Then check what the target section consumes, without changing the target.** *Multi-section mode
only* — in single-section mode `external contract consumed` is always `none`. Walk its features'
`external contract consumed` values; for each, open the boundary contract that item belongs to in
`docs/ROADMAP-INDEX.md` and read the producing section off its edge. If Step 3 classified that
section `NOT YET DECOMPOSED`, record the contract as a **provisional producer** — index-phase Step 4
makes those names provisional until that section is decomposed. This blocks nothing and moves no
target; it is what Steps 7 and 8 need in front of them.

**Guard against name drift.** If a roadmap name has no `.specs/features/<name>/` directory but a
similarly-named one exists (`auth-login` vs. `auth-signin`), do not count it as unbuilt — that is
almost certainly the same feature built under a different name. Report the mismatch and stop, rather
than seeding a pointer that would rebuild shipped work.

**Do not assert what you did not check.** Step 6's template asks for `Completed` / `In-progress`. If
the target has partial work on disk (a `spec.md`, a `tasks.md` with unchecked boxes) but no PASS,
say so rather than writing `not started` — a confident falsehood in the machine-read handoff surface
is worse than a vague truth. If the target's `validation.md` reads FAIL, do not treat it as unstarted
either: name it as needing fixes.

If every feature in every decomposed roadmap is done, there is nothing to seed. Skip Step 6 — never
write a Handoff pointing at nothing, and never invent a "next" feature — but still write Step 5's
`## Status` block (its `**Handoff**` line records why nothing was seeded), then report at Step 7 and
end there.

## Step 5 — Write the durable Status block (this skill's own file)

Insert or replace a `## Status` block in `docs/ROADMAP-INDEX.md` (multi-section) or `docs/ROADMAP.md`
(single-section): if the heading is already there — both output shapes leave it in place — replace
only its body, **up to the next heading of any level** (`#`, `##`, `###`, …), respecting code
fences. Not "up to the next `##`": in a roadmap the feature entries are bare `### <feature-name>`
sections with no `##` container of their own, so a cut that stops only at `##` swallows every one of
them and deletes the feature list. That is the same cut `split_block` makes in
`scripts/convert-to-multi.py`, for the same reason and with the same fence handling — this block's
own body never contains a heading, so the stricter rule loses nothing. The failure is silent where it
bites: `docs/roadmap.txt` survives, so the next seed still finds targets and nobody notices until
someone opens the roadmap. If the heading is missing (a legacy or hand-made file), insert it
immediately after the H1 title, or at the very top when the file has none. Leave the rest of the file
untouched — `## Cross-Cutting Decisions` lives in this same file and is never yours to rewrite here.

```markdown
## Status

_Backlog position. Regenerated by spec-driven-roadmap v<version> on <YYYY-MM-DD>; feature status is
derived from `.specs/features/<name>/validation.md`, never hand-edited here._

- `docs/ROADMAP-<slugA>.md` — DONE (4/4, verified PASS)
- `docs/ROADMAP-<slugB>.md` — IN PROGRESS (2/5 verified PASS)
  - **Remaining** (build order): `<feature-3>` → `<feature-4>` → `<feature-5>` (closes the roadmap)
- `docs/ROADMAP-<slugC>.md` — NOT STARTED (0/6) — next after `<slugB>` per this index
- `docs/ROADMAP-<slugD>.md` — NOT YET DECOMPOSED (depends on `<slugC>`)

**Next feature**: `<target>` — see `docs/ROADMAP-<slugB>.md` for its objective, dependencies and
flagged dimensions.

**Handoff**: seeded to `.specs/STATE.md` — or one of the not-seeded states below
```

**Two fields in that italic header line are resolved, not copied.** `<version>` is **this** skill's
own version — the `metadata.version` value in its own `SKILL.md` frontmatter, read at run time,
never a number from memory and never the downstream skill's. **Resolve it from disk: read the
frontmatter of this skill's own `SKILL.md`** — the file whose body is already in your context, which
sits in the **parent** of the directory holding these reference files, with `references/` and
`scripts/` as its siblings — not the downstream skill's `SKILL.md` (Step 2's `<skill-dir>`), and not
the project root. Its frontmatter is what the installers stamp and what discovery reads, so it may
not be in context with the body — open the file rather than recalling the number. **If it cannot be
located or read, write `unknown` in the stamp and say so in Step 7's report.** Never fill this field
from memory or from inference: a wrong number on disk is worse than `unknown`, because it asserts a
false provenance for the whole roadmap — the exact failure the stamp exists to prevent.
`<YYYY-MM-DD>` is the date of the run that writes the block. Stamp both every time: without them the
generated roadmap is the one artifact of this whole procedure that cannot say which release produced
it, so a user whose install lags the documentation has nothing to check it against. The stamp cannot
go stale either, because Step 5 rewrites this block whole on every seed. **`<name>`, further along
that same italic sentence, is the third placeholder and the only one that does not resolve** —
literal, type the angle brackets. It names the path pattern every feature's report follows, not a
feature; substituting the target's name turns a general rule into a false claim that the whole
backlog's status was derived from one feature's `validation.md`.

When every decomposed feature is done, write `**Next feature**: none — every decomposed roadmap is
complete` instead of naming a target.

Single-section mode collapses the list to one line for `docs/ROADMAP.md` plus its own **Remaining**
sub-list.

**The `**Handoff**` line is where a skipped Step 6 becomes durable.** A pending seed announced only in
chat dies with the session, and a later run cannot tell "never seeded" from "seeded and since
overwritten". Write the seeded path when Step 6 runs. Step 6 is skipped for four different reasons
and only one is a missing skill, so write the one that is actually true:

- `pending — no downstream spec-driven skill installed; install one and re-run this skill's seed`
- `pending — <skill> confirmed but its handoff schema could not be read`
- `not rewritten this run — work in flight on <feature>` — and when the cause of the skip is a
  single-to-multi conversion, name the dead path too, because the pointer is now wrong rather than
  merely stale: `not rewritten this run — work in flight on <feature>; its Handoff still names the
  pre-conversion <old-path>` (index-phase.md's conversion procedure, exit (b))
- `not seeded — every decomposed feature is done`

One more line is not a skip at all — Step 9 can invalidate a Handoff that was written, and its
re-run exit writes this instead:

- `superseded — decomposition invalidated this run (<category-5 gap on X | category-4 collision
  on Y>); do not act on this block until Phase 2 re-runs and this skill's seed runs again from
  Step 1`

Step 5 runs before Step 6, so decide from Step 1's evidence test and Step 6's own two skip cases. One
line, regenerated on every seed, so it cannot go stale.

Keep it to counts, names and paths. Never copy feature objectives or task lists here — that detail
already lives in the roadmap body below it. The version and the date are part of the block's own
header line rather than any feature's detail, so they are not what that rule excludes.

## Step 6 — Write the Handoff (downstream skill's file, its exact schema)

**Skip this entire step when there is no schema to write into.** Two cases:

- **Phase 0 recorded that no downstream skill is installed.** There is no `.specs/` namespace to hand
  off into and no field list to match.
- **A skill was confirmed but its handoff/memory reference could not be read**, so its field names
  are unknown. "Write only the fields it defines" presupposes knowing them; inventing them is rule 1's
  silent default wearing a schema.

In either case write **nothing** under `.specs/` — not `STATE.md`, not an empty `## Handoff`, not a
placeholder. Creating that file speculatively is worse than leaving it absent: the downstream skill's
resume treats `## Handoff` as its own snapshot to reconcile against git, so a guessed shape becomes a
stale hypothesis it has to work around before it can start. Step 5's `## Status` already carries the
target and the remaining build order, in a file no other skill rewrites; record the pending seed on
its `**Handoff**` line and go to Step 7.

Otherwise: locate the `## Handoff` header in `.specs/STATE.md` and replace only the body between it
and the next `##` or EOF. Never touch `## Decisions`. If the file does not exist, create it in the shape the
downstream skill prescribes — for `tlc-spec-driven`, an H1 `# STATE`, then `## Decisions` with an
empty body, then `## Handoff`.

Emit **only** the fields that skill defines. For `tlc-spec-driven` v3.x, exactly these eight:

```markdown
## Handoff

- **Feature**: <target feature name>
- **Phase / Task**: not started — no spec.md on disk yet
- **Completed**: none
- **In-progress** (file:line): none
- **Next step**: specify feature `<target>` — create it at `.specs/features/<target>/` using that exact directory name. Spec source: `<ROADMAP-PATH>` section `<target>` (objective, scope-units, dependencies, flagged dimensions and open questions are there — read it before clarifying). Project-wide decisions already settled: `<STATUS-PATH>` `## Cross-Cutting Decisions` — read before Discuss and do not re-decide what it answers. Backlog position: `<STATUS-PATH>` `## Status`.
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: <output of `git branch --show-current`>
```

**Resolve every path placeholder by mode** — writing an index path in single-section mode points
at a file that does not exist:

| Placeholder | Multi-section | Single-section |
|---|---|---|
| `<ROADMAP-PATH>` | `docs/ROADMAP-<slug>.md` | `docs/ROADMAP.md` |
| `<STATUS-PATH>` | `docs/ROADMAP-INDEX.md` | `docs/ROADMAP.md` |
| `<BUILD-ORDER-TXT>` | `docs/roadmap-<slug>.txt` (from the index's **Build-order file** column) | `docs/roadmap.txt` |

`<STATUS-PATH>` carries **both** project-level blocks — `## Status` and `## Cross-Cutting Decisions`
(decompose-phase Step 7a) — which is why one placeholder serves both references above. They live
together for the same reason: exactly one of each exists per project. `<BUILD-ORDER-TXT>` is unused
by the Handoff itself; it lives here because Step 10 resolves its placeholders against this one table.

Notes on the fields that carry real weight:

- **Next step** is the highest-value field in this file: it is the one place both the downstream
  skill's resume *and* the human read. It must carry (a) the trigger phrase confirmed at Phase 0,
  (b) the exact directory name so the built feature matches the roadmap's name, (c) the roadmap
  path, and (d) the pointer to `## Cross-Cutting Decisions`. Without (c) the entire Phase 2 output —
  objective, scope-units, dependencies, sizing, dimensions — reaches nothing, and the user gets
  re-interviewed on scope this skill already resolved. Without (d) the same happens to decompose-phase
  Step 7a: that skill's Discuss starts from `spec.md` and resolves the rest from the code, and neither
  its own procedure nor its rubric names a roadmap file — `docs/` is reachable through the Knowledge
  Verification Chain, but nothing there points at `## Cross-Cutting Decisions`. Unless the path is put
  in front of it, a project decision the user already made gets asked again per feature — and answered
  inconsistently, which is worse than not having asked at all.
- On a **legacy roadmap with no `## Cross-Cutting Decisions` block** (Step 10 names the one case that
  produces it), drop clause (d) rather than pointing the downstream skill at a heading that is not
  there.
- **Branch** is unconditional. Obtain it with `git branch --show-current`; use `none` only outside a
  git repo.
- **Uncommitted files** — report what `git status --porcelain` actually shows, not a blind `none`.
  The downstream skill's resume reconciles this field against git, so a false `none` is a claim it
  will catch and have to work around.
- **Blockers** — check three sources in this order and stop at the first that fires; put that exact
  question here instead of `none`, and set **Next step** to answering it rather than the specify
  trigger. Quote one question, not three sources' worth — the ~500-token budget is real.
  1. The target's own `open questions` field has a `status: open` question.
  2. A boundary contract the target consumes has an unresolved marked-open item.
  3. `<STATUS-PATH>` `## Cross-Cutting Decisions` has a `not decided` row (decompose-phase Step 7a).
     A `deferred to feature <name>` row is not one of these and does not block; the build order
     already enforces it.
     Follow it to the `cross-cutting` entry it names and read that entry's `affects:` line: it blocks
     when `affects:` reads `all` or names the target. **`needs pre-written context.md` does not gate
     this source** — a project-wide invariant reaches a feature whether or not that feature flagged a
     dimension of its own, which is exactly why source 1's test cannot see this class.

  Treat a question as resolved if its roll-up entry reads `status: answered`, or — **sources 1 and 2
  only** — if `.specs/features/<target>/context.md` exists. That file records one feature's
  discussion; it cannot have settled a project-wide theme. Source 3's proof of resolution is its row
  having become a decision.

  **Read `affects:`; never re-derive it.** Judging here that a question "probably does not touch" the
  target is deciding an ambiguity from less information than Phase 2 had — rule 1. An entry with no
  `affects:` line is a malformed roll-up: treat it as `all` and say so in Step 7's report. If
  `## Cross-Cutting Decisions` does not exist at all, the roadmap predates Step 7a — report that too,
  and never read its absence as "no open themes".

  Never point a fresh start past an unanswered question **that reaches it**. An open cross-cutting
  question does not block a target its `affects:` line excludes: the harm this gate prevents is a
  feature being built against a guess, and a question that feature never encounters cannot be guessed
  at. Blocking anyway would freeze the whole backlog behind one project-wide question and make option
  A unusable. It is also the only shape the downstream skill can act on — its Handoff, its Discuss
  and its `context.md` are each scoped to one feature, so a blocker about a feature it is not
  building has nowhere to land.

Keep the whole section near the downstream skill's ~500-token budget. The backlog picture is not
repeated here — Step 5's file holds it, and **Next step** points at it.

## Step 7 — Report the outcome

Tell the user, plainly:

- that roadmap generation is finished — this is the moment the planning work closes;
- which version of this skill produced the run — the `metadata.version` value from its own
  `SKILL.md` frontmatter, resolved as Step 5 prescribes and the same one Step 5 stamped into the
  roadmap's `## Status` block (`unknown` if it could not be read). A user who compares it against the
  release they believe they installed is how a stale install gets caught. This **repeats**, at the
  close, the version the Phase 0 preamble announced before the run's first question (scope-phase.md)
  — the roadmap file is not the only place that number has to land, but this is the last one, and a
  user who never opens that file sees it only in chat: there and here. Report it even though the run
  already opened with it;
- the roadmap status list from Step 3, one line each;
- which feature is next, and whether it was seeded into `.specs/STATE.md` or not — and if not, why
  (work in flight / nothing left to build / no downstream skill to seed into or a schema you could
  not read — in which case the target is still named, from Step 5's `## Status`). A Handoff that
  *was* written with its **Blockers** field filled is reported as seeded-but-blocked, not as
  not-seeded. When the blocker came
  from a `not decided` row, say so and name the other features its `affects:` line reaches: one
  answer unblocks all of them, which is the difference between a five-minute question and a stalled
  backlog;
- any **provisional producers** Step 4 recorded, and which sections have to be decomposed before
  those names are firm;
- that construction from here on is the downstream skill's own job, through its own triggers.

Then go to Step 8 — **unless** any of these hold, in which case there is no prompt to hand over and
this procedure ends here:

- **Nothing was seeded** (work in flight, or every feature already done). There is no target to
  build; offering a prompt would point at nothing. When the cause is work in flight, add that this is
  a pause rather than the end of the line: once that feature closes and this seed runs again, the
  user gets a choice between a command that builds one feature and a single `/loop` run across a
  whole roadmap. Say only that the choice will be there — no command, no trigger phrase and no
  template is handed over at this exit, because the prompt is Step 10's to emit and only after Step 8
  has asked which one the user wants.
- **Step 6 was skipped** — no downstream skill, or a confirmed one whose schema you could not read.
  Say the roadmap is complete and usable as it stands, name the target feature and point at Step 5's
  `## Status` for the backlog position, name what to install, and say that re-running this skill's
  seed afterwards completes the chain without re-running Phase 2. Add that the same choice waits on
  the other side of that install — one feature at a time, or one `/loop` run across a whole
  roadmap — and that it is conditional on installing the skill, since neither shape exists without
  one. Name only the existence of that choice. There is no confirmed trigger phrase, so there is no
  prompt to hand over — never improvise one from `tlc-spec-driven`'s, and that same prohibition is
  why the sentence above carries no command with it.

A blocker recorded in Step 6 does **not** end it here — Step 8 is still offered, because option B
exists precisely to close blocking questions.

## Step 8 — Ask which implementation prompt to hand over

The roadmap is done and the user now has to actually build from it. There are two legitimate ways to
drive that, and **which one is the user's call — never pick for them, and never default to the loop
because it looks faster.** Ask, in the confirmed output language:

- **Option A — one feature at a time.** They get the prompt for `<target>` only, run it, and come
  back for the next feature when it passes. Full control, a checkpoint per feature.
- **Option B — one `/loop` run over one roadmap.** The build does not stop until every feature in
  *that roadmap* is verified PASS. **A loop covers exactly one roadmap file**, so say which:
  - *Single-section mode:* `docs/ROADMAP.md` — that is the whole backlog, so B finishes the product.
  - *Multi-section mode:* the target section's `docs/ROADMAP-<slug>.md` alone, the one Step 4 picked.
    Name that section, name every other section as not covered, and say what happens when it ends:
    they come back, this skill re-seeds, and the next section gets its own loop. Give the reason or
    it reads as a limitation — a boundary contract's producer names are *"provisional until that
    section is decomposed"* (index-phase Step 4; Step 10's scope rule carries the same reason in
    full — keep the two in step), so the gap between two sections is where a plan meets what
    actually shipped. That is a checkpoint, not a step a loop can take unattended.

  State the precondition up front: **that roadmap must have zero open questions**, because a loop has
  no one to ask. If any remain, you will interview them closed first, and only then produce the prompt.

  **When Step 4 recorded a provisional producer, say so here and do not present option B as the
  default** — every feature that consumes one would be built unattended against names that can still
  move. Option A is unaffected, because a human is present. The user may still choose B; then Step 10
  names the provisional producers beside the prompt, in the surrounding message.

Everywhere below, **"the roadmap"** means that one file and its build order — `<ROADMAP-PATH>` and
`<BUILD-ORDER-TXT>` exactly as Step 6's table resolves them for the target section.

**Say what option B actually trades away — it is not "no questions left".** Closing the roadmap's
open questions does not close the gray areas Phase 2 Step 7b deliberately left to the downstream
skill's own Discuss. In a loop those get the agent's default, recorded with its rationale in each
spec's Assumptions & Open Questions, for the user to review afterwards. That is a legitimate trade
and it is that skill's own documented fallback — see Step 10 below, which cites it — but it is the
user's to make knowingly:
option B means *"the roadmap has no gaps, and the implementation-shape calls inside each feature get
decided for you and written down"*. Name the count from that roadmap's `## Expected Gray Areas` so
the size of the trade is concrete rather than abstract — and say it is a floor, not a ceiling: that
block holds only what Phase 2's own sweep turned up (decompose-phase Step 7b), while each feature's
Discuss generates its own on top of it. A roadmap that omits the block has none, not an error. Under
option A those same gray areas are put to the user in context, with the code in front of them — which
is the better answer whenever a human is available.

**Option B is also the path of greatest accumulation** — a cost that only surfaces after several
waves of work over the same roadmap. Step 9 closes *every* open question in that roadmap before the
prompt exists, and decompose-phase Step 8 requires the results to stay: *"Answered entries stay —
never deleted"*, because the answer itself is the record. Each loop therefore deposits a full set of
answered questions that never leaves the file — in the `## Open Questions` roll-up, and in each
carrying feature's own `open questions` field. Across successive waves aimed at one roadmap that is
the single largest driver of its growth, and it is why a new wave usually reads better as its own
section than as an extension of the one already there —
see `New scope arriving at a project that already has a roadmap` in scope-phase.md. That is a cost
to name, not a veto: option B remains the user's to choose, exactly as this step already frames it.

If Step 6 recorded a blocker, say so here: option A cannot give a clean start command until that
question is answered, and option B's sweep is what answers it.

Option A → skip to Step 10. Option B → Step 9.

## Step 9 — Loop option only: close every open question first

*Only when the user chose option B.*

A loop runs unattended. Every ambiguity rule 1 refused to guess is a place the run would either stall
or silently guess — so all of them get closed **before** the prompt exists. Announce that first: say
you will read the roadmap for gaps, and that the roadmap must be complete before you can hand over a
loop prompt.

**1. Sweep the roadmap the loop will actually run, in full.** Not just the target feature — the loop
runs past every feature in that file without stopping. Scope the sweep to exactly what the loop
covers and no wider: a question about a section this loop will not build is asked weeks early,
against a decomposition that "When to re-run, and what is frozen" expects to move before it is built.

- Single-section mode: `docs/ROADMAP.md`.
- Multi-section mode: the target section's `docs/ROADMAP-<slug>.md` **only** — plus, in
  `docs/ROADMAP-INDEX.md`, the **Marked-open** items of every boundary contract on an edge into this
  section that a feature here cites in its `external contract consumed` field. Those are open
  questions living in no roll-up, and Step 6's **Blockers** rule checks them for the target feature
  only; the loop runs past every other feature that consumes one.

Read each file top to bottom. Collect open questions from **both** places they live: each feature's
`open questions` field, and the `## Open Questions` roll-up. They can disagree — a question present
in one and missing from the other is still an open question, and the roll-up is the half the loop
prompt's reader is least likely to check.

Also read `## Cross-Cutting Decisions` (in `docs/ROADMAP.md`, or `docs/ROADMAP-INDEX.md` in
multi-section mode), for three things. Its `not decided` rows are the project-level index of
unanswered themes, and they are **in scope for this interview even when their entry lives in a file
this sweep does not cover** — decomposition is lazy, so a theme first raised by a sibling section
keeps its one roll-up entry there (decompose-phase Step 7a). For each `not decided` row: open the
`<roadmap-path>` it names, read only that file's `## Open Questions`, and if the entry's `affects:`
line reads `all` or names any feature in this roadmap, ask it here and write it back per point 3.
Repair a mismatch before anything else, because it is exactly the shape that reaches the build
unnoticed: an entry with no row → add the `not decided` row naming it; a row whose named path holds
no such entry → create the entry in this roadmap's `## Open Questions`, tagged `cross-cutting` with
`affects: all`, and ask it here too. Point 4's propagation check tests every new
answer against the decided rows. And a theme sitting there as an `N/A because` row whose reason no
longer holds is a gap the sweep must close: a decomposed roadmap now touches it, so ask it in this
interview like any other open question and write the answer over the row (decompose-phase Step 7a's
supersession rule). A loop cannot ask it later. A ``deferred to feature`` row is neither of those and
is not swept: its question is carried by a feature in the build order, so this sweep already meets it
in that feature's own `open questions` field.

**Do not sweep `## Expected Gray Areas`.** Those were deliberately left to the downstream skill's own
Discuss (decompose-phase Step 7b) — they failed the three tests, meaning they are feature-local and
better answered with the code in front of them. Step 10's prompt is what tells the run how to handle
them unattended; re-asking them here is the exact waste decompose-phase Step 7 exists to prevent.

**No section but the target's is covered by this loop** — decomposed or not, and for two different
reasons. A `NOT YET DECOMPOSED` section has no build order to run, and decomposing it is a Phase 2
run this skill never marches into on its own (rule 10). A decomposed sibling is excluded by Step 10's
scope rule instead. Either way, name every uncovered section explicitly, so the user does not read
"loop until done" as "loop until the whole product exists".

**2. Interview them closed, one at a time, in build order** — earliest-blocking question first, so an
answer that reshapes later questions arrives before them. For each: quote the question, cite where
the source leaves it unresolved (the field already carries that citation), and wait for the answer.
Never batch them into one wall of questions, and never answer one yourself.

If the user replies "you decide": ask once for the single constraint that actually governs the
choice, then record the resulting choice as the answer, noting it was delegated. Never leave a
question effectively unanswered while tagging it `answered`.

If the user abandons the interview or defers a question, **option B is off the table.** Say so, and
fall back to option A at the first still-open question. Never emit a loop prompt over a roadmap with
a known gap.

**3. Write each answer back, everywhere its carrier lives.** Which writes those are depends on what
carries the question (decompose-phase Step 8), and the carriers do not take the same set.

**Feature-carried — two writes.** Retag that feature's `open questions` line `status: answered` and
write the answer inline; do the same on that question's `## Open Questions` entry. Answered entries
are never deleted. Then re-evaluate that feature's **needs pre-written context.md** — it stays `yes`
if any implicit dimension is still present, and flips to `no` only when the open question was its
sole cause.

**`cross-cutting` — two writes, and neither is a feature's field.** The carrier is the entry's own
`affects:` line, so there is no `open questions` line to retag and you must not create one.

- Retag the `## Open Questions` entry `status: answered` and write the answer inline. **Leave
  `affects:` in place** — it records what the answer reached, and point 4 reads it to know where to
  look for propagation.
- Promote that theme's `not decided` row in `## Cross-Cutting Decisions` to the real decision, with
  one line of rationale. This is a state change, not a third copy: the roll-up keeps the answered
  question as the record of where the decision came from, and the row is the standing rule the build
  obeys — Step 6's **Next step**, Step 10's prompts and the `CLAUDE.md` bridge all point at the
  ledger and never at the roll-up. An answer that lands only in `## Open Questions` was collected and
  then dropped on the floor; a row still reading `not decided` beside an answered question tells the
  build to re-decide what the user just settled.
- Touch no feature's **needs pre-written context.md**. A cross-cutting question never set that flag —
  Step 6 computes it from the feature's own dimensions and its own field — so answering one cannot
  clear it, and flipping it here would claim a Discuss trigger went away that was never there.

**A marked-open boundary-contract item is written back where it lives** — in `docs/ROADMAP-INDEX.md`'s
contract for that edge, the answer replacing the question while keeping the question text as the
record of what was decided and why. It has no roll-up entry; the contract is its only home.

**Stay inside the question.** An answer never re-opens scope-units, sizing, or task estimates — those
are Phase 2's, and no answer makes them this step's to edit. It can legitimately reach two other
things: an edge between features that already exist, and the coverage table. **Both route through
point 4's categories 4 and 5, and only there** — never decide either here, or one trigger gets two
answers. Never quietly patch a decomposition inside this step.

**4. Re-read from disk, and check what the answers set off.** When the last answer is written, read
every swept roadmap file again, top to bottom, from disk — not from your memory of the interview. Do
not report "no gaps" on the strength of having asked the questions; report it on the strength of
having re-read the files.

The re-read does two things at once. First, the obvious one: confirm no `status: open` survives
anywhere, in either place. If one turns up — the usual cause is a roll-up and a feature field that
were out of sync — close it and start the pass over.

Second, and this is what the pass is really for: **an answer is not inert.** It can create work
somewhere else in the roadmap that nobody wrote down, and the loop will not notice. Test each answer
just given against this fixed list, in the other features, not only in the one that carried the
question:

1. **It adds a dimension elsewhere.** "Payments retry automatically" gives the orders feature
   idempotency/dedup that was never flagged on it.
2. **It creates a question elsewhere.** "Soft delete, always" forces "do reports count
   soft-deleted rows?" onto a feature that had no open question at all.
3. **It contradicts an earlier answer** — including a `## Cross-Cutting Decisions` entry, or an
   `N/A because <reason>` whose reason the answer just invalidated.
4. **It adds or moves an edge between features that already exist.** "Every write is audited" makes
   the orders feature depend on the audit-log feature already in this roadmap, listed after it because
   nothing needed it first. Coverage does not change; the order does.
5. **It requires a capability no feature provides.** "Auth through an external IdP" needs config and
   secrets handling no feature's objective or scope-units deliver. `uncovered: none` is now false.

**Categories 4 and 5 arrive looking identical** — both read as *"something has to exist before X"*.
Tell them apart on the **coverage table**, never on the dependency graph. Name the capability the
answer requires, then look for its owner:

- A feature in this roadmap delivers it (its objective or `scope-units covered` say so), or a row
  already reads `covered by reference to …`, `deferred to …`, or `pre-existing` → **4**.
- Nothing delivers it and no row claims it → **5**.

The self-check: **a 4 never edits the coverage table.** If the repair needs a new row, a changed
disposition, or a new feature, it is a 5 — and a 5 is not yours to repair.

**Route categories 1–3 as questions.** Each becomes a new question, asked the same way, written back
the same way, and then the whole pass runs again, because the new answers propagate too.

**Route category 4 as a bounded repair, not a question.** Rule 4's no-forward-dependencies makes the
fix forced, so there is nothing genuine to put to the user; applying an invariant is not deciding an
ambiguity. Establish the movable window first: list `.specs/features/`. **Every name with a directory
on disk is frozen in place** — decompose-phase freezes names and relative order at directory
existence, not at PASS, so a FAIL or a half-written spec freezes its feature too. The rest of the
build-order file is movable (*"reordering it only among not-yet-started features is fine"*). Then:

- **The edge already points backwards** — the provider is listed earlier. Nothing moves. Write the
  dependent's `depends on` field and touch no other file.
- **Otherwise move the provider, never the dependents**, to the latest position still before every
  feature that depends on it and still after everything it depends on. Moving one feature earlier
  leaves every other position intact; moving dependents later cascades into their own dependents and
  can push work across an increment boundary the user never moved.
- **Stop if that position does not exist** — the provider is frozen, would have to cross a frozen
  feature, or is not in this roadmap at all. Report the edge and what it collides with: something
  already built, or already delegated elsewhere, now needs something planned after it. No reordering
  fixes that, and renaming around it is forbidden. Option B is off the table — and so is option A:
  the recorded order still carries the dependency this pass just proved it cannot legally satisfy,
  so follow **What follows either re-run exit** below.

A legal move writes exactly three things: the `depends on` field, the roadmap's execution-order block
(keep its increment markers), and the `.txt` (names only, one per line). Editing anything else means
you misread the case. Then run the pass again — the re-read is what proves rule 4 still holds
everywhere after the move.

**Route category 5 as a stop.** Never invent the missing feature here; decompose-phase Step 7c
refuses the same move for the same reason. Keep the answer (point 3's writes already landed it) and
append one clause to its `## Open Questions` entry naming the capability that has no owner. Then take
option B off the table and follow **What follows either re-run exit** below. The answer is not lost:
that answered entry is what the re-run reads instead of putting the same question to the user twice.

**What follows either re-run exit.** Two paths reach here: a category-5 stop, and a category-4
collision no legal move repairs. Hand over no prompt — not option B, and not option A: the target
came out of a decomposition you have just proved wrong, and a re-run may reorder any feature that has
no `.specs/features/<name>/` directory yet, which the target by definition has not. Answers already
written back stay on disk; they are correct and the re-run extends around them. Say explicitly that
the `## Status` block and the `## Handoff` written in Steps 5-6 describe the pre-answer decomposition
and must not be acted on until Phase 2 re-runs and this seed runs again from Step 1 — Step 1's
evidence test is what makes that second run safe.

Make it durable before stopping — a warning that lives only in chat dies with the session (Step 5).
Rewrite the `**Handoff**` line of the `## Status` block to its `superseded` state, and rewrite the
body of `## Handoff` in `.specs/STATE.md` inside the same eight fields: the cause in **Blockers**,
and **Next step** reading `re-run Phase 2 for <ROADMAP-PATH>, then re-run this skill's seed` instead
of the specify trigger. Then stop.

**Cap it at three passes.** If a third pass still produces a new question or a category-4 move, stop
and say so plainly: a set of answers that keeps generating more work is evidence the scope is not
settled, and that is information the user needs — not something to grind out.

Write down what the capped pass found before falling back — dropping it is rule 1's silent default
with extra steps. Each question the last pass turned up and did not ask takes point 3's
feature-carried shape, minus the answer: the carrying feature's `open questions` field,
`status: open`, plus its matching `## Open Questions` entry — and set that feature's
`needs pre-written context.md` to `yes`, which is what that field then derives to. A category-4 edge
left unapplied is written the same way, as a question on the dependent feature naming the provider
and what the move collided with. A question no feature carries takes point 3's `cross-cutting` shape
instead — the roll-up entry with its `affects:` line **and** its `not decided` row, since the row is
the half Step 6's Blockers source 3 reads. This does not restart the pass: the cap has already taken
option B off the table, and option A is the path that tolerates a recorded open question.

Option B is off the table in that case; fall back to option A and report where it kept branching —
through point 5, whose re-run of Steps 2-6 is what promotes any of these that reaches the target into
the Handoff's **Blockers** field, so Step 10's blocker branch reports the question instead of handing
over a command. An uncapped fixpoint is how a check designed to protect an unattended run becomes an
unattended run of its own.

**5. Recompute the seed if anything moved.** Closing a question can discharge a question-only feature
(Step 2's exception), which changes the target and the remaining order — and it clears the Step 6
**Blockers** field. If any question was closed or any feature moved, re-run Steps 2–6 before emitting
the prompt, so the `## Status` block and the Handoff cannot contradict the prompt you are about to
hand over. Re-running Step 6 re-reads the ledger: a `not decided` row point 3 failed to promote will
re-block here, which is the check working, not a new problem. **A blocker surviving this re-run takes
option B off the table** — emit no loop prompt, name the question and the file its entry lives in,
and fall back to option A's blocker branch (Step 10).

**If that re-run reaches Step 4's "nothing to seed", there is no loop to hand over.** Discharging the
last unbuilt feature finishes the backlog. Say so plainly: the questions just closed are written into
the roadmap, Step 5's `## Status` block is current, and no prompt follows — Step 6 is skipped along
with Step 10, because a Handoff pointing at nothing and a loop prompt with an empty `<target>` are the
same error in two files. Do not fall back to option A either; it has no target for the same reason.

## Step 10 — Hand over the prompt, warn about the session, stop

Give the prompt **verbatim, in one copy-paste block** — the downstream skill is entered by the user
typing its trigger, so a paraphrase is a broken handoff. Resolve the placeholders exactly as the
table below prescribes — Step 6's table defines only three of the seven, and one of the seven must
not be resolved at all. Write the prose in the confirmed output language, but keep trigger phrases,
feature names and file paths exactly as they are on disk.

**Placeholders — resolve six, leave the seventh exactly as written.** The two templates use one kind
of placeholder they do not share, and mixing them up is the one way to emit a prompt that looks right
and cannot work:

| Placeholder | Emit as | Value |
|---|---|---|
| `<target>` | substituted | Step 4's target feature name |
| `<ROADMAP-PATH>` | substituted | Step 6's table |
| `<STATUS-PATH>` | substituted | Step 6's table |
| `<BUILD-ORDER-TXT>` | substituted | Step 6's table |
| `<downstream-skill>` | substituted | the skill confirmed at Phase 0 — its **name**, not its trigger phrase; both appear in the prompt and they are different strings |
| `<DISCHARGED-LIST>` | substituted | resolved below; `none` when there are none |
| `<current-feature>` | **literal — type the angle brackets** | nothing. It is the loop run's own per-iteration variable, defined inside the prompt itself |

`<current-feature>` is the only placeholder that survives into the pasted text, and it survives on
purpose. Substituting it — with `<target>` or anything else — pins every iteration to one feature:
the run re-specifies feature one forever and gates every later feature on feature one's
`validation.md`. The loop then never terminates and nothing past the first feature is ever built.
If a placeholder is not in this table, do not invent a value: stop and say which one.

`specify feature` in both templates below is `tlc-spec-driven`'s trigger. If Phase 0 confirmed a
different downstream skill, substitute **its** fresh-start trigger phrase — the same one Step 6's
**Next step** carries. A prompt built on a trigger the installed skill does not answer to is inert.

**Option A — one feature:**

```
specify feature <target> — create it at `.specs/features/<target>/` using that exact directory name.
Spec source: <ROADMAP-PATH>. Read <STATUS-PATH> `## Cross-Cutting Decisions` before Discuss and treat
it as settled — do not re-decide what it answers.
```

The directory-name clause is not redundant with Step 6. This prompt is pasted into a **fresh**
session, and the downstream skill reads `## Handoff` on resume only — so this prompt, not the
Handoff, is the only place the exact name reaches a fresh start. One drifted directory name makes
verified work look unbuilt to the next seed.

*Unless Step 6 recorded a blocker.* Then give no command at all: report the question that has to be
answered first, so the user is not handed a command that would start a feature that cannot start
cleanly.

Omit the last sentence only for a **legacy roadmap generated before Step 7 existed** — that is the
only way the block is absent, since decompose-phase's sanity check forces it to exist (all-`N/A` at
minimum) and Phase 1 pre-creates the heading in multi-section mode. Check the file before omitting;
do not reason your way into this branch. That sentence is what makes decompose-phase Step 7a reach
the build, and a prompt without it hands the user a roadmap whose project-wide answers the downstream
skill will never see.

**Option B — one roadmap in one loop.** Tell the user first that `/loop` must be the literal first
thing in the message — it is their CLI's own loop command (Claude Code, Cursor, OpenCode all have
one), and it is already baked into the front of the prompt below, so it must be pasted as-is, not
retyped after a greeting. This skill never runs that loop itself; it only writes the prompt.

**Scope rule — one loop, one roadmap, in both modes.** `<ROADMAP-PATH>` and `<BUILD-ORDER-TXT>` are
single files: Step 6's table resolves them to the target section's pair, and that is exactly right.
Never widen this to every decomposed section, and never emit a list of pairs — there is one template
because there is one roadmap per loop.

The reason is structural, not tidiness. Inside one roadmap every dependency points backwards to a
feature in the same file (rule 4), so the whole order is knowable when the prompt is written. Across
roadmaps it is not: cross-section needs are boundary contracts whose producer names are *"provisional
until that section is decomposed"* (index-phase Step 4), decomposition is lazy by design, and a
section decomposed early is the one most likely to be built against names that have since moved. A
loop crossing that seam builds the next section against a plan the previous section's shipping has
already invalidated, with no one present to notice — and the loop's only evidence, a per-feature
PASS, cannot detect it. The seam is where the user re-seeds: this procedure re-runs from Step 1,
Step 3 recounts what is really done, and the next section gets its own loop over a roadmap that can
be corrected first.

Say all of this in the same breath as the prompt: which roadmap the loop builds, which sections it
does not, and that the next one is one re-seed away.

```
/loop Implement the roadmap at <ROADMAP-PATH>, one feature at a time, in the exact order of
<BUILD-ORDER-TXT>, using the `<downstream-skill>` skill for every feature — run its full cycle
(specify → design → tasks → execute → verify). This run covers <ROADMAP-PATH> and nothing else: no
other `docs/ROADMAP*.md` file is in scope, whatever <STATUS-PATH> lists.

`<current-feature>` below is this run's own variable, not a name to resolve once. At the start of
every iteration, re-read <BUILD-ORDER-TXT> and set it to the first name at or after `<target>` that
is not on the discharged list below and has no verified PASS in
`.specs/features/<current-feature>/validation.md`. Start that feature with:
`specify feature <current-feature> — create it at `.specs/features/<current-feature>/` using that
exact directory name, spec source: <ROADMAP-PATH>`. Do not skip a feature, do not reorder them, and
do not start the next one until the current one has that verified PASS. Exception — these features
are already discharged and must be skipped, never built: <DISCHARGED-LIST>.

Before each feature's gray-area discussion, read <STATUS-PATH> `## Cross-Cutting Decisions` and
treat every entry as settled — do not re-decide it, and keep every feature consistent with it.

No user is available for this run. When a gray area is not settled there, treat it as declined:
choose the default, record it with its rationale in that feature's spec under Assumptions & Open
Questions, and continue. Never stop to ask, and never leave one silently unrecorded.

Backlog position is at <STATUS-PATH> `## Status`. Stop when every name in <BUILD-ORDER-TXT> from
`<target>` onward has a verified PASS or is on the discharged list above; report and stop there
rather than continuing into another roadmap.
```

Three clauses in that template are load-bearing and easy to "tidy" into breakage. The
`<current-feature>` resume rule replaces a literal `Start at <target>`, because `/loop` re-reads the
whole prompt every iteration and a fixed start restarts at the same feature forever. The stop
condition says *"or is on the discharged list"* because a question-only feature can never earn a PASS
— without that clause the run either spins on it or fabricates a verdict. And the scope sentence
matters most in multi-section mode, where `<STATUS-PATH>` **is** `docs/ROADMAP-INDEX.md`, the file
listing every other roadmap: without it a diligent run finds the rest of the backlog and keeps going.
In single-section mode that clause is vacuously true and costs one line — keep it rather than
emitting a conditional template.

The two added paragraphs are what keep the run from stalling. The downstream skill triggers its own
Discuss automatically whenever a feature has any implicit dimension present — which, in a well-formed
roadmap, includes the very first feature, since decompose-phase Step 3 puts the shared persistence
foundation there. That discussion is interactive by design and offers no "skip all". Unattended, it
either hangs on a question nobody will answer or invents an answer and leaves no trace.

**The declined-gray-area instruction is not a workaround; it is that skill's own documented
fallback** — `tlc-spec-driven`'s discuss.md already routes any gray area the user declines or leaves
undiscussed into the spec's Assumptions & Open Questions with the agent's default and rationale,
*"never silently dropped"*. The loop prompt only states, up front, that every remaining gray area is
in that state. Confirm the wording against the confirmed downstream skill's own reference; if it
defines no such fallback, say so and do not invent one — offer option A instead.

**Resolve `<DISCHARGED-LIST>` before emitting, or the loop cannot terminate.** Phase 2 may formalize
a blocking open question as its own feature (decompose-phase Step 3). It is a normal feature name in
`<BUILD-ORDER-TXT>`, but it *"produces no code, so it can never earn a PASS `validation.md`"* — it is
discharged by its question reading `status: answered`, which is exactly what Step 9 just did to every
question. Left unnamed, the prompt orders the run to wait for a PASS that can never exist: it either
spins on that feature or fabricates a verdict to get past it. Walk `<BUILD-ORDER-TXT>` against Step
2's question-only test. `<BUILD-ORDER-TXT>` supplies the **name set**: **one** file, as Step 6's table
resolved it, from `<target>` to its end. It carries names only — no comments, no markers
(decompose-phase Step 8) — so look each name up in `<ROADMAP-PATH>` and keep the ones whose entry
carries Step 2's `discharge:` line; write `none` when there are none. It is singular in both modes
because the loop is (scope rule above). Names before `<target>` are behind the run, and names from
another section's `.txt` are not in this file and the run never reaches them — listing either only
sends the run looking for a feature it has no order for.

Point at the paths; never paste the roadmap's contents into the prompt — the files are on disk and
the run will read them, and an inlined copy goes stale the moment anything is edited. The sections
this loop does not cover are named in the surrounding message, never inside the prompt: the prompt is
an instruction to one run over one roadmap, and a list of roadmaps it must not touch is an invitation
to touch them. If the user's tool has no `/loop`, the body still works as a plain instruction — say
so, and say the run will then need supervising.

**Say where the loop's own decisions will be waiting.** Each gray area the cross-cutting ledger has
not already settled gets the run's default, recorded with its rationale in that feature's
`.specs/features/<name>/spec.md`, under its Assumptions & Open Questions section — one spec per
feature the loop builds. Tell the user, in the surrounding message, that reading those sections once
the loop ends is the next step this handoff expects and not extra work option B created: they are
where every call made on the user's behalf comes back, each with the reason it was made. Say it out
here only — the prompt already carries the instruction that writes them, and reviewing them is the
user's job after the run, not an instruction the run can act on.

**Then the session warning — both options, every time, unconditionally.** Do not omit it because the
option looked simple or the session felt short. Render it prominently, in the confirmed output
language:

> ⚠️ **Open a new chat session before running this prompt.** Paste it into a fresh session with clean
> context — not this one. This session is full of scope and decomposition reasoning that construction
> does not need; the downstream skill re-derives everything it needs from the paths in this prompt and
> the roadmap files on disk — and from `.specs/STATE.md` on any later `resume work`, which is what the
> Handoff is for. Building here risks the agent working from remembered conversation instead of the
> written artifacts, and it starts the build with the context budget already spent.

Then stop. Do not wait, do not poll `validation.md`, do not check back in — including under option B,
where the loop is the user's CLI running the downstream skill, not this skill continuing. If asked to
seed again later, this procedure simply re-runs from Step 1, and Step 1's evidence test is what keeps
it from clobbering real progress.

**Optional bridge, offered as text — never written automatically.** The downstream skill reaches
`docs/` only through its Knowledge Verification Chain, which names the directory and no file — and
the Handoff's own pointer is gone at the first `pause work`, since that section is overwritten. If
the project has a `CLAUDE.md`, offer the user these lines to paste into it (their file, their call):

```markdown
- `docs/ROADMAP-INDEX.md` `## Status` — current backlog position and the next feature to build.
- `docs/ROADMAP-INDEX.md` `## Cross-Cutting Decisions` — project-wide decisions already made with
  the user (deletion policy, auth model, failure handling, …). Read before discussing gray areas;
  treat as settled and keep every feature consistent with it.
- `docs/ROADMAP-*.md` — per-feature objective, scope-units, dependencies, flagged dimensions.
  Read the relevant section before specifying a feature.
```

In single-section mode both blocks are in `docs/ROADMAP.md`; adjust the paths accordingly. This
bridge is the durable half of the delivery: the Handoff's **Next step** carries the pointer for the
next feature only, while these lines make it reach every feature after it.
