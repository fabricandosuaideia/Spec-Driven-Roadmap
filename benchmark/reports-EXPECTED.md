# Answer key — the Step 2 completion test

**This file lives one level above [`reports/`](reports/) on purpose.** An executor was asked to
judge those files and grepped the directory; a key sitting beside them prints itself into the
run. That is the isolation rule this repository already learned once, at directory granularity —
seven runs under one parent, any of them able to read another's answers — reappearing at file
granularity. Give an executor the `reports/` path, never this one.

Thirteen `validation.md` reports, and what the completion test in
[`references/handoff-seed.md`](../references/handoff-seed.md) Step 2 must conclude about each.

**Why these exist.** Step 2 decides whether a feature is done, and the seed skips every feature it
calls done. A wrong `done` is the worst answer the skill can give: the loop builds on top of work
that never passed, and nothing downstream revisits it. The rule is prose an agent executes, so the
only way to know it works is to hand the prose and these files to an agent that has never seen either.

**These are inputs, not a project.** They sit outside [`fixture/`](fixture/) on purpose —
`run-benchmark.py` copies `fixture/` wholesale into a scenario, and these are not part of any project
tree.

## The reports

| file | expected | what it is there to catch |
|---|---|---|
| `en-pass-cited.md` | **done** | the happy path — every AC passes, verdicts green, evidence cited |
| `en-fail.md` | **not done** | a genuine FAIL that still carries `\| ✅ PASS \|` rows — the trap Step 2 opens by naming |
| `unfilled-template.md` | **not done** | the template shipped unfilled, both verdict words present |
| `en-pass-uncited.md` | **not done** | PASS asserted with no `path.ext:NN` anywhere — evidence-or-zero |
| `sensor-fail.md` | **not done** | the Discrimination Sensor failed and there is no consolidated verdict |
| `prose-aside-pass.md` | **done** | a finished feature whose prose contains `⚠️` mid-sentence |
| `pt-fail-translated.md` | **not done** | ← every AC passes; the failure lives **only** in a translated verdict |
| `pt-pass-translated.md` | **done** | a finished feature whose verdict words are not English |
| `es-fail-translated.md` | **not done** | the same shape as the Portuguese one, one language over |
| `no-verdict-lines.md` | **not done** | prose only — no heading, no verdict line, but `PASS` and a citation in the text |
| `heading-mark-only.md` | **not done** | the only mark is in the **title**, and no consolidated verdict exists |
| `pt-fail-mark-drifted.md` | **not done** | a real failure whose mark drifted off the verdict position |
| `sensor-pass-only.md` | **not done** | a green sensor is the **only** verdict line — mutants died, nothing else was verified |

## The five the rule used to get wrong

Recorded because a fixture with no known-wrong cases measures nothing.

`pt-fail-translated.md` and `es-fail-translated.md` are the expensive ones. Every acceptance
criterion passes and is cited, so the file contains `✅ PASS` rows and **not one occurrence of the
word `FAIL`**. The feature is unfinished for a reason that appears nowhere but the consolidated
verdict — `**Geral**: ❌ Não Pronto`, `**General**: ❌ No listo`. The old selection matched verdict
lines by the English literals `Result:`, `Overall:` and `Status:` only, so nothing was selected, the
whole-file fallback ran, and it found `PASS` with a citation and no `FAIL`: **done**. Failed work,
reported as finished, by the one path the step's own opening paragraph forbids.

`pt-pass-translated.md` is the mirror. Its title matched, its verdicts did not, so the selection
carried no verdict word at all and a **finished** feature came back unfinished.

`prose-aside-pass.md` is the fifth, and it fails the shipped rule for the opposite reason: its two
verdict lines carry `✅` and no English `PASS`, so the selection came back carrying no verdict word at
all and a **finished** feature read as unfinished. It is in the corpus as the false-positive control
for the current rule's tight selection, and it happens to be a known-wrong case as well.

`no-verdict-lines.md` is the fallback itself. The old text sent an unmatched report to a whole-file
read that could answer `done` — which is what the step forbids in its second paragraph and mandates
in its ninth. The rule contradicted itself, and the contradiction only fired on reports too irregular
to select from.

## The two added after the first execution

These three were added after the shipped rule had already been scored, so they are **not** part of
the 5-of-10 above; they were reasoned to rather than measured against it.

`heading-mark-only.md` and `pt-fail-mark-drifted.md` are the wrong-`done` paths the first execution
reasoned its way to without any fixture triggering them. Both are the dangerous direction, so both
were worth planting rather than trusting to prose.

The first asks whether a heading can carry a verdict. Rule 1 matches its word **anywhere** in a
heading, so `# pauta-item-archive Validation ✅` is selected — and if that mark scores, the file has
`PASS` and a citation and nothing contradicting it. The rule now says a heading selects the report
and never carries a verdict.

The second asks whether the permission to add a spelling is actually used. `**Geral**: Não Pronto ❌`
puts its mark last, so the positional selection rule does not see it, while its **passing** sibling
`**Situação**: ✅ Critérios cobertos` is mark-first and is selected. Read without adding `Geral:` to
the verdict labels, the file comes out `done` — a failed feature reported as finished. It is the
only fixture whose correct answer depends on a permission rather than on a pattern.

## The one added after the third execution

`sensor-pass-only.md` closes a hole the third execution named against itself. The rule says the
Discrimination Sensor's line *"can refuse a feature but never pass one"* — and the corpus tested only
the refusing half. `sensor-fail.md` exercises a red sensor; `en-pass-cited.md` exercises the
paragraph **not** firing, because `**Status**: ✅` and `**Overall**: ✅` sit beside the sensor. The
direction the clause was written for — a green sensor alone, with cited criteria and no consolidated
verdict — had no fixture, so the fix rested on reading rather than on running. That is the failure
this repository names first in its own lessons, committed while fixing something else.

The file is what the rule's opening paragraph condemns, made concrete: every mutant killed, an
acceptance criterion whose evidence is "reviewed by hand", and a green result.

## Four ways this rule can still say `done` about unfinished work

Named rather than left implicit, because a wrong `done` is the only direction that costs anything:
a wrong `not done` re-targets the seed at built work and a person sees it in the Step 7 report, while
a wrong `done` makes the loop build on top of work that never passed and nothing revisits it. All
four were constructed by agents executing the rule, and **none has a fixture** — writing one for each
is the next piece of work here.

1. **A verdict label the rule does not name, whose mark drifted off the verdict position, beside a
   green sibling that is mark-first.** `**Veredito**: Não Pronto ❌` above `**Situação**: ✅ …`. The
   positional selection rule cannot reach the failing line and the printed label list is English, so
   the only defence is the reader choosing to add the spelling. `pt-fail-mark-drifted.md` tests this
   shape — but with `Geral:`, a label the rule names in its own worked example, so what it proves is
   that a reader follows a worked example, not that the general permission works.
2. **A verdict expressed as a translated word with no mark at all**, beside a green mark-bearing
   sibling. Scoring is defined on `PASS`, `FAIL` and the marks that stand for them; a translated word
   is neither, so the failing line contributes nothing even when correctly selected. Without the
   green sibling the file falls to the fallback and its ceiling saves it — the danger needs the
   sibling.
3. **A green consolidated summary above a red acceptance-criterion row.** Table rows are excluded
   from selection by design, which is the right fix for the opposite error and creates the symmetric
   hole: the red row never scores. The rule stops looking at the table rather than declaring the
   consolidated verdict authoritative over it.
4. **A failure stated as a prose sentence** — *"a feature não está pronta; falta a integração de
   canal"* — beside a green labelled verdict. Nothing selects the sentence.

## What six executions left standing

The rule was executed six times against this corpus, the last two by readers instructed to work from
the ordered bullet list alone without hunting back through the surrounding prose — which is what a
reader under time pressure does, and which is where every dangerous residue turned out to live. The
final run was 13 of 13, unanimous on every file at 4-0.

One structural gap survives, and it is honest rather than fixable by wording: **the bullets
presuppose a step performed outside them.** Extending rules 1 and 2 with the report's own translated
verdict labels has to happen before the selection runs, because it changes what gets selected. The
list says so and now carries the test for it, but no bullet performs it. Skip that step and
`**Geral**: Não Pronto ❌` is never selected — rule 3 misses it because the mark is not first after
the colon — leaving its passing sibling as the only scoring line and answering `done` on failed work.
Every agent in the last two runs performed the step; none of them could have inferred its content
from the bullets alone before the test was moved into them.

## What this does not cover

The reports are written by someone who knows which rule is under test, so they sample the raggedness
somebody already named. The six title forms in [`state-scenarios.md`](state-scenarios.md) were
found by reading a real project for an afternoon, after nine releases of prose review found nothing —
these thirteen were not, and no count of them replaces reading real output.

Specifically untested here: a report that carries **no** mark and no English verdict word; mixed
scripts inside one report; a verdict expressed as a sentence rather than a labelled line; and any
form the downstream skill starts writing after this file was frozen.
