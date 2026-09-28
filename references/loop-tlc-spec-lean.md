# The `/loop` template — `tlc-spec-lean`

Read this file **only** when Step 8's answer was option B and the downstream profile Phase 0 confirmed
(or the seed detected) is `tlc-spec-lean`; the other profile's template is in its own file, and a run never
needs both. Everything that governs *how* to emit it — the placeholder table, the scope rule,
`<DISCHARGED-LIST>`, `<SUBAGENT-DISPOSITION>`, and why each clause is load-bearing — stays in
[handover-prompt.md](handover-prompt.md) Step 10, which sent you here. Emit the block below verbatim,
placeholders resolved as that table says.

**Option B, `tlc-spec-lean`'s template.** Same scope rule, same `<current-feature>` discipline, same
placeholders — what differs is the cycle it drives, what "done" means, and every stop it disposes of.
Its differences from the template above are exactly these: the cycle is **plan → checks → build →
verify** with no Discuss, design or task list; the human stop is the **end of Plan**, not a Discuss;
the gate is `validate_verification.py`, which reads a `**Verdict**:` line and refuses a PASS its own
rows contradict, so there is no verdict-format workaround to carry; and the Verifier is a fresh
sub-agent that the run dispatches and does not write itself.

```
/loop Implement the roadmap at <ROADMAP-PATH>, one feature at a time, in the exact order of
<BUILD-ORDER-TXT>, using the `<downstream-skill>` skill for every feature — run its full cycle
(plan → checks → build → verify). This run covers <ROADMAP-PATH> and nothing else: no other
`docs/ROADMAP*.md` file is in scope, whatever <STATUS-PATH> lists.

`<current-feature>` below is this run's own variable, not a name to resolve once. At the start of
every iteration, re-read <BUILD-ORDER-TXT> and set it to the first name at or after `<target>` that
is not on the discharged list below and has no verified PASS in
`.specs/features/<current-feature>/verification.md` — verified means the gate described further down
exits 0, never the word PASS found in the file (a refused report still says `**Verdict**: PASS`). Start that feature with:
`specify feature <current-feature> — create it at `.specs/features/<current-feature>/` using that
exact directory name, plan source: the <ROADMAP-PATH> entry <current-feature>`. If that directory
already exists, the feature is partly built: read its artifacts and its report first, fix what the
report refuses, and do not start the plan over. Do not skip a feature, do not reorder them, and
do not start the next one until the current one has that verified PASS. Exception — these features
are already discharged and must be skipped, never built: <DISCHARGED-LIST>.

Before each feature's plan, run
`python3 <ROADMAP-SKILL-DIR>/scripts/feature-brief.py <current-feature>` and work from its output: the
feature's entry, its risk tier and what that tier sets for this skill (follow it), the questions naming it, the contracts it consumes, and `## Cross-Cutting Decisions`,
which are settled — do not re-decide them, and keep every feature consistent with them. Never open
<ROADMAP-PATH> or <STATUS-PATH> whole: each is shared by the whole backlog and you would carry all of
it on every later turn. If the script cannot run, read only the `### <current-feature>` entry and the
lines that name it.

No user is available for this run. Dispose of every stop as follows and never wait for an answer,
but never leave one silently unrecorded either:

- A decision the plan needs that `## Cross-Cutting Decisions` does not settle — choose the default and
  record it in that feature's `plan.md` under `## Assumptions`, with its rationale and `Confirmed?`
  set to `n`. That table is where that skill already puts a decision the user did not make.
- The stop at the end of Plan, where that skill presents the plan for a human to confirm before any
  check exists — approve and continue, and write in that same `## Assumptions` section that the plan
  was self-approved. Do the same for `checks.md`. Nobody reviewed them, and that line is what lets
  somebody review them later.
- **The size gate and the Verifier**, the two places that skill uses sub-agents.
  <SUBAGENT-DISPOSITION> Say which you took, in that feature's `checks.md` under `## Handoff`. Read
  that skill's own build and verify references from disk for the budget and the dispatch rule — they
  are its numbers and its rule, not this prompt's, and they move between its versions.
- Any other choice about how to execute — ordering inside a feature, how much to do before checking —
  pick one, say which, continue.
- A project-level fact the run cannot invent, such as which test framework to use — take it from
  `## Cross-Cutting Decisions`; if it is not there, record it as an open question and choose the most
  conservative option that exists in the repository already. Never invent a credential and never
  reach a network service to resolve one. That skill's blast-radius rule stands: local edits and local
  commits only — never `git push`, never a deploy, never a change to production data.
- A failing test — never edit, weaken, skip or delete a test to reach a PASS, **and never add one
  either**. A new test asserting the opposite of the failing one leaves the suite holding two
  contradictory claims about the same input and manufactures the look of coverage; the prohibition
  covers adding for the same reason it covers editing. Never record a feature as done while its
  suite is red. If a test is genuinely wrong, leave it failing and write
  down why. This is the one stop where continuing costs more than halting: a verified PASS is the
  only evidence this run produces, and a test bent to produce it destroys the evidence rather than
  the defect.
- **The same forgery from the implementation side is also forbidden, and it is the one that hides.**
  Never change behaviour in a way that contradicts an acceptance criterion or a settled
  `## Cross-Cutting Decisions` entry in order to turn a test green. Inverting a rule usually satisfies
  the assertion, leaves `tests/` untouched, and arrives in a diff of the source carrying no label that
  says what was traded away. When the only implementations that pass are ones the spec forbids, that
  is a genuinely wrong test: leave it red and say which criterion each rejected implementation
  violated.
- **A check is fixed once approved, and this run approves its own.** That skill's rule is that a
  genuinely wrong check is a stop-and-ask, never an edit; an unattended run cannot ask, so it stops
  that feature instead. Where a check's proof can only go green by bending behaviour, or a roadmap
  entry claims `open questions — none` while an unanswered one blocks the work, do not edit the
  check to fit: record in `## Assumptions` which check you refused to satisfy and why, leave it red,
  and let the rule below end the run.

**A feature counts as done only when `validate_verification.py <current-feature> --root <PROJECT-ROOT>`
exits 0** — run from that skill's own directory — **and its `verification.md` carries
`**Verdict**: PASS` with at least one `file:line` citation.** Exit `2` means the gate found nothing to
read: that is not done, and it is never a pass. Never pass `--allow-empty`. Never decide this by
searching the report for `PASS`: a failed report is full of `PASS` rows.

**The Verifier writes `verification.md`; you do not.** Dispatch it as that skill's verify reference
prescribes, after the last commit of the feature, in the same turn, over every check. A FAIL is
written the way a PASS is — `**Verdict**: FAIL` at the top, `FAIL` in the `Result` cell of each
check that failed — and no heading or label of your own invention.

**Nobody is reviewing this run, so say what its PASS is.** The plan and the checks were approved by
this run itself, and a fresh sub-agent that read them is independent of the builder but is the same
kind of reader. A PASS this run records is evidence that the suite was green and that a second reader
found nothing against the checks — not that any person agreed. Name the artifacts you self-approved
in each feature's `## Assumptions`.

**When that skill's own loop cannot terminate, this instruction ends it.** It treats a red gate as
*stop, fix, re-run* — correct in general, and a deadlock here: if the only fixes that would turn the
gate green are ones this instruction forbids, the feature can never reach a PASS. Reaching that point
**is** the answer. Record the feature as not done, name every fix you rejected and which criterion each
violated, and let the rule below end the run.

If the same feature comes out of verification without a PASS twice, stop the whole run and report it.
Two verification runs, not two rewrites: you are never required to ship a change you have already
shown to be wrong merely to spend a cycle. Do not try a third time and do not move on to the next
feature — a feature that cannot pass is the one thing this loop cannot settle by itself, and
continuing past it builds on top of it. **This stop outranks the finishing condition below.** That
one asks for a PASS on every feature and can therefore never be reached when a feature has none;
stopping here, and saying which feature and why, is the correct end of the run.

**A phase with nothing to do is done, not skipped.** If the implementation already satisfies every
check, build is complete: say so and move to verification. Do not manufacture a change to have
something to show — an edit made for that reason is indistinguishable, in a diff, from one made to
bend a result.

**When a feature ends without a PASS, none of its checks is complete either.** Leave the completion
marks in its `checks.md` unset, whatever each proof says on its own. Marks under a failed feature are
read by the next reviewer as progress that did not happen.

**Do not commit the failure.** That skill makes its own coherent commits, each checked by its own
script — that is its contract and this instruction does not override it. What must not happen is a
**feature** landing in history as done while its suite is red: no commit closing it, no branch merged,
no tag. Leave that state in the working tree, where a person sees it before it becomes part of the
record.

**Reconcile every claim an artifact makes about itself, not only the ones named here.** `open
questions — none` beside an unanswered question is the example; a check's expected value, a comment
asserting a project fact the data beside it contradicts, a status line describing work that did not
happen are the same defect. Where the artifact and the evidence disagree, the evidence wins: fix the
artifact and record that you did — except a check, which the bullet above governs.

Record the run's outcome before you stop, with
`python3 <ROADMAP-SKILL-DIR>/scripts/status-block.py <STATUS-PATH> --last-run "DATE - FEATURE - STATE REACHED - WHY IT STOPPED" --note ACCOUNT-FILE`,
filling the capitalised words yourself (ACCOUNT-FILE is a file holding your full account):
the one line lands in <STATUS-PATH> `## Status`, the account in `docs/roadmap-history.md`. If it cannot
run, replace the single `**Last run**:` line of that block yourself and append the account to
`docs/roadmap-history.md`. Never write paragraphs or headings into `## Status` — every later agent
pointed at it pays for them. A run that halts and leaves no trace looks, to the next reader, exactly
like one that never started.
**Features are built one at a time and that is not negotiable.** Never start the next one before this
one has a verified PASS, whatever capacity is idle. Every dependency in this roadmap points backwards
to a feature in the same file, so building ahead means building on work nothing has verified.

Backlog position is at that same block. Stop when every name in <BUILD-ORDER-TXT> from
`<target>` onward has a verified PASS or is on the discharged list above; report and stop there
rather than continuing into another roadmap.
```

**What is deliberately *not* in that template, so it is not "restored" by someone comparing the two.**
No Discuss disposition, because that skill has none. No `tasks.md` and no phase-batch offer, because
it has neither. No verdict-relabelling workaround: that exists for `validate_state.py`, which joins
every line it recognises into one string, and `validate_verification.py` reads the `**Verdict**:` line
and the rows directly. And no *"write your own verdict so that test cannot be got wrong"* — the
Verifier writes it. Where the two templates *do* share a clause it is word for word, on purpose: the
failing-test clause and the implementation-side forgery clause are the two that must never drift
apart, and `scripts/check-consistency.py` compares them.
