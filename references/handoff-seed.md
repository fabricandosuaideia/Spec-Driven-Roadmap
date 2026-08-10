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
- [Steps 8-10 — handing over a prompt](#steps-8-10--handing-over-a-prompt) — in [handover-prompt.md](handover-prompt.md)

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

**How to find `<skill-dir>`, because nothing else says.** A real run reported "no downstream skill
installed" and skipped the whole seed while `tlc-spec-driven` sat on disk in two places — the check
had nowhere to look. Search these, first hit wins, and say which one answered:

1. `<project-root>/.claude/skills/<name>/SKILL.md` — a project install, what Claude Code loads first.
2. `~/.claude/skills/<name>/SKILL.md` — a global install.
3. `~/.claude/plugins/**/<name>/**/SKILL.md` — a plugin install; take the highest version present,
   and ignore any directory carrying an `.orphaned_at` marker.
4. `~/.cache/agent-skills/skills/<name>/SKILL.md` — where
   `npx @tech-leads-club/agent-skills install` puts it, which is the command this project's own
   README prescribes for installing `tlc-spec-driven`. Two independent runs had to abandon the
   procedure and `find` for it because this line was missing.
5. The path the user gave, if they named one.

**If none of the five hits, search before concluding.** `find ~ -maxdepth 6 -name SKILL.md -path
"*<name>*"` costs one command and is the difference between a seed and a skipped one. The list above
is what is known to exist today, not a proof of what exists.

**Absence is a finding, not a default.** Report which paths you looked in before concluding nothing
is installed — Phase 0's "generate the roadmap anyway" branch and Step 6's skip both hang off that
conclusion, and reaching it without looking discards the entire handoff for a skill that was there.

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

Collect three kinds of line. The selection is case-**in**sensitive:

1. a **heading** (1-4 `#`) whose text contains `Validation`, `Validação`, `Validación`, `Verifier`,
   `Verificação`, `Verificación` or `Verificador` anywhere in it;
2. a line containing `Result:`, `Overall:` or `Status:`, with or without the `**`;
3. a line shaped **`**<anything>**:` immediately followed by a `✅`, `❌` or `⚠️`** — the mark is the
   first non-space character after the colon, not merely somewhere on the line.

**Rule 3 is the one that does not depend on spelling, and it exists because rules 1 and 2 do.** The
downstream skill's own guidance contemplates writing the artifact in Portuguese
(`references/coding-principles.md`), and the two consolidated verdicts in its template are
`**Status**: ✅ All ACs covered / ❌ Gaps present` and `**Overall**: ✅ Ready | ⚠️ Issues | ❌ Not
Ready` — a label, a colon, then the mark. Translate the label and rule 2 stops matching; the mark
survives translation, so rule 3 still selects the line.

**Why "immediately after the colon" and not "anywhere on the line".** The looser form selects prose
asides — `**Note**: the suite is ⚠️ slow` would fail a finished feature. The template puts the mark
first, so the tight form keeps every real verdict and drops the commentary. It also leaves the
acceptance-criteria rows out on its own: `| AC-1 | … | ✅ PASS |` is a table row, not a bold label,
and those rows are exactly what this step opened by refusing to match.

**Before applying the selection, extend its lists — this is a step, not a permission.** Read
the report's own bold labels and headings first, and add to rules 1 and 2 every one that is plainly
one of these words in the report's language. The literals printed above are **observed, never
complete**: they are the spellings somebody has seen, and the next project writes one nobody wrote
down.

The test for adding one is narrow, but it is about **which concept**, not which of three English
words. A label qualifies when it states the report's own overall judgement of the feature — `Result`,
`Overall`, `Status`, `Verdict`, `Conclusion` and their translations all do. It does not qualify when
it names a document, a section or an activity. `Situação:`, `Estado:`, `Geral:`, `General:`, `Resultado:`, `Veredito:`, `Veredicto:` and
`Conclusão:` qualify; `Relatório:` is *Report*, `Resumo:` is *Summary* and `Comprobación:` is *Check*
— those name the artifact or the act, not the judgement, so none of them does. The same test governs
rule 1's headings. Reading this as a closed list of three English words is what let
`**Veredito**: Não Pronto ❌` go unselected on a report that said in its own words it was not ready.
Name every spelling you added when you report, and treat skipping this step as skipping the test:
`**Geral**: Não Pronto ❌` beside `**Situação**: ✅ Critérios cobertos` reads as a finished feature
until `Geral:` is on the list. What you may not do is
stop at the list and conclude the report carries no verdict — the list is a floor, not a quota.

**On a selected line, a mark counts as the verdict word it stands for:** `✅` reads as `PASS`, `❌`
and `⚠️` read as `FAIL`. Without this the test only half works in translation — `❌ Não Pronto`
would be caught while `✅ Pronto` would not, and a **finished** feature written in Portuguese would
come back as unfinished for having no English `PASS` in it.

A mark counts **wherever it sits on a scoring line**, not only right after the colon — and a
heading is never a scoring line, so a `✅` in a title scores nothing. That is the loose reading and it
is deliberate: `**Status**: ✅ All ACs covered — ⚠️ flaky suite` comes out as a
failure. Scoring marks by position would be more precise and would cost more than it buys — an
incidental mark then stops vetoing, and the verdict it stops vetoing is one that says something is
wrong. Errs toward `not done`, which is the error this test is built to prefer.

**Selection is positional; scoring is not, and the two are different jobs.** Rule 3 is tight because
it has to decide *whether a line is a verdict at all* using nothing but its shape. Once a line is in,
its label has already been recognised, so there is no longer anything to protect against.

**A heading selects the report; it never carries a verdict.** Rule 1 finds the file's subject, and a
heading matches on one word appearing anywhere in it — which also pulls in interior section headings
like `## Verificação de Portão`. Score no mark and no verdict word found in a heading. Otherwise
`# pauta-item-create Validation ✅` plus any citation reads as **done** with no consolidated verdict
anywhere in the file, which is the wrong direction.

**When you recognise a verdict label, select its whole line under rule 2, wherever its mark sits.**
Rule 3's positional test is a net for labels you could not recognise, so it drops a real verdict
whose mark drifted — `**Geral**: Não Pronto ❌`, `**Geral**: **❌ Não Pronto**`. The permission above
to add a spelling is what catches those: once `Geral:` is on rule 2's list, the line comes in whole
and its mark counts. The Verifier writes prose and prose varies, and a mark that is not first is
exactly the variation to expect.

**A `path.ext:NN` citation** is a filename carrying an extension, then a colon, then a line number —
`api/app/routers/items.py:42`. It counts anywhere in the file, including inside an evidence column,
because that column is where the Verifier is told to put it.

**What follows scores only the selected lines that can carry a verdict, which never includes a
heading.** A heading was selected to identify the report; it contributes no word and no mark to any
bullet below. Read the bullets without that sentence and a title such as
`# pauta-item-archive Validation ✅` satisfies them on its own.

Then judge **case-sensitively**, on the whole words `PASS` and `FAIL` and on the marks that stand for
them, taking the first of these that matches. Two definitions the bullets use and cannot be applied
without:

- **A scoring line** is a selected line that is **not a heading**. Headings were selected to identify
  the report and contribute no word and no mark to any bullet — otherwise a title reading
  `# pauta-item-archive Validation ✅` satisfies the `done` bullet by itself, on a report carrying no
  verdict anywhere.
- **A `path.ext:NN` citation** is a filename carrying an extension, then a colon, then a line
  number — `api/app/routers/items.py:42`. Prose like *"reviewed by hand"* is not one. It counts
  anywhere in the file, evidence columns included, because that is where the Verifier is told to put
  it.
- **The lists are already extended.** If you have not yet added the report's own translated verdict
  labels to rules 1 and 2, stop and do that before reading further; half these bullets score lines
  that only exist once you have. The test is narrow — the word must be *that word* translated, not a
  different word sitting near it. `Situação:`, `Estado:`, `Geral:`, `General:` and `Resultado:`
  qualify; `Relatório:` is *Report* and `Comprobación:` is *Check*, so neither does.

- a scoring line offering **two or more verdicts as choices** — separated by `|`, or wrapped in
  `[ ]`, as in `[PASS | FAIL]` and `✅ Ready | ⚠️ Issues | ❌ Not Ready` — is the template with
  nobody's answer in it → **not done**. **The separator is the test**, not the count of verdict
  tokens: `PASS ✅` is one verdict said twice and `**Overall**: ✅ Ready | 0 blockers` offers one, so
  neither is an unfilled template.
- a `FAIL`, a `❌` or a `⚠️` on any scoring line → **not done**, whatever any `PASS` says
  elsewhere. `FAIL` is the whole word in capitals, so the `0 failed` of a Gate Check count is not
  one — that line reports how many tests failed, not a verdict.
- **at least one** `PASS` or `✅` on a scoring line and no `FAIL` or mark against it, with no
  `path.ext:NN` citation anywhere in the file → **not done**
- a `PASS` or a `✅`, and the **only** scoring line is the Discrimination Sensor's `Result:` — the
  one reporting a mutant count in the shape `N/N killed`, whatever the section around it is called
  → **not done**. That line reports whether mutants died, not whether the feature is done, so it can
  refuse a feature and never pass one. Without this bullet the next one answers `done` on exactly the
  report this step opened by condemning: every mutant killed, an acceptance criterion with no
  evidence, and a green result. A sibling `**Status**: ✅` or `**Overall**: ✅` is also a scoring line,
  so this bullet does not fire merely because the sensor's is the only line spelling `PASS` in letters.
- an acceptance-criteria row carrying a `FAIL`, a `❌` or a `⚠️` → **not done**. **This is the one
  bullet that reads the table rows, and it is deliberate** — every other bullet scores selected lines,
  and the rows are not selected. Read them here anyway, for refusal only: **those rows can refuse a
  feature and never pass one** — the same asymmetry as the sensor, and for the same reason.
  They are kept out of the selection because a genuine FAIL report is full of `| ✅ PASS |` rows, so
  letting them establish a pass is what this step opened by refusing. Letting a red one *refuse* costs
  nothing and closes the mirror hole: a green summary sitting above `| AC-3 | not implemented | ❌ FAIL |`
  used to read as **done**, unanimously.
- **anything anywhere in the file saying this work is unfinished** → **not done**, and name the
  sentence that decided it. Read the whole file for this one; it is the only bullet that looks past
  the scoring lines. Three shapes reach this point with every other condition satisfied and their own
  text saying the opposite: a verdict line the selection could not reach
  (`**Veredito**: Não Pronto ❌`), a translated verdict carrying no mark (`**Geral**: Não Pronto`), a
  plain sentence (*"a feature não está pronta"*). **This bullet runs in one direction only** — it can
  withhold a `done`, never grant one — so it cannot resurrect the whole-file `PASS` match this step
  opened by forbidding.
- **at least one** `PASS` or `✅` on a scoring line, no `FAIL` or mark against it, and at least one
  `path.ext:NN` citation → **done**
- no scoring line carried a verdict word or a mark at all → **not done**, and take the reason to
  record from the fallback below. This bullet is why the two above say *at least one*: read them as
  satisfiable by the absence of any verdict and they swallow this case, and a report with no verdict
  and an incidental citation comes out `done`.

**The sensor's line is the `Result:` one reporting a mutant count** — `3/3 killed`. A `FAIL ❌`
there is decisive: a suite that cannot tell a mutated implementation from the real one has verified
nothing. That is why the bullet above it exists, and why it sits *inside* the ordered list — an
exception written after a list whose first line says "the first of these that matches" is an
exception most readers never reach.

**Every tie in this test breaks toward `not done`, on purpose.** The two errors are not symmetric.
Reading a finished feature as unfinished re-targets the seed at built work — visible in the Step 7
report, and a person catches it in one glance. Reading a failed feature as finished makes the seed
skip past it, and the loop builds on top of work that never passed; nothing downstream ever revisits
it. Prefer the recoverable error, and say which one you took.

**A `done` has to survive one last read of the whole file.** Before recording it, read the report
end to end and ask one question only: **does anything here say this work is not finished?** A verdict
line the selection could not reach — `**Veredito**: Não Pronto ❌`, whose label is a word no list
names and whose mark drifted off the verdict position. A translated verdict carrying no mark at all,
`**Geral**: Não Pronto`, which is neither `PASS` nor `FAIL` nor a mark and so scores nothing. A plain
sentence: *"a feature não está pronta; falta a integração de canal."* Any of those turns the answer
into **not done**, and you say which sentence did it.

**This reads in one direction only, and that is what makes it safe.** It can turn a `done` into a
`not done` and never the reverse, so it cannot resurrect the defect this step opened by forbidding —
that was matching `PASS` across the whole file, which reports failed work as finished. This is
reading the whole file for evidence of *failure*, which is the opposite error and the recoverable
one. It also uses the one thing you have that a pattern does not: you can read. Every shape above was
found by executing this rule against a report built to carry it, and all three came back **done**
before this paragraph existed.

**When nothing selected carried a verdict — the fallback, and its one restriction.** That is the
case whether the selection matched no line at all, or matched only a heading — which selects the
report and scores nothing. Keying this on *matching* rather than on *scoring* is what made an earlier
draft claim two different conditions were one. Read the whole
file's text by the same rules, but the whole-file read may conclude **`not done`, never `done`**.
Concretely: where that read would have answered `done`, answer **`not done — no locatable verdict`**
instead. It is a real verdict with a stated reason, not a refusal to answer, and the reason is what
tells a reader afterwards that the rule never found what it was looking for.
This step opened by forbidding a whole-file `PASS` match, because a genuine FAIL report normally
carries per-criterion `| ✅ PASS |` rows; a fallback allowed to answer `done` would do exactly what
that sentence forbids, on precisely the reports too irregular to select from. Name the feature that
fell back, and why, in the Step 7 report — a degraded path that decides silently is indistinguishable
from one that worked.

Two traps in that file, both verified against `tlc-spec-driven` v3.x's `references/validate.md`. Its
persisted report is titled `# <feature> Validation` — the word comes *last*, so it fails a naive
starts-with test. **And the template is not what a real project contains.** One six-month project on
disk carried six distinct title forms across its reports — `# <feature> Validation`,
`# <feature> — Validação`, `# <feature> — Verifier Report`, `# Validation Report — <feature>`,
`# Validation: <feature>`, `# Validação — <feature>` — because the Verifier writes prose and prose
varies. Four of the six fail a starts-with test, and the Portuguese one contains no `Validation` at
all, which is why the selection above matches the word **anywhere** in the heading and accepts the
translated and `Verifier` spellings.

**Six is the count somebody wrote down, not the count that exists.** Those six came from reading one
project for one afternoon; the seventh is already predictable, because that same list translates
`Validation` into three languages while leaving `Verifier` in English only. A Portuguese project
writing `# <feature> — Verificação` was never covered, and the same asymmetry ran through the verdict
lines: `Result:`, `Overall:` and `Status:` are English, so a translated verdict fell through to the
fallback — where per-criterion `| ✅ PASS |` rows plus one citation made a **failed** feature read as
done. That is why rule 3 keys on the mark rather than the word, and why the fallback may no longer
answer `done`. `## Validation: <feature> — PASS/FAIL` is the Verifier's **chat** summary and is never
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
  will catch and have to work around. Outside a git repo that command errors rather than returning
  an empty list, so there is nothing to report: write exactly `none — not a git repository`. The
  annotation is what keeps the field honest — a bare `none` there is indistinguishable from the
  false one this bullet forbids.
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

---

## Steps 8-10 — handing over a prompt

They live in [handover-prompt.md](handover-prompt.md): Step 8 asks which prompt the user wants, Step
9 closes every open question when they chose the loop, and Step 10 emits it and stops. Go there **only
from Step 7**, and only when its exit list did not end the procedure — with nothing seeded, or Step 6
skipped, there is no prompt to hand over and this file is where the run finishes.
