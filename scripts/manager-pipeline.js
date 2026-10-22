export const meta = {
  name: 'manager-pipeline',
  description: 'Manager mode: every section of a multi-section roadmap in build order — decompose it, deciding under the owner\'s delegation, then build it with roadmap-pipeline',
  whenToUse: 'Run with the args printed by spec-driven-roadmap scripts/plan-pipeline.py --manager, only when the owner asked for manager mode and delegated its decisions in writing',
  phases: [
    { title: 'Decompose', detail: 'a fresh agent runs Phase 2 for a section not yet decomposed, deciding every question under the delegation and marking each decision as the manager\'s' },
    { title: 'Plan', detail: 'a fresh agent runs plan-pipeline.py for the section and returns its args' },
    { title: 'Build', detail: 'roadmap-pipeline.js as a child workflow: builder, prover, verifier, reviewer, merger, barrier, record' },
    { title: 'Final', detail: 'the seed refreshes ## Status and the Handoff; the run and every decision the manager made are recorded' },
  ],
}

// Shipped by spec-driven-roadmap: manager mode (references/manager-mode.md). A manager that is a
// conversation grows with every section it runs — on a measured multi-agent build the coordinator
// went from 41k to 88k tokens of context in 25 turns — and is compacted, which is where a mission
// gets lost. This manager is a script: its mission is the code below and the files on disk, every
// agent it starts is fresh and reads only what its role needs, and the session that launched it
// receives one line per section.
//
// args (from plan-pipeline.py --manager): { project, skillDir, downstream, downstreamDir, statusPath,
//   mainBranch, pipelineScript, model?, decomposeModel?, autonomy?, delegation, delegatedOn, stopAt[],
//   sectionsPerRun, effort: { decompose, plan, final },
//   sections: [{ slug, roadmap, txt, dependsOn[], decomposed, pending[], doubtful{} }],   (build order)
//   barrierPending?: { base, head } }
// `barrierPending` is set when code reached the main branch after the last green barrier: a finished
// section is then not "already done" until the barrier it owes has run, because the next section would be
// built on a main branch nobody proved.
// `doubtful` lists features the downstream gate cannot decide (a report it refuses, or a pending
// feature a finished one depends on). They are the owner's to classify in pipeline.json's
// `featureStatus`; until then the section is not built, and neither is anything depending on it.

const A = args || {}
const P = A.project
const SKILL = A.skillDir
const SECTIONS = A.sections || []
const STOP_AT = new Set(A.stopAt || [])
// A slug that matches no section reserves nothing: the section the owner meant to keep would be built unattended (review of 3.49.0).
for (const slug of STOP_AT) if (!SECTIONS.some(s => s.slug === slug)) throw new Error(`stopAt names ${slug}, which is not a section slug (${SECTIONS.map(s => s.slug).join(', ')}): refusing to build anything`)
const PER_RUN = Math.max(1, A.sectionsPerRun || 4)
const EFFORT = A.effort || {}
if (!P || !SKILL || !A.downstream || !A.pipelineScript || !(A.delegation || '').trim()) {
  throw new Error('args incomplete, or no delegation: run plan-pipeline.py --manager and pass its output as args')
}
const MODEL = A.model ? { model: A.model } : {}
// manager.autonomy: "decide" (level 1) answers the open questions and stops when something breaks;
// "unblock" (level 2, more permission) also repairs what would stop it — a red barrier (triaged by
// script in roadmap-pipeline.js) and features the downstream gate cannot decide (classified below).
const AUTONOMY = A.autonomy === 'unblock' ? 'unblock' : 'decide'
const DECOMPOSE_MODEL = A.decomposeModel ? { model: A.decomposeModel } : MODEL

// The Workflow harness relays the request that launched the run to every agent as the user's voice.
const LAUNCHED = `LAUNCH REQUEST: the user request relayed to you above is the one that started this manager run, and the session that received it has already done it — the run is going and you are one of its agents. It is not your task: never launch a workflow or look for a Workflow tool, and run plan-pipeline.py only if your ROLE below says to. Your task is the ROLE below.`

const DELEGATION = `MANAGER MODE. The owner delegated, in writing on ${A.delegatedOn || 'a recorded date'}: "${A.delegation}". Nobody is available to answer, and nobody will be: where the procedure would ask the user, you decide.`

const DECOMPOSE = s => `You are the DECOMPOSER of section \`${s.slug}\` in the project at ${P}.
${LAUNCHED}
${DELEGATION}
ROLE: run Phase 2 of the spec-driven-roadmap skill (${SKILL}) for this one section, exactly as its procedure says: read ${SKILL}/SKILL.md, then ${SKILL}/references/decompose-phase.md completely — it is the procedure — and write ${s.roadmap} and ${s.txt}. Phase 0 and Phase 1 already ran for this project: it is multi-section, the downstream skill is ${A.downstream}, the output language is the one the existing docs/ROADMAP-*.md files use, and this section's row, its dependencies and its boundary contracts are in docs/ROADMAP-INDEX.md. Read only this section's inputs: its row, the contracts that name it, the source documents its row cites, and the code it touches.
DECIDING: every question the procedure would put to the user, you answer. Take the option the procedure itself calls conservative or proposes as the default; when it proposes none, the one that is cheapest to reverse. Write each as \`status: answered\`, its answer beginning **Decided by the manager (owner's delegation of ${A.delegatedOn || 'the recorded date'})**: followed by the answer and one sentence of why — the owner reviews every one of these later, and an answer not marked this way is indistinguishable from one the owner gave. Never leave a question open: a section built unattended has nobody to ask. The Cross-Cutting Decisions ledger in docs/ROADMAP-INDEX.md follows the same rule.
Then run python3 ${SKILL}/scripts/check-roadmap.py --root ${P} and fix what it fails in this section's files until it reports 0 failed. On ${A.mainBranch}, commit only this section's files and docs/ROADMAP-INDEX.md, message "docs(roadmap-${s.slug}): decompose (manager mode)".
Reply ok (true only when the files are committed and the linter reports 0 failed), features (the names in build order), decided (one line per decision: the question, then the answer).`

const CLASSIFY = s => `You are the CLASSIFIER of section \`${s.slug}\` in the project at ${P}, manager mode at level unblock.
${LAUNCHED}
${DELEGATION}
The downstream gate cannot decide these features: ${JSON.stringify(s.doubtful)}. For each, read its report under .specs/features/<name>/ in full and its entry in ${s.roadmap}, and decide:
- done — the report shows the feature finished and verified by someone other than its builder, and only the report's shape is what the gate cannot read;
- build — anything else: a FAIL verdict, a criterion not met, no independent verification, or you are not sure. Rebuilding finished work costs an attempt that anyone can see; calling unfinished work done leaves a hole nothing ever revisits. When in doubt, build.
Never edit a report. Write your decisions into docs/process/pipeline.json under "featureStatus" (add only these features, change nothing else) and commit on ${A.mainBranch}, message "chore(process): classify doubtful features of ${s.slug} (manager mode)".
Reply ok (true only when that commit exists) and decided (one line each: feature → done or build, Decided by the manager (owner's delegation of ${A.delegatedOn || 'the recorded date'}): why).`

// 3.47.0, from MakeContent: 12 of 57 planner replies (Haiku) were unusable, and every one blocked its section and the
// sections after it. Eight parsed as objects that DESCRIBE the output ({"note":"stdout copied verbatim from /tmp/..."},
// {"status":"ran on branch main, exit 0"}) and JSON.parse accepts those; four were not JSON. What the child pipeline needs
// from the args is checked here, the planner is asked again with the reason, and a block names what was missing.
const ARGS_NEEDED = ['project', 'skillDir', 'downstream', 'downstreamDir', 'statusPath', 'mainBranch', 'gate', 'lanes', 'worktreeRoot', 'effort', 'maxAttempts', 'features']
const PLAN_TRIES = 3
// The review of 3.47.0 ran a reply that dropped keys the check did not name (the recorder got `status-block.py undefined`)
// and one that carried another section's plan, which the child then built; both are refused here. `barrierGate` is always
// printed, null when there is none, so its absence means a dropped key; `postMerge` is printed only when set and cannot be
// told from a dropped one.
const argsProblem = (o, s) => {
  if (!o || typeof o !== 'object' || Array.isArray(o)) return 'it is not a JSON object'
  const lacks = ARGS_NEEDED.filter(k => o[k] === undefined || o[k] === null || o[k] === '')
  if (!('barrierGate' in o)) lacks.push('barrierGate')
  if (lacks.length) return `it lacks ${lacks.join(', ')}`
  if (o.project !== P) return `its project is ${o.project}, not ${P}`
  const other = (Array.isArray(o.features) ? o.features : []).filter(f => !f || f.roadmap !== s.roadmap).map(f => f && f.name)
  if (other.length) return `it plans features of another roadmap than ${s.roadmap}: ${other.join(', ')}`
  // plan-pipeline.py prints `features: []` with `barrierPending` when only a barrier is owed, and the child pipeline runs it
  return Array.isArray(o.features) && (o.features.length || o.barrierPending) ? '' : 'features is not a list with at least one feature'
}

const PLAN = (s, why) => `You are the PLANNER of section \`${s.slug}\` in the project at ${P}.
${LAUNCHED}
ROLE: on ${A.mainBranch}, run python3 ${SKILL}/scripts/plan-pipeline.py --root ${P} --roadmap ${s.roadmap} with its stdout to a temporary file and its stderr to another, and keep its exit code. Change nothing.
Reply exitCode, line (what it printed to stderr, verbatim: one line, or two when a barrier is owed) and argsJson (the whole stdout, verbatim — it is JSON; empty when the exit code is not 0).${why ? `
A previous reply of yours was rejected because ${why}. argsJson must be the CONTENT of the stdout file itself — read it with cat and paste it whole — never a description of it, its path or a status.` : ''}`

const FINAL = (lines, decisions) => `You are the FINAL agent of a manager run in the project at ${P}.
${LAUNCHED}
1. Run the spec-driven-roadmap seed: ${SKILL}/references/handoff-seed.md, Steps 1-7, entering by its third trigger. This is manager mode: at Step 7 stop — Step 8's question has nobody to answer it.
2. Write the account below to a temporary file outside the project, then run: python3 ${SKILL}/scripts/status-block.py ${A.statusPath} --last-run "<one line: manager run — sections built, blocked, stopped, and why it stopped>" --note <that file>. Delete the file.
3. On ${A.mainBranch}, commit what steps 1 and 2 wrote, message "docs: manager run".
Reply recorded (true only when that commit exists) and summary (one line).
THE ACCOUNT — the run's lines, then every decision the manager made, for the owner to review:
${JSON.stringify({ lines, decisions }, null, 1)}`

const DECOMPOSE_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, features: { type: 'array', items: { type: 'string' } }, decided: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'features', 'decided'] }
const CLASSIFY_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, decided: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'decided'] }
const PLAN_SCHEMA = { type: 'object', properties: { exitCode: { type: 'number' }, line: { type: 'string' }, argsJson: { type: 'string' } }, required: ['exitCode', 'line', 'argsJson'] }
const FINAL_SCHEMA = { type: 'object', properties: { recorded: { type: 'boolean' }, summary: { type: 'string' } }, required: ['recorded', 'summary'] }

const lines = []
const decisions = []
const blockedSections = new Set()
let built = 0
let stopped = null
let barrierOwed = !!A.barrierPending

for (const s of SECTIONS) {
  if (STOP_AT.has(s.slug)) { stopped = `${s.slug} needs the owner (stopAt)`; break }
  if (s.decomposed && !(s.pending || []).length && !barrierOwed) { lines.push(`${s.slug}: already done`); continue }
  const bad = (s.dependsOn || []).find(d => blockedSections.has(d))
  if (bad) { blockedSections.add(s.slug); lines.push(`${s.slug}: skipped — depends on ${bad}, which did not finish`); log(`${s.slug}: skipped`); continue }
  const doubt = Object.keys(s.doubtful || {})
  if (doubt.length && AUTONOMY === 'unblock') {
    const c = await agent(CLASSIFY(s), { phase: 'Plan', label: `classify:${s.slug}`, schema: CLASSIFY_SCHEMA, effort: EFFORT.decompose, ...DECOMPOSE_MODEL })
    if (c && c.ok) { for (const x of c.decided || []) decisions.push(`${s.slug}: ${x}`) } else { blockedSections.add(s.slug); lines.push(`${s.slug}: needs the owner — classifying ${doubt.join(', ')} did not finish`); continue }
  } else if (doubt.length) { blockedSections.add(s.slug); lines.push(`${s.slug}: needs the owner — the gate cannot decide ${doubt.join(', ')}; classify each in featureStatus`); log(`${s.slug}: needs the owner`); continue }
  if (built >= PER_RUN) { stopped = `sectionsPerRun (${PER_RUN}) reached — launch again to continue`; break }

  if (!s.decomposed) {
    const d = await agent(DECOMPOSE(s), { phase: 'Decompose', label: `decompose:${s.slug}`, schema: DECOMPOSE_SCHEMA, effort: EFFORT.decompose, ...DECOMPOSE_MODEL })
    if (!d || !d.ok) { blockedSections.add(s.slug); lines.push(`${s.slug}: blocked — decomposition did not finish`); log(`${s.slug}: decomposition failed`); continue }
    for (const x of d.decided || []) decisions.push(`${s.slug}: ${x}`)
    log(`${s.slug}: decomposed, ${(d.features || []).length} features, ${(d.decided || []).length} decisions`)
  }

  let pargs = null, p = null, why = ''
  for (let t = 0; t < PLAN_TRIES && !pargs; t++) {
    p = await agent(PLAN(s, why), { phase: 'Plan', label: `plan:${s.slug}`, schema: PLAN_SCHEMA, effort: EFFORT.plan, ...MODEL })
    if (!(p && p.exitCode === 0)) break  // plan-pipeline.py's own refusal is its answer, not a copy that went wrong
    let o = null
    try { o = JSON.parse(p.argsJson) } catch (e) { why = 'it is not valid JSON'; continue }
    why = argsProblem(o, s)
    if (!why) pargs = o
  }
  if (!pargs) {
    if (p && p.exitCode === 1 && / 0 to build /.test(p.line || '')) { lines.push(`${s.slug}: already done`); continue }
    blockedSections.add(s.slug)
    lines.push(`${s.slug}: blocked — ${p && p.exitCode === 0 ? `the planner's reply was unusable after ${PLAN_TRIES} tries: ${why}` : `planning failed: ${p ? p.line : 'no result'}`}`)
    continue
  }

  built++
  let out, raw, ran = true
  // managerMode lets a builder correct a test asserting behaviour the owner revoked, and makes the
  // verifier check every test change; option C, run by a person, never gets it.
  try { raw = await workflow({ scriptPath: A.pipelineScript }, { ...pargs, managerMode: true, autonomy: AUTONOMY }) } catch (e) { ran = false; lines.push(`${s.slug}: blocked — the pipeline did not run: ${(e && e.message) || e}`) }
  // The child returns one text line per outcome. Anything else is read as no account at all, and said so: a result the manager
  // cannot read must not block its section silently (a line that is not text used to crash the run before its final record).
  out = Array.isArray(raw) && raw.every(l => typeof l === 'string') ? raw : []
  if (ran && !out.length) lines.push(`${s.slug}: blocked — the pipeline returned ${Array.isArray(raw) ? (raw.length ? 'lines that are not text' : 'no lines') : raw == null ? 'nothing' : 'a ' + typeof raw}, so what it merged is unknown: read git log on ${A.mainBranch}`)
  // The run's own lines are read by their exact shape: a feature called `barrier` writes `barrier: merged (attempt 1)`.
  const isBarrier = l => /^barrier: (green|red) after /.test(l)
  if (out.some(isBarrier)) barrierOwed = false
  // A feature line is `<name>: <result>`, so the match is anchored: barrier and triage lines carry test names and failure
  // text (`…: skipped rows`, `…: merged_totals`), and an unanchored one counted them as features (review of 3.47.0).
  const merged = out.filter(l => /^[^\s:]+: merged\b/.test(l)).length
  const unfinished = out.filter(l => /^[^\s:]+: (blocked|skipped|held|merge-failed)\b/.test(l))
  const postMergeFailed = out.find(l => /^[^\s:]+: merged\b.*\[post-merge command failed\]/.test(l))
  // The last barrier line decides: at level unblock a red barrier can be repaired and run again
  // green, and a real run stopped on the first, red line after its triage had fixed the cause.
  const red = [...out].reverse().find(isBarrier)
  const stillRed = red && red.startsWith('barrier: red') ? red : null
  const triaged = out.filter(l => /^triage: (repaired|not enough|stopped) \(cycle \d+\)/.test(l))
  if (out.length) lines.push(`${s.slug}: ${merged} merged${unfinished.length ? ', ' + unfinished.length + ' not finished (' + unfinished.map(l => l.split(':')[0]).join(', ') + ')' : ''}${stillRed ? ' — ' + stillRed : ''}`)
  for (const t of triaged) lines.push(`  ${s.slug} ${t}`)
  // what a builder stashed and a push that failed are the owner's to know; the child says them, the manager passes them on
  for (const l of out.filter(l => l.startsWith('stashed: before ') || /^[^\s:]+: merged\b.*\[push failed\]/.test(l))) lines.push(`  ${s.slug} ${l}`)
  // and a record that was not written takes its blocked features' last issues with it: the child lists them under its line
  const rec = out.findIndex(l => l.startsWith('record: not written'))
  if (rec >= 0) for (const l of [out[rec], ...out.slice(rec + 1).filter(l => l.startsWith('  '))]) lines.push(`  ${s.slug} ${l.trim()}`)
  if (!out.length || unfinished.length) blockedSections.add(s.slug)
  if (stillRed) { stopped = `the barrier is red after ${s.slug}`; break }
  // The child held what followed a failed post-merge command and ran no barrier; the next section would be built on an
  // environment out of step with the code (handover-prompt.md Step 10 says nothing runs after it).
  if (postMergeFailed) { stopped = `the post-merge command failed after ${postMergeFailed.split(':')[0]}, in ${s.slug}`; break }
}

phase('Final')
if (stopped) lines.push(`stopped: ${stopped}`)
const fin = await agent(FINAL(lines, decisions), { phase: 'Final', label: 'final', schema: FINAL_SCHEMA, effort: EFFORT.final, ...MODEL })
lines.push(`decisions made by the manager: ${decisions.length}${fin && fin.recorded ? ' — recorded in docs/roadmap-history.md' : ' — NOT recorded; they are listed in this run\'s result'}`)
if (!(fin && fin.recorded)) lines.push(...decisions)
return lines
