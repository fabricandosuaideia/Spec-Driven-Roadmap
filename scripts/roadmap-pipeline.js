export const meta = {
  name: 'roadmap-pipeline',
  description: 'Build pending roadmap features: implement, prove on a fresh context, verify (and review for tier A), merge only on pass',
  whenToUse: 'Run with the args printed by spec-driven-roadmap scripts/plan-pipeline.py, only when the user asked to run the pipeline',
  phases: [
    { title: 'Build', detail: 'a builder implements on feat/<name>; a fresh prover rebases, runs the full gate once and writes the receipt' },
    { title: 'Verify', detail: 'the downstream skill verifier (and, for tier A, an independent reviewer) — never the builder' },
    { title: 'Merge', detail: 'the authoritative gate on the exact tree, then a fast-forward into the main branch' },
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
// args (from plan-pipeline.py): { project, skillDir, downstream, downstreamDir, statusPath, mainBranch,
//   gate, testHint, setup, push, lanes, worktreeRoot, checklist, effort, maxAttempts,
//   features: [{ name, roadmap, tier, dependsOn[], lane, startAttempt?, feedback? }] }

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
if (!P || !SKILL || !DS || !DSDIR || !A.gate) throw new Error('args incomplete: run plan-pipeline.py and pass its output as args')

const tierOf = f => (f.tier === 'A' || f.tier === 'C') ? f.tier : 'B'
const laneOf = f => Math.min(LANES, Math.max(1, f.lane || 1))
const wt = f => LANES > 1 ? `${A.worktreeRoot}/lane${laneOf(f)}/${f.name}` : P
const effortFor = (role, f) => {
  const e = EFFORT[role]
  return (e && typeof e === 'object') ? e[tierOf(f)] : e
}
const HASH = `git diff ${MAIN}...HEAD -- . ':!.specs' ':!docs' | sha256sum | cut -d' ' -f1`

const WORKTREE = f => LANES > 1
  ? `WORKING TREE: ${wt(f)} (branch feat/${f.name}); if it does not exist create it with: git -C ${P} worktree add -b feat/${f.name} ${wt(f)} ${MAIN} || git -C ${P} worktree add ${wt(f)} feat/${f.name}${A.setup ? `, then in it: ${A.setup}` : ''}. Work only there; never run commands in ${P}.`
  : `WORKING TREE: ${P}. Work on branch feat/${f.name} (git checkout feat/${f.name}, creating it from ${MAIN} if it does not exist).`

const COMMON = f => `You are one agent of a build pipeline for the project at ${P}. Nobody is available to answer: decide, record the decision where ${DS} keeps assumptions, never ask.
FEATURE: ${f.name}, risk tier ${tierOf(f)}. Its spec source is the output of: python3 ${SKILL}/scripts/feature-brief.py ${f.name} --root ${P} — the entry, the questions naming it, the contracts it consumes, the settled Cross-Cutting Decisions, and what tier ${tierOf(f)} sets for ${DS}. Never open a docs/ROADMAP*.md file whole.
DOWNSTREAM SKILL: ${DS}, at ${DSDIR}. Read its SKILL.md and only the references your role needs.
${WORKTREE(f)}
CONTEXT BUDGET: every turn re-reads your whole conversation. Read files with offset/limit, grep for a symbol instead of reading a directory, send long command output to a file and read back only the lines that matter, never paste a whole log or diff, never re-read a file that did not change.
TESTS: never edit, weaken, skip, delete or add a test to reach a pass, and never change behaviour against an acceptance criterion or a settled Cross-Cutting Decision to turn a test green. A test that is genuinely wrong stays red, with the reason written down.`

const ANGLES = [
  'Build the feature exactly as its spec source states.',
  'The previous attempt was refused. Resolve every listed issue precisely; do not widen scope and do not undo what already passes.',
  'Two attempts have been refused. BEFORE writing code, write in one sentence the invariant the refusals share (the single rule that, enforced in one place, prevents all of them), record it with your notes, then satisfy it with the smallest change — a different place or shape if needed, reusing what already works.',
  'Three attempts have been refused. Restate the invariant if the last one was wrong or incomplete, then make the smallest change that enforces it and meets every criterion. If one criterion is truly impossible as written, say exactly why and meet all the others.',
  'Several attempts have been refused, each time on a narrower variant of the same cause. Fix ONLY the blocker and major issues below, at the root (state the invariant, enforce it in one place), leave minor ones alone, do not refactor.',
]

const IMPLEMENT = (f, attempt, feedback) => `${COMMON(f)}

ROLE: BUILDER, attempt ${attempt} of ${MAX[tierOf(f)]}. ${ANGLES[Math.min(attempt, ANGLES.length) - 1]}
${attempt > 1 ? `First rebase feat/${f.name} onto ${MAIN}. Issues to resolve (check each against the code first; if one is wrong, say why in your notes):\n${JSON.stringify(feedback || [], null, 1)}\n` : ''}Run ${DS}'s cycle for this feature through its last commit: ${LEAN ? 'plan and checks (approve them yourself and write that you did in plan.md under ## Assumptions), then build' : 'spec, design and tasks at the depth the tier sets (approve them yourself and write that you did in the spec under Assumptions & Open Questions), then execute'}. Commit atomically.
While you work, run only the tests related to what you touched${A.testHint ? ` (${A.testHint})` : ''}. Do NOT run the full gate and do NOT write ${REPORT}: a fresh prover and an independent verifier come after you.
${A.checklist ? `Before you finish, check your diff against every item of ${A.checklist} (the problems reviewers kept finding in this project) and fix what fails.\n` : ''}DEFERRED SCOPE: an issue that is the declared scope of a LATER feature in the build order is not yours: name that feature in your notes and move on.
Reply ready=true once every change is committed, even though the full gate has not run; otherwise ready=false with blockers.`

const PROVE = f => `${COMMON(f)}

ROLE: PROVER, on a fresh context. A builder already committed this feature on feat/${f.name}; you did not write it. Do not re-implement and do not widen scope.
1. Rebase feat/${f.name} onto ${MAIN}${A.setup ? ` (if dependency manifests changed, run: ${A.setup})` : ''}.
2. Run the FULL GATE once on this exact tree, output to a file, then read only its tail and failures: ${A.gate}
   A failure is a defect, never "environmental": reply ready=false naming the failing test or file, and fix nothing.
3. Write .specs/features/${f.name}/gate-receipt.json as {"codeHash":"<output of: ${HASH}>","gate":"pass","command":<the gate command>} and commit it.
Reply ready=true only when the rebase is clean, the gate passed and the receipt is committed.`

const VERIFY = f => `${COMMON(f)}

ROLE: VERIFIER. You did not build this; try to show it is NOT done. Follow ${DS}'s ${LEAN ? 'references/verify.md' : 'references/validate.md'} over every ${LEAN ? 'check' : 'acceptance criterion'}. You change no code.
GATES BY RECEIPT: recompute the code hash (${HASH}); if it equals .specs/features/${f.name}/gate-receipt.json's codeHash and the receipt says pass, do NOT re-run the full gate — run only this feature's tests and ${DS}'s own fault injection or discrimination sensor. If it differs or is missing, run the full gate yourself (${A.gate}) and report that as a minor issue.
${LEAN ? 'Write verification.md exactly as verify.md prescribes, with **Verdict**: PASS or FAIL at the top.' : 'Write validation.md from validate.md\'s template with ONE line reading "## Validation: ' + f.name + ' — PASS" or "— FAIL" as the only verdict the gate can see: relabel the sensor and gate-check result fields (**Sensor verdict** —, **Gate outcome** —); per-criterion rows say MET or NOT MET, never PASS.'} Cite file:line evidence. Commit the report.
Then run the completion gate: python3 ${DSDIR}/scripts/${GATE_SCRIPT} ${f.name} --root ${wt(f)} — and report its exit code as the script returned it, never through a pipe.${tierOf(f) === 'C' ? '\nThis is a tier C feature and no reviewer follows you: review the diff for correctness, security and weak tests as well, and list those issues too.' : ''}
Reply with gateExit, pass (true only if gateExit is 0, every ${LEAN ? 'check' : 'criterion'} holds and you found no blocker or major issue), notMet and issues.`

const REVIEW = f => `${COMMON(f)}

ROLE: CODE REVIEWER, independent of the builder and the verifier. Review git diff ${MAIN}...feat/${f.name}; read a changed file in full only where the diff is not enough. You edit and commit nothing, and you do not run the full suite.
Look for: correctness and unhandled edge cases; non-atomic read-then-write on shared state; state written before validation; security (injection, missing authorisation, secrets in logs or persisted text); swallowed errors; missing timeouts; unbounded queries or per-row query loops; a duplicate of a helper that already exists; weak or tautological tests; comments that claim more than the code does.${A.checklist ? ` Also every item of ${A.checklist}.` : ''}
The builder's and the prover's notes are claims: spot-check the few most likely to be wrong instead of re-deriving everything.
Report each issue with severity blocker | major | minor, where (file:line), problem and fix.`

const MERGE = f => `You are the MERGER for feature ${f.name} in the project at ${P}. Verification passed. Nothing reaches ${MAIN} without the gate below. Stop with ok=false at the first failure and change nothing further.
1. In ${wt(f)}: rebase feat/${f.name} onto ${MAIN}${A.setup ? ` (if dependency manifests changed, run: ${A.setup})` : ''}.
2. Run the FULL GATE once on that exact tree, output to a file, reading only its tail and failures: ${A.gate}
3. Fast-forward ${MAIN} to feat/${f.name}${LANES > 1 ? ` (git -C ${P} checkout ${MAIN} && git -C ${P} merge --ff-only feat/${f.name})` : ` (git checkout ${MAIN} && git merge --ff-only feat/${f.name})`}.${A.push ? ` Then git push origin ${MAIN}.` : ' Do not push: pushing is the owner\'s call.'}
4. ${LANES > 1 ? `git -C ${P} worktree remove ${wt(f)}; ` : ''}git branch -d feat/${f.name}.
Reply with ok, the new ${MAIN} commit and notes.`

const RECORD = (outcomes) => `In the project at ${P}, record this pipeline run. Write the account below to a temporary file, then run:
python3 ${SKILL}/scripts/status-block.py ${A.statusPath} --last-run "<one line: how many merged, blocked, skipped, and the first blocked feature if any>" --note <that file>
then delete the file. Change nothing else. The account:
${JSON.stringify(outcomes, null, 1)}`

const ISSUES = { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, where: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'where', 'problem', 'fix'] } }
const BUILD_SCHEMA = { type: 'object', properties: { ready: { type: 'boolean' }, summary: { type: 'string' }, blockers: { type: 'array', items: { type: 'string' } } }, required: ['ready', 'summary', 'blockers'] }
const PROVE_SCHEMA = { type: 'object', properties: { ready: { type: 'boolean' }, notes: { type: 'string' }, blockers: { type: 'array', items: { type: 'string' } } }, required: ['ready', 'notes', 'blockers'] }
const VERIFY_SCHEMA = { type: 'object', properties: { gateExit: { type: 'number' }, pass: { type: 'boolean' }, notMet: { type: 'array', items: { type: 'string' } }, issues: ISSUES }, required: ['gateExit', 'pass', 'notMet', 'issues'] }
const REVIEW_SCHEMA = { type: 'object', properties: { issues: ISSUES }, required: ['issues'] }
const MERGE_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, commit: { type: 'string' }, notes: { type: 'string' } }, required: ['ok', 'commit', 'notes'] }
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

const runFeature = async f => {
  await Promise.all((f.dependsOn || []).filter(d => settled[d]).map(d => settled[d]))
  const bad = (f.dependsOn || []).find(d => blocked.has(d))
  if (bad) { blocked.add(f.name); outcomes.push({ name: f.name, result: 'skipped', because: bad }); log(`${f.name}: skipped (depends on ${bad})`); return }
  const tier = tierOf(f)
  let feedback = f.feedback || null
  let passedAt = 0
  for (let attempt = f.startAttempt || 1; attempt <= MAX[tier] && !passedAt; attempt++) {
    const built = await agent(IMPLEMENT(f, attempt, feedback), { phase: 'Build', label: `build:${f.name}:${attempt}`, schema: BUILD_SCHEMA, effort: effortFor('implement', f) })
    if (!built || !built.ready) {
      feedback = [{ severity: 'blocker', where: 'build', problem: 'the builder did not finish: ' + (built ? built.blockers.join('; ') : 'no result'), fix: 'finish the work on the existing branch' }]
      continue
    }
    const proved = await agent(PROVE(f), { phase: 'Build', label: `prove:${f.name}:${attempt}`, schema: PROVE_SCHEMA, effort: effortFor('prove', f) })
    if (!proved || !proved.ready) {
      feedback = ((proved && proved.blockers.length) ? proved.blockers : ['the prover did not finish, or the gate failed'])
        .map(b => ({ severity: 'blocker', where: 'prove', problem: b, fix: 'make the full gate pass on the rebased tree' }))
      continue
    }
    const thunks = [() => agent(VERIFY(f), { phase: 'Verify', label: `verify:${f.name}:${attempt}`, schema: VERIFY_SCHEMA, effort: effortFor('verify', f) })]
    if (tier === 'A') thunks.push(() => agent(REVIEW(f), { phase: 'Verify', label: `review:${f.name}:${attempt}`, schema: REVIEW_SCHEMA, effort: effortFor('review', f) }))
    const [ver, rev] = await parallel(thunks)
    const pass = !!(ver && ver.pass && ver.gateExit === 0 && serious(ver.issues).length === 0 &&
      (tier !== 'A' || (rev && serious(rev.issues).length === 0)))
    log(`${f.name}: attempt ${attempt} ${pass ? 'passed' : 'refused'}`)
    if (pass) { passedAt = attempt; break }
    feedback = [...serious(ver && ver.issues), ...serious(rev && rev.issues),
      ...((ver && ver.notMet) || []).map(n => ({ severity: 'blocker', where: 'criterion', problem: 'not met: ' + n, fix: 'meet it' }))]
    if (ver && ver.gateExit !== 0 && !feedback.length) feedback.push({ severity: 'blocker', where: 'gate', problem: `${GATE_SCRIPT} exited ${ver.gateExit}`, fix: 'read the report the verifier wrote' })
    if (!ver) feedback.push({ severity: 'blocker', where: 'verify', problem: 'the verifier returned nothing', fix: 're-run verification' })
  }
  if (!passedAt) {
    blocked.add(f.name)
    outcomes.push({ name: f.name, result: 'blocked', lastIssues: (feedback || []).slice(0, 5) })
    log(`${f.name}: blocked after ${MAX[tier]} attempts`)
    return
  }
  const doMerge = () => agent(MERGE(f), { phase: 'Merge', label: `merge:${f.name}`, schema: MERGE_SCHEMA, effort: effortFor('merge', f) })
  const m = await withMergeLock(doMerge)
  if (m && m.ok) { outcomes.push({ name: f.name, result: 'merged', attempt: passedAt, commit: m.commit }); log(`${f.name}: merged`); return }
  blocked.add(f.name)
  outcomes.push({ name: f.name, result: 'merge-failed', notes: m ? m.notes : 'no result' })
  log(`${f.name}: merge failed`)
}

await parallel(Object.values(queues).map(q => async () => {
  for (const f of q) { try { await runFeature(f) } finally { resolve[f.name]() } }
}))

phase('Record')
await agent(RECORD(outcomes), { phase: 'Record', label: 'record', schema: RECORD_SCHEMA, effort: effortFor('record', { tier: 'B' }) })
return outcomes.map(o => `${o.name}: ${o.result}${o.attempt ? ' (attempt ' + o.attempt + ')' : ''}${o.because ? ' — depends on ' + o.because : ''}`)
