# The `/loop` template — `tlc-spec-driven`

Read this file **only** when Step 8's answer was option B and the downstream profile Phase 0 confirmed
(or the seed detected) is `tlc-spec-driven`; the other profile's template is in its own file, and a run never
needs both. `<SUBAGENT-DISPOSITION>` is resolved right below. Everything else that governs *how* to
emit it — the placeholder table, the scope rule, `<DISCHARGED-LIST>`, and why each clause is
load-bearing — stays in
[handover-prompt.md](handover-prompt.md) Step 10, which sent you here. Emit the block below verbatim,
placeholders resolved as that table says.

**Resolve `<SUBAGENT-DISPOSITION>` to exactly one of these two paragraphs**, by Step 8's answer to
*can the session you will run this in spawn sub-agents?* Never emit the placeholder, never both.

- the session **can** spawn sub-agents →

```text
**This session coordinates the features; it does not build them.** Everything a feature's work puts
into this conversation is re-read on every later turn, for every later feature — on a real multi-agent
build, re-reading context was three quarters of the cost. For each `<current-feature>`:

1. Dispatch a fresh sub-agent as its BUILDER — the `roadmap-builder-a` agent type when the brief's risk
   tier is A, `roadmap-builder` otherwise, whenever `.claude/agents/` defines them; if the harness
   does not know the type, dispatch a general sub-agent and put that file's body first in its
   instructions. Hand it the start command above with `<current-feature>` filled in, everything in
   this prompt from "No user is available" up to (not including) "Record the run's outcome" — the
   paragraphs from there on govern the loop, not a feature — and its role: it runs the skill's cycle through the feature's last commit, does not validate its own work, never records the run's outcome, and replies with ONE line — the feature, its last
   commit, and anything it refused to do.
2. Dispatch a second fresh sub-agent as its VERIFIER — the `roadmap-verifier` agent type, or a
   general one with that file's body first, as above — never a child of the builder. Hand it the same part of this prompt and its role: it
   runs that skill's validate phase over every acceptance criterion and writes `validation.md`
   (replacing an earlier one), changes no code, never records the run's outcome, and replies with ONE line.
3. Judge the verdict yourself with the fewest commands the done rule below allows — the gate
   script's exit code, read from the script itself and never through a pipe (a pipe reports the last
   command's), and a grep for the one verdict line — never by opening the report here.
4. Dispatch a second builder, told the report's path, only when the report names a fix this prompt
   allows. When every fix it names is one this prompt forbids, the feature is not done: say so and
   stop as the paragraphs below say.

Never hand on the leading `/loop`. Never read a builder's or a verifier's work into this conversation
beyond its one line — the files on disk are the record. Only this session records the run's outcome.
```

- it **cannot** →

```text
**You cannot spawn sub-agents, so every feature is built and validated in this one conversation, and
each one makes every later turn more expensive.** Keep what enters it small: read files with an offset
and a limit, filter a command's output to the lines that matter, never paste a whole log or diff, never
re-read a finished feature's files, and keep one verdict line per feature. Do not attempt to spawn
anything.
```

```
/loop Implement the roadmap at <ROADMAP-PATH>, one feature at a time, in the exact order of
<BUILD-ORDER-TXT>, using the `<downstream-skill>` skill for every feature — run its full cycle
(specify → design → tasks → execute → verify). This run covers <ROADMAP-PATH> and nothing else: no
other `docs/ROADMAP*.md` file is in scope, whatever <STATUS-PATH> lists.

`<current-feature>` below is this run's own variable, not a name to resolve once. At the start of
every iteration, re-read <BUILD-ORDER-TXT> and set it to the first name at or after `<target>` that
is not on the discharged list below and has no verified PASS in
`.specs/features/<current-feature>/validation.md` — verified as defined further down (one consolidated
verdict line reading PASS, with a `file:line` citation), never the word PASS found anywhere in it. Start that feature with:
`specify feature <current-feature> — create it at `.specs/features/<current-feature>/` using that
exact directory name, spec source: the <ROADMAP-PATH> entry <current-feature>`. If that directory
already exists, the feature is partly built: read its artifacts and its report first, fix what the
report refuses, and do not start the spec over. Do not skip a feature, do not reorder them, and
do not start the next one until the current one has that verified PASS. Exception — these features
are already discharged and must be skipped, never built: <DISCHARGED-LIST>.

Before each feature's gray-area discussion, run
`python3 <ROADMAP-SKILL-DIR>/scripts/feature-brief.py <current-feature>` and work from its output: the
feature's entry, its risk tier and what that tier sets for this skill (follow it), the questions naming it, the contracts it consumes, and `## Cross-Cutting Decisions`,
which are settled — do not re-decide them, and keep every feature consistent with them. Never open
a `docs/ROADMAP*.md` file whole: each is shared by the whole backlog and you would carry all of it on
every later turn. If the script cannot run, read only the `### <current-feature>` entry and the
lines that name it.

<SUBAGENT-DISPOSITION>

No user is available for this run. Dispose of every stop as follows and never wait for an answer,
but never leave one silently unrecorded either:

- A gray area not settled in `## Cross-Cutting Decisions` — treat it as declined: choose the
  default and record it with its rationale in that feature's spec under Assumptions & Open Questions.
- A request to approve this run's own spec, context, design or task list — approve and continue,
  then note in that same section which artifacts were self-approved. Nobody reviewed them, and that
  line is what lets somebody review them later.
- **The offer of phase-batch sub-agents**, which the downstream skill makes above its own task
  threshold and then waits on — decline it and execute inline: whoever builds is already a fresh
  context for this one feature, or, without sub-agents, the paragraph above governs. Say so in that
  feature's spec.
- Any other choice about how to execute — ordering inside a feature, how much to do before checking —
  pick one, say which, continue.
- A project-level fact the run cannot invent, such as which test framework to use — take it from
  `## Cross-Cutting Decisions`; if it is not there, record it as an open question and choose the most
  conservative option that exists in the repository already. Never invent a credential and never
  reach a network service to resolve one.
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
- **Where a feature's own artifacts demand what this instruction forbids, this instruction wins.** A
  `tasks.md` whose done-when is *"test X passes"*, a roadmap entry claiming `open questions — none`
  while an unanswered one blocks the work — rewrite the artifact to match the acceptance criterion,
  and record that you rewrote it and why. Left unstated, this is the pressure point that manufactures
  a bent test: a task list ordering the very thing the rule refuses.

**A feature counts as done only when its `validation.md` carries a consolidated verdict line reading
PASS, with at least one `file:line` citation.** A report whose acceptance-criteria rows contain the
word `PASS` while its verdict says otherwise is **not** a pass — never decide this by searching the
file for `PASS`, which is exactly how a failed feature gets skipped. Write your own verdict so that
test cannot be got wrong: one consolidated line, and nothing above it that reads like one.

**Nobody is reviewing this run, so every verification is self-verification.** Say so in the report:
name the artifacts you approved yourself and the verdict you reached on your own work. A PASS this
run records is evidence the suite was green, not evidence anyone independent agreed — and the
difference matters to whoever reads it next.

**When the downstream skill's own loop cannot terminate, this instruction ends it.** That skill
treats a red gate as *stop, fix, re-run* — correct in general, and a deadlock here: if the only fixes
that would turn the gate green are ones this instruction forbids, its loop can never exit and the
feature can never reach verification. Reaching that point **is** the answer. Record the feature as
not done, name every fix you rejected and which criterion each violated, and end the run
there: the two-verification rule below is for fixes that were tried and failed, not for fixes that
were refused — verifying an unchanged tree again cannot say anything new.

If the same feature comes out of verification without a PASS twice, stop the whole run and report it.
Two verification runs, not two rewrites: you are never required to ship a change you have already
shown to be wrong merely to spend a cycle. Do not try a third time and do not move on to the next
feature — a feature that cannot pass is the one thing this loop cannot settle by itself, and
continuing past it builds on top of it. **This stop outranks the finishing condition below.** That
one asks for a PASS on every feature and can therefore never be reached when a feature has none;
stopping here, and saying which feature and why, is the correct end of the run.

**Write a FAIL the downstream gate can actually read.** Its own script decides by looking at
headings matching `## Validation…` and at any line containing `Result:` — a verdict written anywhere
else is invisible to it. A run that wrote `## VERDICT: FAIL` was told by that gate that the report
*"has no PASS/FAIL verdict"*, which is the worst possible outcome: a feature that failed, recorded in
a way the thing checking for failure cannot see. **Read the downstream skill's own template from disk
and match it** — never invent a heading of your own, however clear it reads.

**Those two demands collide if you follow the template literally, so reconcile them this way.** That
gate joins *every* line it recognises into one string before deciding, and the template emits three
such lines — the sensor's `**Result**:`, Gate Check's `- **Result**:` and the chat block's
`## Validation: FEATURE - [PASS | FAIL]`. Together they put both words in the haystack, and the gate
then reports *"still the template placeholder"* instead of your verdict. Keep every section heading
verbatim, **relabel only the inline result fields** so they stop matching that pattern —
`**Sensor verdict** —`, `**Gate outcome** —` — and let one `## Validation: FEATURE — VERDICT`
line be the only thing the gate sees. Verified against the real script: it then reads `FAIL` as
`FAIL`.

Per-criterion rows say `MET` / `NOT MET`, never `PASS`. **When a criterion is met by the code and denied by the test guarding it**, say exactly that
rather than collapsing it either way: `MET, contradicted by TEST-NAME`. Calling it `MET` hides a red
suite and calling it `NOT MET` blames code that is correct, and the consolidated verdict is a FAIL in
both readings anyway — what a later reader needs is which of the two is broken.

**A phase with nothing to do is done, not skipped.** If the implementation already satisfies every
acceptance criterion, execute is complete: say so and move to verification. Do not manufacture a
change to have something to show — an edit made for that reason is indistinguishable, in a diff, from
one made to bend a result. A FAIL that a later iteration mistakes for a pass is how the loop skips past unfinished work,
which is the one outcome every rule here is aimed at.

**When a feature ends without a PASS, no task inside it is complete either.** Leave its checkboxes
unticked, whatever their individual done-whens say. A `tasks.md` full of ticks under a failed feature
is read by the next reviewer as progress that did not happen.

**Do not commit the failure.** The downstream skill may make its own atomic commit after each task
whose gate passed — that is its contract and this instruction does not override it. What must not
happen is a **feature** landing in history as done while its suite is red: no commit closing it, no
branch merged, no tag. Leave that state in the working tree, where a person sees it before it becomes
part of the record.

**Reconcile every claim an artifact makes about itself, not only the ones named here.** `open
questions — none` beside an unanswered question is the example; a task's done-when, a comment
asserting a project fact the data beside it contradicts, a status line describing work that did not
happen are the same defect. Where the artifact and the evidence disagree, the evidence wins: fix the
artifact and record that you did.

Record the run's outcome before you stop, with
`python3 <ROADMAP-SKILL-DIR>/scripts/status-block.py <STATUS-PATH> --last-run "DATE - FEATURE - STATE REACHED - WHY IT STOPPED" --note ACCOUNT-FILE`,
filling the capitalised words yourself (ACCOUNT-FILE is any temporary file holding your full
account; delete it afterwards):
the one line lands in <STATUS-PATH> `## Status`, the account in `docs/roadmap-history.md`. If it cannot
run, replace the single `**Last run**:` line of that block yourself and append the account to
`docs/roadmap-history.md`. Never write paragraphs or headings into `## Status` — every later agent
pointed at it pays for them. A run that halts and leaves no trace looks, to the next reader, exactly
like one that never started.
**Features are built one at a time and that is not negotiable.** Never start the next one before this
one has a verified PASS, whatever capacity is idle. Every dependency in this roadmap points backwards
to a feature in the same file, so building ahead means building on work nothing has verified. Batching
happens *inside* a feature; the sequence *between* features is the guarantee.

Backlog position is at that same block. Stop when every name in <BUILD-ORDER-TXT> from
`<target>` onward has a verified PASS or is on the discharged list above; report and stop there
rather than continuing into another roadmap.
```
