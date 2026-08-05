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
without re-deriving anything. That takes **two writes to two different files**, because they have
two different lifetimes:

1. **`## Status` in this skill's own roadmap file** — the durable backlog picture (every roadmap,
   what's done, remaining build order). Rewritten freely on every seed; nothing else owns it.
2. **`## Handoff` in `.specs/STATE.md`** — the downstream skill's own pause snapshot, in **its**
   exact schema, carrying a pointer back to (1).

Then it hands the user **one prompt** to start construction with — either one feature, or a `/loop`
run across the whole roadmap — and stops.

This is the entire extent of this skill's involvement in construction — no waiting for PASS, no
advancing to the next feature automatically, no re-invoking itself. Once this step reports, every
subsequent "specify feature", "resume work", pause, and verify belongs entirely to the downstream
skill's normal flow, driven by the user or the general agent.

## Two surfaces, two lifetimes

**Do not put the backlog picture in `## Handoff`.** For `tlc-spec-driven` (the default downstream
assumption), `references/memory.md` defines that section as a *"pause snapshot (~500 tokens,
overwritten each pause)"*, with a trigger table row reading `| Pause work / end of session |
## Handoff | Replace - overwrite Handoff section only |` and a pause procedure that replaces
"everything between `## Handoff` and the next `##` or EOF". Its template is **eight fixed fields**.
Anything extra written there survives exactly until the first `pause work` and is then gone, with no
mechanism that ever restores it.

The durable half therefore lives in a file this skill owns and the downstream skill never rewrites:

- **Multi-section mode** → a `## Status` block at the top of `docs/ROADMAP-INDEX.md`.
- **Single-section mode** → a `## Status` block at the top of `docs/ROADMAP.md`.

That location is reachable by the downstream skill: `tlc-spec-driven`'s Knowledge Verification Chain
Step 2 is *"Project docs → README, docs/, inline comments"*. It will not go there unprompted, which
is why Step 6's **Next step** field must name the path explicitly.

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

If work is in flight → **stop.** Do not write `.specs/STATE.md`. You may still refresh the `## Status`
block in `docs/` (Step 5) — that file is this skill's own and reflects the roadmap, not the session.
Report which feature is in flight and that the current position is unchanged.

If none hold — including when the Handoff is a stale snapshot naming a feature that is already
verified PASS, or is this skill's own earlier seed — it is safe to write. Continue.

## Step 2 — Determine which features are actually done

"Done" means a **real PASS**, not the presence of a file. A `validation.md` can exist while being
empty, still holding the unfilled `[PASS | FAIL]` placeholder, reporting FAIL, or asserting PASS with
no evidence. Worse, a genuine FAIL report normally contains per-criterion rows reading `| ✅ PASS |`,
so **never substring-match `PASS` across the whole file** — that reports failed work as done and
makes the seed skip past it.

**Precondition, before any test — check the directory exists.** If `.specs/features/<name>/` is not
on disk, the feature is **not done**. Stop there; do not run the gate script.

This is not a formality. `tlc-spec-driven`'s `validate_state.py` returns **exit 0 when
`.specs/features/` does not exist at all** (it prints "nothing to check" and exits before it ever
looks at the feature argument). A fresh project — the normal state when this skill runs, since it is
a prequel to the build cycle — would therefore report *every* feature as verified, and the seed would
conclude the whole backlog is finished and seed nothing.

**Then run the downstream skill's own gate.** `tlc-spec-driven` ships one:

```
python3 <skill-dir>/scripts/validate_state.py <feature> --root <project-root>
```

Read the result as: exit `0` **and** the feature directory existed = real PASS. Exit `1` = not done
(missing report, FAIL, unfilled placeholder, or PASS with no `file:line` evidence). Exit `2` = usage
error, most often the feature directory is missing — also not done. `<skill-dir>` is the downstream
skill's own directory, not the project's.

**Fallback, when no code execution is available.** Read only the `## Validation` heading line and any
`**Result**:` line — not the whole file:

- both `PASS` and `FAIL` on that line → unfilled template → **not done**
- `FAIL` → **not done**
- `PASS` with no `path.ext:NN` citation anywhere in the file → **not done**
- `PASS` with at least one such citation → **done**
- no `validation.md`, or no verdict at all → **not done**

**One exception — question-only features.** Phase 2 may formalize a blocking open question as its own
feature (decompose-phase Step 3). It produces no code, so it can never earn a PASS report and would
block the seed forever. Such a feature is **done** when the roadmap's `## Open Questions` shows its
question `status: answered`, or when `.specs/features/<name>/context.md` exists. Its roadmap entry
says it produces no code — that is what marks it as taking this test instead of the PASS test.

**Reading a `.txt`, always:** one feature name per line. Skip blank lines and any line starting with
`#`. Count and target only feature-name lines.

## Step 3 — Build the roadmap status list

One line per roadmap, so the whole backlog shape is visible — not a single disconnected pointer.

- **Single-section mode:** one line for `docs/ROADMAP.md`: how many of its features are done
  (Step 2's test) out of the total in `docs/roadmap.txt`.
- **Multi-section mode:** walk the topological list in `docs/ROADMAP-INDEX.md`'s **Ordering** section
  (its output-shape item 3) — that is build order; the roadmaps table is not necessarily sorted. For
  each section, read its **Build-order file** column to get the exact `.txt` filename (never
  reconstruct it from the slug), then classify:
  - all done → `DONE (X/X, verified PASS)`
  - some done → `IN PROGRESS (N/M verified PASS)`
  - none done, `.txt` exists → `NOT STARTED (0/M)`
  - no `.txt` yet → `NOT YET DECOMPOSED` — note what it depends on per the index

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

**Guard against name drift.** If a roadmap name has no `.specs/features/<name>/` directory but a
similarly-named one exists (`auth-login` vs. `auth-signin`), do not count it as unbuilt — that is
almost certainly the same feature built under a different name. Report the mismatch and stop, rather
than seeding a pointer that would rebuild shipped work.

**Do not assert what you did not check.** Step 6's template asks for `Completed` / `In-progress`. If
the target has partial work on disk (a `spec.md`, a `tasks.md` with unchecked boxes) but no PASS,
say so rather than writing `not started` — a confident falsehood in the machine-read handoff surface
is worse than a vague truth. If the target's `validation.md` reads FAIL, do not treat it as unstarted
either: name it as needing fixes.

If every feature in every decomposed roadmap is done, there is nothing to seed. Say so and stop —
never write a Handoff pointing at nothing, and never invent a "next" feature.

## Step 5 — Write the durable Status block (this skill's own file)

Insert or replace a `## Status` block immediately after the H1 of `docs/ROADMAP-INDEX.md`
(multi-section) or `docs/ROADMAP.md` (single-section). Replace only that block's body — leave the
rest of the file untouched.

```markdown
## Status

_Backlog position. Regenerated by spec-driven-roadmap; feature status is derived from
`.specs/features/<name>/validation.md`, never hand-edited here._

- `docs/ROADMAP-<slugA>.md` — DONE (4/4, verified PASS)
- `docs/ROADMAP-<slugB>.md` — IN PROGRESS (2/5 verified PASS)
  - **Remaining** (build order): `<feature-3>` → `<feature-4>` → `<feature-5>` (closes the roadmap)
- `docs/ROADMAP-<slugC>.md` — NOT STARTED (0/6) — next after `<slugB>` per this index
- `docs/ROADMAP-<slugD>.md` — NOT YET DECOMPOSED (depends on `<slugC>`)

**Next feature**: `<target>` — see `docs/ROADMAP-<slugB>.md` for its objective, dependencies and
flagged dimensions.
```

Single-section mode collapses the list to one line for `docs/ROADMAP.md` plus its own **Remaining**
sub-list.

Keep it to counts, names and paths. Never copy feature objectives or task lists here — that detail
already lives in the roadmap body below it.

## Step 6 — Write the Handoff (downstream skill's file, its exact schema)

Locate the `## Handoff` header in `.specs/STATE.md` and replace only the body between it and the
next `##` or EOF. Never touch `## Decisions`. If the file does not exist, create it in the shape the
downstream skill prescribes — for `tlc-spec-driven`, an H1 `# STATE`, then `## Decisions` with an
empty body, then `## Handoff`.

Emit **only** the fields that skill defines. For `tlc-spec-driven` v3.x, exactly these eight:

```markdown
## Handoff

- **Feature**: <target feature name>
- **Phase / Task**: not started — no spec.md on disk yet
- **Completed**: none
- **In-progress** (file:line): none
- **Next step**: specify feature `<target>` — create it at `.specs/features/<target>/` using that exact directory name. Spec source: `<ROADMAP-PATH>` section `<target>` (objective, scope-units, dependencies, flagged dimensions and open questions are there — read it before clarifying). Backlog position: `<STATUS-PATH>` `## Status`.
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: <output of `git branch --show-current`>
```

**Resolve the two path placeholders by mode** — writing an index path in single-section mode points
at a file that does not exist:

| Placeholder | Multi-section | Single-section |
|---|---|---|
| `<ROADMAP-PATH>` | `docs/ROADMAP-<slug>.md` | `docs/ROADMAP.md` |
| `<STATUS-PATH>` | `docs/ROADMAP-INDEX.md` | `docs/ROADMAP.md` |
| `<BUILD-ORDER-TXT>` | `docs/roadmap-<slug>.txt` (from the index's **Build-order file** column) | `docs/roadmap.txt` |

Notes on the fields that carry real weight:

- **Next step** is the highest-value field in this file: it is the one place both the downstream
  skill's resume *and* the human read. It must carry (a) the trigger phrase confirmed at Phase 0,
  (b) the exact directory name so the built feature matches the roadmap's name, and (c) the roadmap
  path. Without (c) the entire Phase 2 output — objective, scope-units, dependencies, sizing,
  dimensions — reaches nothing, and the user gets re-interviewed on scope this skill already
  resolved.
- **Branch** is unconditional. Obtain it with `git branch --show-current`; use `none` only outside a
  git repo.
- **Uncommitted files** — report what `git status --porcelain` actually shows, not a blind `none`.
  The downstream skill's resume reconciles this field against git, so a false `none` is a claim it
  will catch and have to work around.
- **Blockers** — if the target feature has `needs pre-written context.md: yes` **and** a question
  tagged `status: open` in its `open questions` field (or an unresolved marked-open item in a
  boundary contract it consumes), put the exact question here instead of `none`, and set **Next
  step** to answering it rather than the specify trigger. Treat the question as resolved if the
  roll-up entry reads `status: answered` or `.specs/features/<target>/context.md` already exists.
  Never point a fresh start past an unanswered question.

Keep the whole section near the downstream skill's ~500-token budget. The backlog picture is not
repeated here — Step 5's file holds it, and **Next step** points at it.

## Step 7 — Report the outcome

Tell the user, plainly:

- that roadmap generation is finished — this is the moment the planning work closes;
- the roadmap status list from Step 3, one line each;
- which feature was seeded as next — or that nothing was seeded, and why (work in flight / nothing
  left / blocked on an open question);
- that construction from here on is the downstream skill's own job, through its own triggers.

Then go to Step 8 — **unless** any of these hold, in which case there is no prompt to hand over and
this procedure ends here:

- **Nothing was seeded** (work in flight, or every feature already done). There is no target to
  build; offering a prompt would point at nothing.
- **No downstream skill exists** (Phase 0 recorded its absence). Say the roadmap is complete and
  name what to install to build from it; there is no trigger to put in a prompt.

A blocker recorded in Step 6 does **not** end it here — Step 8 is still offered, because option B
exists precisely to close blocking questions.

## Step 8 — Ask which implementation prompt to hand over

The roadmap is done and the user now has to actually build from it. There are two legitimate ways to
drive that, and **which one is the user's call — never pick for them, and never default to the loop
because it looks faster.** Ask, in the confirmed output language:

- **Option A — one feature at a time.** They get the prompt for `<target>` only, run it, and come
  back for the next feature when it passes. Full control, a checkpoint per feature.
- **Option B — one `/loop` run over the whole roadmap.** The build does not stop until every feature
  in the backlog is verified PASS. State the precondition up front: **the roadmap must have zero open
  questions**, because a loop has no one to ask. If any remain, you will interview them closed first,
  and only then produce the prompt.

If Step 6 recorded a blocker, say so here: option A cannot give a clean start command until that
question is answered, and option B's sweep is what answers it.

Option A → skip to Step 10. Option B → Step 9.

## Step 9 — Loop option only: close every open question first

*Only when the user chose option B.*

A loop runs unattended. Every ambiguity rule 1 refused to guess is a place the run would either stall
or silently guess — so all of them get closed **before** the prompt exists. Announce that first: say
you will read the roadmap for gaps, and that the roadmap must be complete before you can hand over a
loop prompt.

**1. Sweep every decomposed roadmap, in full.** Not just the target's section, and not just the
target feature — the loop will run past all of them without stopping.

- Single-section mode: `docs/ROADMAP.md`.
- Multi-section mode: every `docs/ROADMAP-<slug>.md` that exists — i.e. every section Step 3 did not
  classify `NOT YET DECOMPOSED`.

Read each file top to bottom. Collect open questions from **both** places they live: each feature's
`open questions` field, and the `## Open Questions` roll-up. They can disagree — a question present
in one and missing from the other is still an open question, and the roll-up is the half the loop
prompt's reader is least likely to check.

**Sections that are `NOT YET DECOMPOSED` cannot be covered by the loop.** Decomposing them is a
Phase 2 run, and this skill never marches through phases on its own (rule 9). Say plainly which
sections the loop prompt will *not* build, so the user does not read "loop until done" as "loop until
the whole product exists".

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

**3. Write each answer back, in both places.** For the feature that carries the question: retag its
`open questions` line `status: answered` and write the answer inline. For the `## Open Questions`
roll-up: the same, on that question's entry. Answered entries are never deleted (decompose-phase
Step 7). Then re-evaluate that feature's **needs pre-written context.md** — it stays `yes` if any
implicit dimension is still present, and flips to `no` only when the open question was its sole
cause.

**Stay inside the question.** Do not re-open scope-units, dependencies, sizing, or task estimates
from an answer. If an answer genuinely invalidates the decomposition — it reveals a scope-unit no
feature covers, or breaks a dependency edge — stop and say Phase 2 has to be re-run for that
roadmap, under its own "When to re-run, and what is frozen" rules. Never quietly patch a
decomposition inside this step.

**4. Re-read from disk before speaking to the user again.** When the last answer is written, read
every swept roadmap file again, top to bottom, from disk — not from your memory of the interview.
Confirm no `status: open` survives anywhere, in either place. If one turns up (the usual cause is a
roll-up and a feature field that were out of sync), close it and re-read again. Repeat until a full
read comes back clean. Do not report "no gaps" on the strength of having asked the questions; report
it on the strength of having re-read the files.

**5. Recompute the seed if anything moved.** Closing a question can discharge a question-only feature
(Step 2's exception), which changes the target and the remaining order — and it clears the Step 6
**Blockers** field. If any question was closed, re-run Steps 2–6 before emitting the prompt, so the
`## Status` block and the Handoff cannot contradict the prompt you are about to hand over.

## Step 10 — Hand over the prompt, warn about the session, stop

Give the prompt **verbatim, in one copy-paste block** — the downstream skill is entered by the user
typing its trigger, so a paraphrase is a broken handoff. Resolve every placeholder against Step 6's
table. Write the prose in the confirmed output language, but keep trigger phrases, feature names and
file paths exactly as they are on disk.

`specify feature` in both templates below is `tlc-spec-driven`'s trigger. If Phase 0 confirmed a
different downstream skill, substitute **its** fresh-start trigger phrase — the same one Step 6's
**Next step** carries. A prompt built on a trigger the installed skill does not answer to is inert.

**Option A — one feature:**

```
specify feature <target> — spec source: <ROADMAP-PATH>
```

*Unless Step 6 recorded a blocker.* Then give no command at all: report the question that has to be
answered first, so the user is not handed a command that would start a feature that cannot start
cleanly.

**Option B — the whole roadmap in one loop.** Tell the user first that `/loop` must be the literal
first thing in the message — it is their CLI's own loop command (Claude Code, Cursor, OpenCode all
have one), and it is already baked into the front of the prompt below, so it must be pasted as-is,
not retyped after a greeting. This skill never runs that loop itself; it only writes the prompt.

```
/loop Implement the entire roadmap at <ROADMAP-PATH>, one feature at a time, in the exact order of
<BUILD-ORDER-TXT>, using the `<downstream-skill>` skill for every feature — run its full cycle
(specify → design → tasks → execute → verify), starting each feature with:
`specify feature <name> — spec source: <ROADMAP-PATH>`. Start at `<target>`. Do not skip a feature,
do not reorder them, and do not start the next one until the current one has a verified PASS in
`.specs/features/<name>/validation.md`. Backlog position is at <STATUS-PATH> `## Status`. Stop only
when every feature in <BUILD-ORDER-TXT> has a verified PASS.
```

Point at the paths; never paste the roadmap's contents into the prompt — the files are on disk and
the run will read them, and an inlined copy goes stale the moment anything is edited. In
multi-section mode, list each decomposed section's `<ROADMAP-PATH>` / `<BUILD-ORDER-TXT>` pair in
index order and name the sections the loop does not cover. If the user's tool has no `/loop`, the
body still works as a plain instruction — say so, and say the run will then need supervising.

**Then the session warning — both options, every time, unconditionally.** Do not omit it because the
option looked simple or the session felt short. Render it prominently, in the confirmed output
language:

> ⚠️ **Open a new chat session before running this prompt.** Paste it into a fresh session with clean
> context — not this one. This session is full of scope and decomposition reasoning that construction
> does not need; the downstream skill re-derives everything it needs from `.specs/STATE.md` and the
> roadmap files on disk, which is exactly what the Handoff and the paths in the prompt are for.
> Building here risks the agent working from remembered conversation instead of the written
> artifacts, and it starts the build with the context budget already spent.

Then stop. Do not wait, do not poll `validation.md`, do not check back in — including under option B,
where the loop is the user's CLI running the downstream skill, not this skill continuing. If asked to
seed again later, this procedure simply re-runs from Step 1, and Step 1's evidence test is what keeps
it from clobbering real progress.

**Optional bridge, offered as text — never written automatically.** The downstream skill only reaches
`docs/` through its Knowledge Verification Chain, not by default. If the project has a `CLAUDE.md`,
offer the user these lines to paste into it (their file, their call):

```markdown
- `docs/ROADMAP-INDEX.md` `## Status` — current backlog position and the next feature to build.
- `docs/ROADMAP-*.md` — per-feature objective, scope-units, dependencies, flagged dimensions.
  Read the relevant section before specifying a feature.
```
