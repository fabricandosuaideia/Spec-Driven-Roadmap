export const meta = {
  name: 'roadmap-pipeline',
  description: 'Build pending roadmap features: implement, prove on a fresh context, verify (and review for tier A), merge only on pass',
  whenToUse: 'Run with the args printed by spec-driven-roadmap scripts/plan-pipeline.py, only when the user asked to run the pipeline',
  phases: [
    { title: 'Build', detail: 'a builder implements on feat/<name>; a fresh prover rebases, runs the full gate once and writes the receipt (after the verifier, with gateOrder verify-first)' },
    { title: 'Verify', detail: 'the downstream skill verifier (and, for tier A, an independent reviewer) — never the builder' },
    { title: 'Merge', detail: 'the authoritative gate on the exact tree (or the prover\'s receipt, with mergeGate receipt), then a fast-forward into the main branch' },
    { title: 'Barrier', detail: 'only when barrierGate is set: the whole suite on the merged main branch; red stops further merges' },
    { title: 'Record', detail: 'one Last run line in ## Status, the account in docs/roadmap-history.md' },
  ],
}

// Shipped by spec-driven-roadmap. Generic form of a pipeline measured on a 162-feature build
// (WordPress AI Agent Manager, v3.3): re-reading context was ~75% of its cost, builders 52%, the
// orchestrator 10%, retries ~28%. Every choice below answers one of those numbers:
// a fresh PROVER so the builder's conversation ends early; the verifier reuses the prover's gate
// receipt instead of re-running the suite; the invariant is written at attempt 3; efforts are set
// per role and tier; this script returns one line per feature and nothing else.
//
//
// Two defects from the first real run (Sales-ai, 2026-09-29), both fixed here. The Workflow harness
// relays the request that launched the run to EVERY agent as "the only user voice", winning over the
// computed task; the launch prompt says "run plan-pipeline, launch the Workflow tool", so provers
// did that instead of proving. LAUNCHED now tells each role that request is not its task. And a
// command is cut off at 10 minutes while a project's gate took longer: provers started it in the
// background and replied "not ready" to have something to return, which ends a workflow agent, so
// no gate ever finished. RUN_GATE runs it detached and waits for its exit file before any reply.
//
// args (from plan-pipeline.py): { project, skillDir, downstream, downstreamDir, statusPath, mainBranch,
//   gate, barrierGate?, barrierEvery?, model?, waitChunk?, testHint, setup, push, lanes, worktreeRoot,
//   checklist, effort, maxAttempts, models?: { <role>: model }, gateOrder?, mergeGate?, postMerge?, verifier?: { sensor?: { A, B, C }, survivor?, rounds? }, barrierPending?: { base, head },
//   features: [{ name, roadmap, tier, dependsOn[], lane, worktree?, startAttempt?, feedback? }] }
// `gateOrder` is 'gate-first' (the default: build, prove, verify) or 'verify-first' (build, verify, and the
// full gate only for a feature the verifier passed): see VERIFY_FIRST below.
// `gate` is what every feature must pass before it merges; `barrierGate`, when a project keeps its
// whole suite for a batch barrier, runs on the merged main branch every `barrierEvery` merges (0 =
// once, at the end). `barrierPending` is set when code reached the main branch after the last green
// barrier (a run paused inside its barrier): that barrier runs first, before anything is built.

const A = args || {}
const P = A.project
const SKILL = A.skillDir
const DS = A.downstream
const DSDIR = A.downstreamDir
const LEAN = DS === 'tlc-spec-lean'
const MAIN = A.mainBranch || 'main'
const LANES = Math.max(1, A.lanes || 1)
const FEATURES = A.features || []
const MAX = A.maxAttempts || { A: 5, B: 4, C: 3 }
const EFFORT = A.effort || {}
const REPORT = LEAN ? 'verification.md' : 'validation.md'
const GATE_SCRIPT = LEAN ? 'validate_verification.py' : 'validate_state.py'
const BARRIER_EVERY = Math.max(0, A.barrierEvery || 0)
const CHUNK = Math.max(30, Math.min(540, A.waitChunk || 540))
if (!P || !SKILL || !DS || !DSDIR || !A.gate) throw new Error('args incomplete: run plan-pipeline.py and pass its output as args')
const MODEL = A.model ? { model: A.model } : {}
// 3.41.0: one model for every agent made a cheap model do the work that needs a careful one, and the other
// way round. `models` (pipeline.json) names a model for a role; a role it does not name uses `model`, and
// that one, when unset, the session's. Roles: build, prove, verify, review, merge, record, triage, barrier.
// The repairer is a builder, the triage checker a verifier, the triage merger a merger.
const modelFor = role => (A.models && A.models[role]) ? { model: A.models[role] } : MODEL
// 3.38.0, from a project whose gate took 24 minutes (Infinity-Agent-Creator): the full gate ran before the
// verifier on every attempt, and 28 of the 37 attempts that reached the verifier were refused, so 28 gates
// bought a refusal that did not need them. 11 of 48 provers did catch a real failure first (lint, a stale
// test, a regression elsewhere), so the order is a trade and the user's: verify-first spends a verifier
// run on those 11 and saves a gate on every attempt the verifier refuses. It pays when the gate is long
// beside a verification (bench-gate.py times it); a short gate loses by it.
const VERIFY_FIRST = A.gateOrder === 'verify-first'
// 3.43.0: the merge ran the whole gate again on a tree the prover had just proved, 9 times in 24 minutes on the
// project that measured it (10% of its time). `mergeGate: 'receipt'` lets the receipt stand in when it proves
// the exact tree: same code hash, and the main branch where the prover rebased onto it. A receipt is written by
// an agent, so plan-pipeline.py refuses this without a barrierGate, the one gate nobody's word stands in for.
const BY_RECEIPT = A.mergeGate === 'receipt' && !!A.barrierGate
// Set by manager-pipeline.js only. In manager mode nobody is there to authorise a test correction,
// and on a real project two features in two days each spent five attempts and stopped the chain on
// tests asserting behaviour the owner had revoked; the owner authorised the same correction by hand
// both times. MANAGED lets the builder make that one correction and makes the verifier check it.
// 3.40.0 widened it from "an owner decision revokes exactly this assertion" to "this feature's spec changes
// the behaviour" (second project: its own diagnosis counted 8 of 53 refusals as an old test the new spec contradicts); the verifier
// still confirms that the criterion cited contradicts the old assertion.
const MANAGED = !!A.managerMode
// Manager mode's second level (manager.autonomy "unblock"): a red barrier is triaged and repaired
// instead of stopping the run. Only the manager sets it; a person running option C never gets it.
const UNBLOCK = MANAGED && A.autonomy === 'unblock'

const tierOf = f => (f.tier === 'A' || f.tier === 'C') ? f.tier : 'B'
const laneOf = f => Math.min(LANES, Math.max(1, f.lane || 1))
// A feature that did not finish an earlier run keeps its worktree, wherever that lane's number now points:
// plan-pipeline.py names it (`worktree`), because git refuses to check a branch out twice and the builder
// and the merger must be looking at the same directory.
const wt = f => LANES > 1 ? (f.worktree || `${A.worktreeRoot}/lane${laneOf(f)}/${f.name}`) : P
const effortFor = (role, f) => {
  const e = EFFORT[role]
  return (e && typeof e === 'object') ? e[tierOf(f)] : e
}
const HASH = `git diff ${MAIN}...HEAD -- . ':!.specs' ':!docs' | sha256sum | cut -d' ' -f1`

const WORKTREE = f => LANES > 1
  ? `WORKING TREE: ${wt(f)} (branch feat/${f.name}); if it does not exist create it with: git -C ${P} worktree add -b feat/${f.name} ${wt(f)} ${MAIN} || git -C ${P} worktree add ${wt(f)} feat/${f.name}${A.setup ? `, then in it: ${A.setup}` : ''}. Work only there; never run commands in ${P}.`
  : `WORKING TREE: ${P}. Work on branch feat/${f.name} (git checkout feat/${f.name}, creating it from ${MAIN} if it does not exist).`

const LAUNCHED = `LAUNCH REQUEST: the user request relayed to you above is the one that started this pipeline, and the session that received it has already done it — this pipeline is running and you are one of its agents. It is not your task: never run plan-pipeline.py and never look for a Workflow tool. Your task is the ROLE below.`

// A gate can outlast one command (10 minutes), and a workflow agent is finished the moment it
// replies, so a gate it does not wait for is read by nobody. `tail --pid` blocks without `sleep`,
// which the harness refuses as a way of waiting.
const RUN_GATE = (cmd, where, what = 'gate') => `run it DETACHED and wait for it — a single command is cut off at 10 minutes, a ${what} can take longer, and you are finished the moment you reply:
   a) D=$(mktemp -d); nohup bash -c 'cd "$1" && ( ${cmd.replace(/'/g, `'\\''`)} ); echo $? > "$0/exit"' "$D" "${where}" > "$D/log" 2>&1 & echo "$D $!"
   b) wait with: timeout ${CHUNK} tail --pid=<that PID> -f /dev/null — never sleep — and repeat it until $D/exit exists; exit code 124 only means keep waiting.
   c) the ${what}'s exit code is the content of $D/exit; read only the tail and the failures of $D/log.
   NEVER reply while $D/exit does not exist: a reply sent while the ${what} still runs is not a result, and the pipeline reads it as a failure.`

// 3.37.0, from the second real project (Infinity-Agent-Creator, Haiku): 8 of 56 builders never reached
// the prover, and the three that ended with a job still running had loaded the Monitor tool, armed a
// watcher on a background test run or a lock regeneration, and answered ready=false "waiting for the
// monitor". A workflow agent is finished the moment it replies, so the job's result was read by nobody
// and the attempt was spent. The prover has had RUN_GATE since 3.31.0; the builder had nothing.
const LONG_COMMANDS = `LONG COMMANDS: you are finished the moment you reply or call StructuredOutput, and nothing wakes you later — a background job, a Monitor or a watcher is read by nobody. Never run_in_background, never load or arm Monitor, never reply ready=false because something is still running. Wait for it in this same turn: a command you are sure ends within 2 minutes (the Bash tool's default timeout) runs in the foreground; anything that may take longer, or whose length you cannot tell (a test batch, a lock regeneration, a build), runs detached and is waited for:
   a) D=$(mktemp -d); nohup bash -c 'cd "$1" && ( <the command> ); echo $? > "$0/exit"' "$D" "<your working tree>" > "$D/log" 2>&1 & echo "$D $!"
   b) timeout ${CHUNK} tail --pid=<that PID> -f /dev/null — never sleep — repeated until $D/exit exists (exit code 124 only means keep waiting). Give that Bash call a timeout parameter of ${(CHUNK + 20) * 1000} milliseconds: the tool's default is 120 seconds, and a wait that outlasts it is moved to the background, which is the thing to avoid.
   c) the exit code is the content of $D/exit; read only the tail and the failures of $D/log.`

const COMMON = f => `You are one agent of a build pipeline for the project at ${P}. Nobody is available to answer: decide, record the decision where ${DS} keeps assumptions, never ask.
${LAUNCHED}
FEATURE: ${f.name}, risk tier ${tierOf(f)}. Its spec source is the output of: python3 ${SKILL}/scripts/feature-brief.py ${f.name} --root ${P} — the entry, the questions naming it, the contracts it consumes, the settled Cross-Cutting Decisions, and what tier ${tierOf(f)} sets for ${DS}. Never open a docs/ROADMAP*.md file whole.
DOWNSTREAM SKILL: ${DS}, at ${DSDIR}. Read its SKILL.md and only the references your role needs.
${WORKTREE(f)}
CONTEXT BUDGET: every turn re-reads your whole conversation. Read files with offset/limit, grep for a symbol instead of reading a directory, send long command output to a file and read back only the lines that matter, never paste a whole log or diff, never re-read a file that did not change.
${MANAGED ? REVOKED_RULE : 'TESTS: never edit, weaken, skip, delete or add a test to reach a pass, and never change behaviour against an acceptance criterion or a settled Cross-Cutting Decision to turn a test green. A test that is genuinely wrong stays red, with the reason written down.'}`

const REVOKED_RULE = `TESTS: never weaken, skip, delete or add a test to reach a pass, and never change behaviour against an acceptance criterion or a settled Cross-Cutting Decision to turn a test green.
MANAGER MODE — one exception, because nobody is there to authorise it: an existing test is updated, not obeyed, when its assertion states a behaviour that this feature's spec changes — an acceptance criterion, an answered open question or a settled Cross-Cutting Decision states the new behaviour, and the old assertion contradicts it. The criterion or decision must come from the roadmap behind this feature (the entry, the answered questions and the Cross-Cutting Decisions that feature-brief.py prints), decided before you started — never from a spec, plan or check that you wrote on this branch. Update THAT assertion, and only it, to the behaviour the spec now states, at the same strength — as specific, no looser matcher, no removed check, no skip — in a commit of its own whose FIRST LINE is REVOKED-TEST <file>:<test name> (so that git log --grep=REVOKED-TEST finds it) and whose body quotes the criterion or decision and names where it is recorded. List each in your notes as well. A test red for any other reason is a defect in your change: fix the code, not the test, and if it truly cannot be fixed inside this feature's scope say exactly why in your notes. The independent verifier refuses every test change that is not such a correction.`

// The triage repairer keeps the narrow exception (an owner decision revokes exactly the assertion) and may fix a
// test that is wrong about timing, ordering or shared state at that cause: a regression belongs to a feature whose
// own spec did not change, so "this feature's spec" gives it nothing to stand on.
const REPAIR_TESTS = `TESTS: never weaken, skip, delete or add a test to reach a pass, never raise a timeout, never add a retry. A test that is wrong about timing, ordering or shared state is fixed at that cause (the PREEXISTING item above), keeping its name and its strength. The one other exception: an owner decision recorded in the roadmap that revokes exactly an assertion lets that assertion be corrected, in a commit of its own whose first line is REVOKED-TEST <file>:<test name> and whose body quotes the decision and where it is recorded, as strong as before.`

const ANGLES = [
  'Build the feature exactly as its spec source states.',
  'The previous attempt was refused. Resolve every listed issue precisely; do not widen scope and do not undo what already passes.',
  'Two attempts have been refused. BEFORE writing code, write in one sentence the invariant the refusals share (the single rule that, enforced in one place, prevents all of them), record it with your notes, then satisfy it with the smallest change — a different place or shape if needed, reusing what already works.',
  'Three attempts have been refused. Restate the invariant if the last one was wrong or incomplete, then make the smallest change that enforces it and meets every criterion. If one criterion is truly impossible as written, say exactly why and meet all the others.',
  'Several attempts have been refused, each time on a narrower variant of the same cause. Fix ONLY the blocker and major issues below, at the root (state the invariant, enforce it in one place), leave minor ones alone, do not refactor.',
]

const IMPLEMENT = (f, attempt, feedback) => `${COMMON(f)}

ROLE: BUILDER, attempt ${attempt} of ${MAX[tierOf(f)]}. ${ANGLES[Math.min(attempt, ANGLES.length) - 1]}
${attempt > 1 ? `First rebase feat/${f.name} onto ${MAIN}. Issues to resolve (check each against the code first; if one is wrong, say why in your notes):\n${JSON.stringify(feedback || [], null, 1)}\n` : ''}${attempt === 1 ? `If feat/${f.name} already exists, an earlier run built on it: first rebase it onto ${MAIN} and resolve any conflict yourself, keeping what both sides intended — the prover rebases it again and fixes nothing, so a conflict left for it costs a whole attempt.\nIf feat/${f.name} already exists and a refused ${REPORT} (or a gate-failure.md note) is committed in .specs/features/${f.name}/, an earlier run refused this feature: read that report or note first and resolve every gap it lists before anything else, as an attempt after a refusal does.\n` : ''}Run ${DS}'s cycle for this feature through its last commit: ${LEAN ? 'plan and checks (approve them yourself and write that you did in plan.md under ## Assumptions), then build' : 'spec, design and tasks at the depth the tier sets (approve them yourself and write that you did in the spec under Assumptions & Open Questions), then execute'}. Commit atomically.
While you work, run only the tests related to what you touched${A.testHint ? ` (${A.testHint})` : ''}. Do NOT run the full gate and do NOT write ${REPORT}: a fresh prover and an independent verifier come after you.
${LONG_COMMANDS}
${A.checklist ? `Before you finish, check your diff against every item of ${A.checklist} (the problems reviewers kept finding in this project) and fix what fails.\n` : ''}DEFERRED SCOPE: an issue that is the declared scope of a LATER feature in the build order is not yours: name that feature in your notes and move on.
Reply ready=true once every change is committed, even though the full gate has not run; otherwise ready=false with blockers.`

const PROVE = f => `${COMMON(f)}

ROLE: PROVER, on a fresh context. A builder already committed this feature on feat/${f.name}${VERIFY_FIRST ? ' and an independent verifier has passed it' : ''}; you did not write it. Do not re-implement and do not widen scope${VERIFY_FIRST ? ', and do not verify again: you are the last step before the merge' : ''}.
1. Rebase feat/${f.name} onto ${MAIN}${A.setup ? ` (if dependency manifests changed, run: ${A.setup})` : ''}.
2. Run the GATE once on this exact tree — ${A.gate} — and ${RUN_GATE(A.gate, wt(f))}
   A failure is a defect, never "environmental": reply ready=false naming the failing test or file, and fix nothing.${VERIFY_FIRST ? ` Because a verifier already passed this feature, first leave a note for the next builder: write .specs/features/${f.name}/gate-failure.md (the failing tests and the command, at most 10 lines) and commit only that file.` : ''}
3. Write .specs/features/${f.name}/gate-receipt.json as {"codeHash":"<output of: ${HASH}>","base":"<output of: git merge-base ${MAIN} HEAD>","gate":"pass","command":<the gate command>} and commit it. (The base is the commit of ${MAIN} your tree is built on: if ${MAIN} moved while the gate ran, it is the older one, which is what makes the receipt honest.)
Reply ready=true only when the rebase is clean, the gate finished and passed, and the receipt is committed.`

const VERIFY_RECEIPT = f => `GATES BY RECEIPT: recompute the code hash (${HASH}); if it equals .specs/features/${f.name}/gate-receipt.json's codeHash and the receipt says pass, do NOT re-run the full gate — run only this feature's tests and ${DS}'s own fault injection or discrimination sensor. If it differs or is missing, report that as a minor issue and run the gate yourself (${A.gate}) — ${RUN_GATE(A.gate, wt(f))}`
// verify-first: no receipt exists yet, and the full gate belongs to the prover who follows a PASS.
const VERIFY_GATE = f => `THE FULL GATE (${A.gate}) RUNS AFTER YOU, by a prover, and only for a feature you pass: do not run it and do not look for a receipt. Run only this feature's tests${A.testHint ? ` (${A.testHint})` : ''} and ${DS}'s own fault injection or discrimination sensor, and in the report's gate section write the command you ran and that the full gate follows.`

// 3.39.0, from the same project: a surviving mutant was named in 12 of 26 readable refusals, and the
// project's own rules record "an unbounded sensor and a new gap each round" as what spent seven attempts
// on one feature. Two controls: the cap and the survivor severity are off unless the project sets them; the scoped rounds are ON
// unless `rounds` is 'full':
// `verifier` in pipeline.json (a cap on mutants per tier, and the severity of a survivor), and rounds
// after the first scoped to what was refused and what changed, as tlc-spec-lean's verify.md already
// prescribes ("Re-verifying after a fix") and tlc-spec-driven's validate.md does not.
const VP = A.verifier || {}
const SENSOR_POLICY = f => {
  const cap = VP.sensor && VP.sensor[tierOf(f)]
  const parts = []
  if (cap) parts.push(`at most ${cap} mutant${cap === 1 ? '' : 's'} for this feature, each chosen so that a DIFFERENT proof has to fail (one per distinct assertion surface); stop once every proof carrying a criterion has been made to fail once`)
  if (VP.survivor) parts.push(`a surviving mutant is a ${VP.survivor} issue${VP.survivor === 'minor' ? ': list it in the report, it does not refuse the feature' : ''}`)
  return parts.length ? `SENSOR POLICY (this project's, over ${DS}'s own default): ${parts.join('; ')}.\n` : ''
}
const SCOPE = f => `its report is the committed ${REPORT} in .specs/features/${f.name}/ (its commit: the sha above); read it first. The round is SCOPED to (1) every row of that report whose result is not PASS or MET and (2) what changed since that commit (git diff <that sha>..HEAD over the files outside .specs and docs — scope by the diff, not by the fix's intent: a fix to a shared helper, fixture or config reaches further than its description). If the branch was rebased since (the base the report's Diff range names is no longer git merge-base ${MAIN} HEAD), what main gained in that rebase is new code too: add git diff <that base>..$(git merge-base ${MAIN} HEAD) over the files this feature touches. Every other row carries forward and says so ("carried from <that sha>"). The proofs re-run in full at HEAD. Fault injection is scoped the same way: a previous mutant that was killed, on code and proofs this diff did not touch, carries forward; re-inject the ones that survived and every one on a surface the diff touched or created, and add new mutants only on such a surface — the code it changed, and the code that a test or assertion it added or changed exercises (a new assertion has never been made to fail once, and a fix that only adds a test changes no code). Never new mutants on code and tests that did not change. Scope limits what you re-run, never what you may refuse: a defect you notice outside it — a criterion not met, a security or correctness flaw — keeps its true severity; only a weakness that lies OUTSIDE the scope and is not a defect (a test that could assert more, a mutant that survives there) is a minor issue: list it, it does not refuse the feature. Inside the scope, and in a first verification, nothing is demoted.${LEAN ? ' Write the Round line as verify.md prescribes (Round: N - scoped).' : ''}`
// `rounds: 'full'` turns the scoping off: a scoped round trusts the earlier round's verdict on the rows it carries
// forward, so a first round that was loose leaves its loose PASS rows standing. That is the price, and the user's.
// Whether a round is a later one depends on a report existing, never on the attempt counter: attempt 2 after a builder
// that did not finish, or after a prover that failed first, is the first time a verifier sees the feature.
const ROUND = (f, attempt) => VP.rounds === 'full' ? '' : `ROUND ${attempt}. Step 1: run git log -1 --format=%H -- .specs/features/${f.name}/${REPORT} . If it prints NOTHING, this is a FIRST verification: ignore the rest of this paragraph and verify everything by ${DS}'s own rules — a clause of a criterion that no test exercises is not proven, and a surviving mutant is a finding, exactly as those rules say. If it prints a sha, this is a LATER ROUND, that sha is the report's commit, and the rest of this paragraph applies — ${SCOPE(f)}\n`

const VERIFY = (f, attempt) => `${COMMON(f)}

ROLE: VERIFIER. You did not build this; try to show it is NOT done. Follow ${DS}'s ${LEAN ? 'references/verify.md' : 'references/validate.md'} over every ${LEAN ? 'check' : 'acceptance criterion'}. You change no code.
${VERIFY_FIRST ? VERIFY_GATE(f) : VERIFY_RECEIPT(f)}
${ROUND(f, attempt)}${SENSOR_POLICY(f)}${MANAGED ? REVOKED_CHECK(f) + '\n' : ''}${LEAN ? 'Write verification.md exactly as verify.md prescribes, with **Verdict**: PASS or FAIL at the top.' : 'Write validation.md from validate.md\'s template with ONE line reading "## Validation: ' + f.name + ' — PASS" or "— FAIL" as the only verdict the gate can see: relabel the sensor and gate-check result fields (**Sensor verdict** —, **Gate outcome** —); per-criterion rows say MET or NOT MET, never PASS.'} Cite file:line evidence. Commit the report.
Then run the completion gate: python3 ${DSDIR}/scripts/${GATE_SCRIPT} ${f.name} --root ${wt(f)} — and report its exit code as the script returned it, never through a pipe.${tierOf(f) === 'C' ? '\nThis is a tier C feature and no reviewer follows you: review the diff for correctness, security and weak tests as well, and list those issues too.' : ''}
Reply with gateExit, pass (true only if gateExit is 0, every ${LEAN ? 'check' : 'criterion'} holds and you found no blocker or major issue), notMet and issues.`

const REVOKED_CHECK = f => `REVOKED TESTS (manager mode): list every change on this branch to a test that already existed on ${MAIN} (git diff ${MAIN}...feat/${f.name}, over the project's test files: test sources, fixtures, conftest, test configuration and the gate script). Each must be a REVOKED-TEST the builder declared, in a commit of its own whose first line is REVOKED-TEST <file>:<test name> (git log ${MAIN}..feat/${f.name} --grep=REVOKED-TEST finds them) and whose body quotes an acceptance criterion, an answered question or a settled Cross-Cutting Decision. Read it where the commit says it is, and confirm (1) that it states a behaviour the OLD assertion contradicts, (2) that the new assertion states that behaviour at the same strength, and (3) that it was decided BEFORE this branch: run git log ${MAIN}..feat/${f.name} -- <the file it is recorded in>, and if the branch itself added or edited that text, or it appears only in a spec, plan or check the builder wrote on this branch with nothing in the roadmap behind it (python3 ${SKILL}/scripts/feature-brief.py ${f.name} --root ${P}), it is not a decision. Every change that fails any of this — an undeclared edit, no such criterion or decision, one the old assertion does not contradict, one the branch wrote itself, a weaker assertion, a skip or an expected-failure mark, a deletion — is a blocker issue at that file:line. A criterion that was written only to explain the edit, and states nothing the product needed, is the same blocker.`

const REVIEW = f => `${COMMON(f)}

ROLE: CODE REVIEWER, independent of the builder and the verifier. Review git diff ${MAIN}...feat/${f.name}; read a changed file in full only where the diff is not enough. You edit and commit nothing, and you do not run the full suite.
Look for: correctness and unhandled edge cases; non-atomic read-then-write on shared state; state written before validation; security (injection, missing authorisation, secrets in logs or persisted text); swallowed errors; missing timeouts; unbounded queries or per-row query loops; a duplicate of a helper that already exists; weak or tautological tests; comments that claim more than the code does.${A.checklist ? ` Also every item of ${A.checklist}.` : ''}
The builder's and the prover's notes are claims: spot-check the few most likely to be wrong instead of re-deriving everything.
Report each issue with severity blocker | major | minor, where (file:line), problem and fix.`

const MERGE_RECEIPT = f => `The gate receipt may stand in for the gate below. Run these checks in ${wt(f)}. Read .specs/features/${f.name}/gate-receipt.json: it proves this exact tree only if ALL of these hold — its gate is "pass"; its command is the same command as the gate named in this step, not a lighter one; it has a base, and the base equals the output of git -C ${wt(f)} rev-parse ${MAIN} (the prover recorded the commit of ${MAIN} its tree was built on, so a match means ${MAIN} has not moved since); git -C ${wt(f)} status --porcelain prints nothing; and its codeHash equals the hash this command prints: git -C ${wt(f)} diff ${MAIN}...HEAD -- . ':!.specs' ':!docs' | sha256sum | cut -d' ' -f1 . If they all hold, do NOT run the gate: write "gate skipped: receipt" in notes. If any one of them fails, or the file is missing or has no base, the receipt proves nothing: `

// 3.44.0, from the WordPress AI Agent Manager, whose local copy of this script ran a database migration after each
// merge (`postMerge` in its pipeline.json) and would have lost it on a reinstall. The merge has happened by then:
// the main branch moved, so a failure does not undo it; it stops what follows and the account says so.
const POST_MERGE = A.postMerge ? `3b. Then, once, on ${MAIN} in ${P}, run the project's post-merge command: ${A.postMerge} (it applies what the merged code needs outside git, for example forward-only database migrations) — and ${RUN_GATE(A.postMerge, P, 'post-merge command')}
   If it fails, the merge STAYS: never undo the fast-forward; reply ok=true with postMerge=false and the tail of its output in notes.
` : ''

const MERGE = f => `You are the MERGER for feature ${f.name} in the project at ${P}. Verification passed. Nothing reaches ${MAIN} without the gate below${BY_RECEIPT ? ', or a receipt that proves this exact tree' : ''}. Stop with ok=false at the first failure and change nothing further.
${LAUNCHED}
0. Note the commit ${MAIN} points at now (git -C ${P} rev-parse ${MAIN}): that is \`before\`.
1. In ${wt(f)}: rebase feat/${f.name} onto ${MAIN}${A.setup ? ` (if dependency manifests changed, run: ${A.setup})` : ''}.
2. ${BY_RECEIPT ? MERGE_RECEIPT(f) : ''}Run the GATE once on that exact tree — ${A.gate} — and ${RUN_GATE(A.gate, wt(f))}
3. Fast-forward ${MAIN} to feat/${f.name}${LANES > 1 ? ` (git -C ${P} checkout ${MAIN} && git -C ${P} merge --ff-only feat/${f.name})` : ` (git checkout ${MAIN} && git merge --ff-only feat/${f.name})`}.${A.push ? ` Then git push origin ${MAIN}.` : ' Do not push: pushing is the owner\'s call.'}
${POST_MERGE}4. ${LANES > 1 ? `git -C ${P} worktree remove ${wt(f)}; ` : ''}git branch -d feat/${f.name}.
Reply with ok, before, the new ${MAIN} commit and notes${A.postMerge ? ', and postMerge (true only if the post-merge command exited 0)' : ''}.`

// ---- triage (level unblock only): classify by script, repair without loosening, check, merge ----
const TRIAGE = (merged, failures, base, specs, cycle) => `You are the TRIAGE of a build pipeline for the project at ${P}, manager mode at level unblock, cycle ${cycle}. The batch barrier (${A.barrierGate}) failed after these features merged into ${MAIN}: ${merged.join(', ')}. You change nothing.
${LAUNCHED}
THE FAILURES the barrier reported: ${JSON.stringify(failures || [])}
For each failing test, write ONE command that runs just that test from the project root and exits non-zero when it fails. Select the test by its NAME or id, never a file:line — a line moves the moment anyone adds one above it, and the command then runs no test: a pytest node id (path.py::test_name), npx playwright test <file> --grep "<exact title>" (-g), -t "<exact name>" for jest and vitest, or the runner's own name filter; the filters are regular expressions, so escape the title's special characters and anchor it. Then run:
python3 ${SKILL}/scripts/triage-probe.py --root ${P} --base ${base} --test "<that command>" --runs 3${A.setup ? ` --setup "${A.setup}"` : ''} ${specs.map(x => '--merged ' + x).join(' ')}
It checks out ${MAIN} as it was before these merges and as it is now into temporary worktrees, runs the test in both, and prints its kind: regression (with the commit and the merged feature that introduced it), preexisting (it fails before the merges too), or not-reproduced. Its classification is the answer: copy it, never override it. If a failure is not a test (the barrier could not start, a service did not come up), report it as not-reproduced with what you saw.
Reply with items: one per failing test, with test, command, kind, feature (for a regression) and evidence (the probe's JSON).`

const REPAIR = (items, cycle) => `You are the REPAIRER of a triaged barrier failure in the project at ${P}, manager mode at level unblock. Nobody is available: decide, never ask.
${LAUNCHED}
Work on a new branch triage/${cycle} created from ${MAIN} in ${P}. The items, classified by a script you do not second-guess:
${JSON.stringify(items, null, 1)}
- A REGRESSION: the named merged feature broke that test. (If the feature is \`earlier-run\`, the break is in merges of an earlier run, not a feature name: find the owner with git log -1 <the commit in the evidence> and its feature-brief.py.) Fix the feature's code so the test passes and that feature's own acceptance criteria still hold (python3 ${SKILL}/scripts/feature-brief.py <feature> --root ${P}). Do not edit the test — the one exception is an owner decision recorded in the roadmap that revokes exactly its assertion, and then only as TESTS below allows.
- PREEXISTING: the test failed before these merges too — broken, or flaky. Find the cause and fix it at the root: in the test when the test is wrong about timing, ordering or shared state (an unordered result compared as ordered, a wait on the wrong event, state leaking between tests), in the code when the code is wrong. Never raise a timeout, never loosen, narrow or delete an assertion, never skip it or mark it expected to fail, never add a retry.
Identify a test by its name, never a file:line, when you write a command or a note about it: a line moves when you add one above it. Your fix keeps the test's name, so a command that selects by name still finds the test.
Prove each fix: run its test 10 times in a row with no retries; all 10 must pass. Commit each fix on its own, message "TRIAGE <kind> <test>: <cause>".
${LONG_COMMANDS}
${REPAIR_TESTS}
Reply ready (true only when every item is fixed and proved), fixed (one line each: test, cause, change, proof) and blockers.`

const CHECK = (items, cycle) => `You are the CHECKER of a triage repair in the project at ${P}. You did not write it; try to show it is wrong. You change nothing.
${LAUNCHED}
Review git diff ${MAIN}...triage/${cycle} against these items: ${JSON.stringify(items)}.
Refuse (ok=false) any change that raises a timeout, loosens, narrows or deletes an assertion, adds a skip, an expected-failure mark or a retry, edits the test of a REGRESSION (unless an owner decision recorded in the roadmap revokes exactly that assertion — read it), or does not address the cause the commit names. Then run each item's test 10 times in a row with no retries on triage/${cycle}; every run must pass, and a run counts only if it actually ran that test.
A command that selects by file:line can select nothing once the repair added or removed a line above the test; "No tests found", "no tests ran" or 0 collected is then a defective command, never evidence of a wrong repair. Derive the command from its NAME (a pytest node id, --grep or -g for Playwright, -t for jest and vitest), confirm with the runner's list or collect-only mode (--list, --collect-only, --listTests) that it selects exactly that test, and use that command for the 10 runs; each run's output must show that one test passing. The test must still exist under the same name in the diff: a rename or a move counts as a deletion, and is refused. If no command can be made to select exactly that test, reply ok=false with a major issue naming the missing selector — never ok=true on runs that ran nothing. Only a test that ran and failed counts against the repair.
Reply ok and issues (each: severity, where, problem, fix).`

const TRIAGE_MERGE = cycle => `You are the MERGER of a triage repair in the project at ${P}. Its checker passed. Nothing reaches ${MAIN} without the gate below. Stop with ok=false at the first failure and change nothing further.
${LAUNCHED}
0. Note the commit ${MAIN} points at now: that is \`before\`.
1. In ${P}: rebase triage/${cycle} onto ${MAIN}.
2. Run the GATE once on that exact tree — ${A.gate} — and ${RUN_GATE(A.gate, P)}
3. Fast-forward ${MAIN} to triage/${cycle} (git checkout ${MAIN} && git merge --ff-only triage/${cycle}).${A.push ? ` Then git push origin ${MAIN}.` : ' Do not push.'}
4. git branch -d triage/${cycle}.
Reply with ok, before, the new ${MAIN} commit and notes.`

const EARLIER = 'earlier-run'
const sinceText = merged => merged.map(n => n === EARLIER ? `an earlier run's merges (${A.barrierPending.base.slice(0, 9)}..${A.barrierPending.head.slice(0, 9)}), which no green barrier ever proved` : n).join(', ')
const BARRIER = merged => `You are the BARRIER of a build pipeline for the project at ${P}. These have been merged into ${MAIN} since the last green barrier: ${sinceText(merged)}. Nothing more merges until you report.
${LAUNCHED}
You change no code and fix nothing. On ${MAIN}, in ${P}${LANES > 1 ? '' : ` (git checkout ${MAIN} first)`}, note the commit ${MAIN} points at (git -C ${P} rev-parse ${MAIN}), then run the project's barrier — ${A.barrierGate} — and ${RUN_GATE(A.barrierGate || '', P)}
The tree must be clean on ${MAIN} before the barrier runs: if \`git -C ${P} status --porcelain\` prints anything, change nothing, run no barrier and reply ok=false with exitCode -1 and that output as the failure — a barrier that ran on uncommitted work proves nothing.
Recording the proof is part of your task: only if the barrier exited 0, run python3 ${SKILL}/scripts/record-barrier.py --root ${P} --sha <that commit>. Never for a red or unfinished barrier: the next run reads that record to know what is proved.
Reply with ok (true only if the barrier finished and exited 0), exitCode, and failures: the failing tests or files, as the log names them.`

// The record lands on the main branch and is committed: on the first real run a blocked feature
// left the tree on its branch, and the record sat there uncommitted for the next session to trip on.
const RECORD = (outcomes) => `In the project at ${P}, record this pipeline run. ${LAUNCHED.replace('Your task is the ROLE below.', 'Your task is this record.')}
1. In ${P}: git checkout ${MAIN}. If that is refused because of uncommitted changes, do not stash, discard or commit them: skip to step 3 with recorded=false and name the files.
2. Write the account below to a temporary file outside the project, then run:
python3 ${SKILL}/scripts/status-block.py ${A.statusPath} --last-run "<one line: how many merged, blocked, skipped, and the first blocked feature if any>" --note <that file>
then delete the file, and commit exactly ${A.statusPath} and docs/roadmap-history.md on ${MAIN} with the message "docs: record pipeline run". Change nothing else.
3. Reply recorded=true only when that commit exists. The account:
${JSON.stringify(outcomes, null, 1)}`

const ISSUES = { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, where: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'where', 'problem', 'fix'] } }
const BUILD_SCHEMA = { type: 'object', properties: { ready: { type: 'boolean' }, summary: { type: 'string' }, blockers: { type: 'array', items: { type: 'string' } } }, required: ['ready', 'summary', 'blockers'] }
const PROVE_SCHEMA = { type: 'object', properties: { ready: { type: 'boolean' }, notes: { type: 'string' }, blockers: { type: 'array', items: { type: 'string' } } }, required: ['ready', 'notes', 'blockers'] }
const VERIFY_SCHEMA = { type: 'object', properties: { gateExit: { type: 'number' }, pass: { type: 'boolean' }, notMet: { type: 'array', items: { type: 'string' } }, issues: ISSUES }, required: ['gateExit', 'pass', 'notMet', 'issues'] }
const REVIEW_SCHEMA = { type: 'object', properties: { issues: ISSUES }, required: ['issues'] }
const MERGE_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, before: { type: 'string' }, commit: { type: 'string' }, notes: { type: 'string' }, postMerge: { type: 'boolean' } }, required: ['ok', 'before', 'commit', 'notes'] }
const TRIAGE_SCHEMA = { type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: { test: { type: 'string' }, command: { type: 'string' }, kind: { type: 'string', enum: ['regression', 'preexisting', 'not-reproduced'] }, feature: { type: 'string' }, evidence: { type: 'string' } }, required: ['test', 'command', 'kind', 'evidence'] } } }, required: ['items'] }
const REPAIR_SCHEMA = { type: 'object', properties: { ready: { type: 'boolean' }, fixed: { type: 'array', items: { type: 'string' } }, blockers: { type: 'array', items: { type: 'string' } } }, required: ['ready', 'fixed', 'blockers'] }
const CHECK_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, issues: ISSUES }, required: ['ok', 'issues'] }
const BARRIER_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, exitCode: { type: 'number' }, failures: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'exitCode', 'failures'] }
const RECORD_SCHEMA = { type: 'object', properties: { recorded: { type: 'boolean' } }, required: ['recorded'] }

// ---- scheduling: one queue per lane, a feature waits for its dependencies, merges serialized ----
const names = new Set(FEATURES.map(f => f.name))
const queues = {}
for (const f of FEATURES) (queues[laneOf(f)] = queues[laneOf(f)] || []).push(f)
{ // refuse a cycle (including one created by lane order) instead of waiting forever
  const edges = {}
  for (const f of FEATURES) edges[f.name] = (f.dependsOn || []).filter(d => names.has(d))
  for (const q of Object.values(queues)) for (let i = 1; i < q.length; i++) edges[q[i].name].push(q[i - 1].name)
  const st = {}
  const visit = n => {
    if (st[n] === 2) return
    if (st[n] === 1) throw new Error('scheduling cycle through ' + n)
    st[n] = 1
    for (const d of edges[n]) visit(d)
    st[n] = 2
  }
  for (const n of Object.keys(edges)) visit(n)
}
const settled = {}
const resolve = {}
for (const f of FEATURES) settled[f.name] = new Promise(r => { resolve[f.name] = r })
let mergeTail = Promise.resolve()
const withMergeLock = fn => { const run = mergeTail.then(fn); mergeTail = run.then(() => {}, () => {}); return run }

const outcomes = []
const blocked = new Set()
const serious = list => (list || []).filter(i => i && i.severity !== 'minor')

// The barrier runs inside the merge lock, so nothing merges while it runs; red stops every later
// merge and build, because building on a main branch the whole suite refuses spends quota on a
// base nobody has proved.
let sinceBarrier = []
let barrierRed = null
let postMergeFailed = null  // the feature after whose merge the post-merge command did not exit 0
const mergedAt = {}
// A run paused inside its barrier leaves merges no green barrier proved; the next run owes it, and the
// triage reads its base from the commit recorded as last proved.
if (A.barrierGate && A.barrierPending && A.barrierPending.base) {
  sinceBarrier = [EARLIER]
  mergedAt[EARLIER] = { before: A.barrierPending.base, after: A.barrierPending.head }
}
const TRIAGE_EFFORT = EFFORT.triage || 'high'

// Level unblock: at most two triage cycles per red barrier. The classification is triage-probe.py's
// (the same test run on the main branch before these merges and after them), never an agent's view;
// anything it cannot reproduce stops the run exactly as level decide would.
const repair = async (merged, failures) => {
  const base = mergedAt[merged[0]] && mergedAt[merged[0]].before
  const specs = merged.filter(n => mergedAt[n]).map(n => `${n}:${mergedAt[n].before}:${mergedAt[n].after}`)
  const stop = (because, cycle) => { outcomes.push({ name: 'triage', result: 'stopped', cycle, because }); log(`triage: stopped — ${because}`); return false }
  if (!base) return stop('no base commit was recorded for these merges', 1)
  for (let cycle = 1; cycle <= 2; cycle++) {
    const t = await agent(TRIAGE(merged, failures, base, specs, cycle), { phase: 'Barrier', label: `triage:${cycle}`, schema: TRIAGE_SCHEMA, effort: TRIAGE_EFFORT, ...modelFor('triage') })
    const items = (t && t.items) || []
    if (!items.length) return stop('nothing could be classified', cycle)
    if (items.some(i => i.kind === 'not-reproduced')) return stop('a failure did not reproduce on either tree: ' + items.filter(i => i.kind === 'not-reproduced').map(i => i.test).join(', '), cycle)
    const fx = await agent(REPAIR(items, cycle), { phase: 'Barrier', label: `repair:${cycle}`, schema: REPAIR_SCHEMA, effort: effortFor('implement', { tier: 'A' }), ...modelFor('build') })
    if (!fx || !fx.ready) return stop('the repair did not finish: ' + (fx ? fx.blockers.join('; ') : 'no result'), cycle)
    const ck = await agent(CHECK(items, cycle), { phase: 'Barrier', label: `check:${cycle}`, schema: CHECK_SCHEMA, effort: TRIAGE_EFFORT, ...modelFor('verify') })
    if (!ck || !ck.ok || serious(ck.issues).length) return stop('the checker refused the repair: ' + (ck ? serious(ck.issues).map(i => i.problem).join('; ') : 'no result'), cycle)
    const m = await agent(TRIAGE_MERGE(cycle), { phase: 'Barrier', label: `merge:triage-${cycle}`, schema: MERGE_SCHEMA, effort: effortFor('merge', { tier: 'B' }), ...modelFor('merge') })
    if (!m || !m.ok) return stop('the repair did not merge: ' + (m ? m.notes : 'no result'), cycle)
    const b = await agent(BARRIER(merged), { phase: 'Barrier', label: `barrier:after-triage-${cycle}`, schema: BARRIER_SCHEMA, effort: effortFor('merge', { tier: 'B' }), ...modelFor('barrier') })
    const green = !!(b && b.ok && b.exitCode === 0)
    outcomes.push({ name: 'triage', result: green ? 'repaired' : 'not enough', cycle, items: items.map(i => `${i.kind}${i.feature ? ' in ' + i.feature : ''}: ${i.test}`) })
    outcomes.push({ name: 'barrier', result: green ? 'green' : 'red', after: merged, failures: b ? b.failures : ['the barrier returned nothing'] })
    log(`triage cycle ${cycle}: barrier ${green ? 'green' : 'still red'}`)
    if (green) return true
    failures = b ? b.failures : []
  }
  return false
}

const runBarrier = async () => {
  if (!A.barrierGate || !sinceBarrier.length || postMergeFailed) return  // main is not in step with its environment: a barrier now proves nothing
  const merged = sinceBarrier
  sinceBarrier = []
  const b = await agent(BARRIER(merged), { phase: 'Barrier', label: `barrier:${merged[merged.length - 1]}`, schema: BARRIER_SCHEMA, effort: effortFor('merge', { tier: 'B' }), ...modelFor('barrier') })
  let green = !!(b && b.ok && b.exitCode === 0)
  outcomes.push({ name: 'barrier', result: green ? 'green' : 'red', after: merged, failures: b ? b.failures : ['the barrier returned nothing'] })
  log(`barrier after ${merged.join(', ')}: ${green ? 'green' : 'red'}`)
  if (!green && UNBLOCK) green = await repair(merged, b ? b.failures : [])
  if (!green) barrierRed = merged
}
const hold = f => {
  const why = barrierRed ? 'the barrier is red' : `the post-merge command failed after ${postMergeFailed}`
  blocked.add(f.name); outcomes.push({ name: f.name, result: 'held', because: why }); log(`${f.name}: held (${why})`)
}

const runFeature = async f => {
  await Promise.all((f.dependsOn || []).filter(d => settled[d]).map(d => settled[d]))
  const bad = (f.dependsOn || []).find(d => blocked.has(d))
  if (bad) { blocked.add(f.name); outcomes.push({ name: f.name, result: 'skipped', because: bad }); log(`${f.name}: skipped (depends on ${bad})`); return }
  const tier = tierOf(f)
  let feedback = f.feedback || null
  let passedAt = 0
  let staleReport = false
  for (let attempt = f.startAttempt || 1; attempt <= MAX[tier] && !passedAt; attempt++) {
    if (barrierRed || postMergeFailed) { hold(f); return }
    const built = await agent(IMPLEMENT(f, attempt, feedback), { phase: 'Build', label: `build:${f.name}:${attempt}`, schema: BUILD_SCHEMA, effort: effortFor('implement', f), ...modelFor('build') })
    if (!built || !built.ready) {
      feedback = [{ severity: 'blocker', where: 'build', problem: 'the builder did not finish: ' + (built ? built.blockers.join('; ') : 'no result'), fix: 'finish the work on the existing branch' }]
      continue
    }
    let gateRefused = false
    const proveStep = async () => {
      const proved = await agent(PROVE(f), { phase: 'Build', label: `prove:${f.name}:${attempt}`, schema: PROVE_SCHEMA, effort: effortFor('prove', f), ...modelFor('prove') })
      if (proved && proved.ready) return true
      feedback = ((proved && proved.blockers.length) ? proved.blockers : ['the prover did not finish, or the gate failed'])
        .map(b => ({ severity: 'blocker', where: 'prove', problem: b, fix: 'make the gate pass on the rebased tree' }))
      return false
    }
    if (!VERIFY_FIRST && !(await proveStep())) continue
    const thunks = [() => agent(VERIFY(f, attempt), { phase: 'Verify', label: `verify:${f.name}:${attempt}`, schema: VERIFY_SCHEMA, effort: effortFor('verify', f), ...modelFor('verify') })]
    if (tier === 'A') thunks.push(() => agent(REVIEW(f), { phase: 'Verify', label: `review:${f.name}:${attempt}`, schema: REVIEW_SCHEMA, effort: effortFor('review', f), ...modelFor('review') }))
    const [ver, rev] = await parallel(thunks)
    let pass = !!(ver && ver.pass && ver.gateExit === 0 && serious(ver.issues).length === 0 &&
      (tier !== 'A' || (rev && serious(rev.issues).length === 0)))
    // verify-first: the full gate runs only now, for a feature that was passed. A refusal here leaves a PASS
    // report on the branch that the gate did not back; it is said in the run's account, not hidden.
    if (pass && VERIFY_FIRST) { pass = await proveStep(); gateRefused = !pass }
    if (ver) staleReport = gateRefused
    log(`${f.name}: attempt ${attempt} ${pass ? 'passed' : gateRefused ? 'passed verification, refused by the gate' : 'refused'}`)
    if (pass) { passedAt = attempt; break }
    if (gateRefused) continue
    feedback = [...serious(ver && ver.issues), ...serious(rev && rev.issues),
      ...((ver && ver.notMet) || []).map(n => ({ severity: 'blocker', where: 'criterion', problem: 'not met: ' + n, fix: 'meet it' }))]
    if (ver && ver.gateExit !== 0 && !feedback.length) feedback.push({ severity: 'blocker', where: 'gate', problem: `${GATE_SCRIPT} exited ${ver.gateExit}`, fix: 'read the report the verifier wrote' })
    if (!ver) feedback.push({ severity: 'blocker', where: 'verify', problem: 'the verifier returned nothing', fix: 're-run verification' })
  }
  if (!passedAt) {
    blocked.add(f.name)
    outcomes.push({ name: f.name, result: 'blocked', lastIssues: (feedback || []).slice(0, 5),
      ...(staleReport ? { because: `branch feat/${f.name} carries a PASS report that the gate refused` } : {}) })
    log(`${f.name}: blocked after ${MAX[tier]} attempts`)
    return
  }
  const doMerge = async () => {
    if (barrierRed || postMergeFailed) return { held: true }
    const m = await agent(MERGE(f), { phase: 'Merge', label: `merge:${f.name}`, schema: MERGE_SCHEMA, effort: effortFor('merge', f), ...modelFor('merge') })
    if (m && m.ok) {
      const postFailed = !!A.postMerge && m.postMerge !== true  // anything but an explicit true is a failure: it is the safe reading
      outcomes.push({ name: f.name, result: 'merged', attempt: passedAt, commit: m.commit, ...(/gate skipped/i.test(m.notes || '') ? { gateSkipped: true } : {}), ...(postFailed ? { postMergeFailed: true } : {}) })
      mergedAt[f.name] = { before: m.before, after: m.commit }
      log(`${f.name}: merged`)
      sinceBarrier.push(f.name)
      if (postFailed) { postMergeFailed = f.name; log(`${f.name}: merged, but the post-merge command did not exit 0`) }
      else if (BARRIER_EVERY && sinceBarrier.length >= BARRIER_EVERY) await runBarrier()
    }
    return m
  }
  const m = await withMergeLock(doMerge)
  if (m && m.held) { hold(f); return }
  if (m && m.ok) return
  blocked.add(f.name)
  outcomes.push({ name: f.name, result: 'merge-failed', notes: m ? m.notes : 'no result' })
  log(`${f.name}: merge failed`)
}

await withMergeLock(runBarrier)

await parallel(Object.values(queues).map(q => async () => {
  for (const f of q) { try { await runFeature(f) } finally { resolve[f.name]() } }
}))

await withMergeLock(runBarrier)

phase('Record')
await agent(RECORD(outcomes), { phase: 'Record', label: 'record', schema: RECORD_SCHEMA, effort: effortFor('record', { tier: 'B' }), ...modelFor('record') })
return outcomes.map(o => o.name === 'barrier'
  ? `barrier: ${o.result} after ${o.after.join(', ')}${o.result === 'red' ? ' — ' + (o.failures || []).slice(0, 5).join('; ') : ''}`
  : o.name === 'triage'
  ? `triage: ${o.result} (cycle ${o.cycle})${o.items ? ' — ' + o.items.join('; ') : ''}${o.because ? ' — ' + o.because : ''}`
  : `${o.name}: ${o.result}${o.attempt ? ' (attempt ' + o.attempt + ')' : ''}${o.gateSkipped ? ' [gate skipped: receipt]' : ''}${o.postMergeFailed ? ' [post-merge command failed]' : ''}${o.result === 'skipped' ? ' — depends on ' + o.because : o.because ? ' — ' + o.because : ''}`)
