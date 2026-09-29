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
//   mainBranch, pipelineScript, model?, decomposeModel?, delegation, delegatedOn, stopAt[],
//   sectionsPerRun, effort: { decompose, plan, final },
//   sections: [{ slug, roadmap, txt, dependsOn[], decomposed, pending[], doubtful{} }] }   (build order)
// `doubtful` lists features the downstream gate cannot decide (a report it refuses, or a pending
// feature a finished one depends on). They are the owner's to classify in pipeline.json's
// `featureStatus`; until then the section is not built, and neither is anything depending on it.

const A = args || {}
const P = A.project
const SKILL = A.skillDir
const SECTIONS = A.sections || []
const STOP_AT = new Set(A.stopAt || [])
const PER_RUN = Math.max(1, A.sectionsPerRun || 4)
const EFFORT = A.effort || {}
if (!P || !SKILL || !A.downstream || !A.pipelineScript || !(A.delegation || '').trim()) {
  throw new Error('args incomplete, or no delegation: run plan-pipeline.py --manager and pass its output as args')
}
const MODEL = A.model ? { model: A.model } : {}
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

const PLAN = s => `You are the PLANNER of section \`${s.slug}\` in the project at ${P}.
${LAUNCHED}
ROLE: on ${A.mainBranch}, run python3 ${SKILL}/scripts/plan-pipeline.py --root ${P} --roadmap ${s.roadmap} with its stdout to a temporary file and its stderr to another, and keep its exit code. Change nothing.
Reply exitCode, line (the one line it printed to stderr, verbatim) and argsJson (the whole stdout, verbatim — it is JSON; empty when the exit code is not 0).`

const FINAL = (lines, decisions) => `You are the FINAL agent of a manager run in the project at ${P}.
${LAUNCHED}
1. Run the spec-driven-roadmap seed: ${SKILL}/references/handoff-seed.md, Steps 1-7, entering by its third trigger. This is manager mode: at Step 7 stop — Step 8's question has nobody to answer it.
2. Write the account below to a temporary file outside the project, then run: python3 ${SKILL}/scripts/status-block.py ${A.statusPath} --last-run "<one line: manager run — sections built, blocked, stopped, and why it stopped>" --note <that file>. Delete the file.
3. On ${A.mainBranch}, commit what steps 1 and 2 wrote, message "docs: manager run".
Reply recorded (true only when that commit exists) and summary (one line).
THE ACCOUNT — the run's lines, then every decision the manager made, for the owner to review:
${JSON.stringify({ lines, decisions }, null, 1)}`

const DECOMPOSE_SCHEMA = { type: 'object', properties: { ok: { type: 'boolean' }, features: { type: 'array', items: { type: 'string' } }, decided: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'features', 'decided'] }
const PLAN_SCHEMA = { type: 'object', properties: { exitCode: { type: 'number' }, line: { type: 'string' }, argsJson: { type: 'string' } }, required: ['exitCode', 'line', 'argsJson'] }
const FINAL_SCHEMA = { type: 'object', properties: { recorded: { type: 'boolean' }, summary: { type: 'string' } }, required: ['recorded', 'summary'] }

const lines = []
const decisions = []
const blockedSections = new Set()
let built = 0
let stopped = null

for (const s of SECTIONS) {
  if (STOP_AT.has(s.slug)) { stopped = `${s.slug} needs the owner (stopAt)`; break }
  if (s.decomposed && !(s.pending || []).length) { lines.push(`${s.slug}: already done`); continue }
  const bad = (s.dependsOn || []).find(d => blockedSections.has(d))
  if (bad) { blockedSections.add(s.slug); lines.push(`${s.slug}: skipped — depends on ${bad}, which did not finish`); log(`${s.slug}: skipped`); continue }
  const doubt = Object.keys(s.doubtful || {})
  if (doubt.length) { blockedSections.add(s.slug); lines.push(`${s.slug}: needs the owner — the gate cannot decide ${doubt.join(', ')}; classify each in featureStatus`); log(`${s.slug}: needs the owner`); continue }
  if (built >= PER_RUN) { stopped = `sectionsPerRun (${PER_RUN}) reached — launch again to continue`; break }

  if (!s.decomposed) {
    const d = await agent(DECOMPOSE(s), { phase: 'Decompose', label: `decompose:${s.slug}`, schema: DECOMPOSE_SCHEMA, effort: EFFORT.decompose, ...DECOMPOSE_MODEL })
    if (!d || !d.ok) { blockedSections.add(s.slug); lines.push(`${s.slug}: blocked — decomposition did not finish`); log(`${s.slug}: decomposition failed`); continue }
    for (const x of d.decided || []) decisions.push(`${s.slug}: ${x}`)
    log(`${s.slug}: decomposed, ${(d.features || []).length} features, ${(d.decided || []).length} decisions`)
  }

  const p = await agent(PLAN(s), { phase: 'Plan', label: `plan:${s.slug}`, schema: PLAN_SCHEMA, effort: EFFORT.plan, ...MODEL })
  let pargs = null
  if (p && p.exitCode === 0) { try { pargs = JSON.parse(p.argsJson) } catch (e) { pargs = null } }
  if (!pargs) {
    if (p && p.exitCode === 1 && / 0 to build /.test(p.line || '')) { lines.push(`${s.slug}: already done`); continue }
    blockedSections.add(s.slug)
    lines.push(`${s.slug}: blocked — planning failed: ${p ? p.line : 'no result'}`)
    continue
  }

  built++
  let out
  try { out = await workflow({ scriptPath: A.pipelineScript }, pargs) } catch (e) { out = null; lines.push(`${s.slug}: blocked — the pipeline did not run: ${e.message}`) }
  out = Array.isArray(out) ? out : []
  const merged = out.filter(l => /: merged/.test(l)).length
  const unfinished = out.filter(l => /: (blocked|skipped|held|merge-failed)/.test(l))
  const red = out.find(l => l.startsWith('barrier: red'))
  if (out.length) lines.push(`${s.slug}: ${merged} merged${unfinished.length ? ', ' + unfinished.length + ' not finished (' + unfinished.map(l => l.split(':')[0]).join(', ') + ')' : ''}${red ? ' — ' + red : ''}`)
  if (!out.length || unfinished.length) blockedSections.add(s.slug)
  if (red) { stopped = `the barrier is red after ${s.slug}`; break }
}

phase('Final')
if (stopped) lines.push(`stopped: ${stopped}`)
const fin = await agent(FINAL(lines, decisions), { phase: 'Final', label: 'final', schema: FINAL_SCHEMA, effort: EFFORT.final, ...MODEL })
lines.push(`decisions made by the manager: ${decisions.length}${fin && fin.recorded ? ' — recorded in docs/roadmap-history.md' : ' — NOT recorded; they are listed in this run\'s result'}`)
if (!(fin && fin.recorded)) lines.push(...decisions)
return lines
