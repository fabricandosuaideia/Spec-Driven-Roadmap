// Exercise scripts/roadmap-pipeline.js with stubbed workflow primitives — no real agent, no quota.
//
// Maintainer tool, run by the release gate. A pipeline spends the owner's quota for hours; its
// control flow (who runs after whom, when a feature is refused, what a dependant does when its
// dependency is blocked, whether two merges can overlap) must be proved before anyone runs it,
// and a stub is the only way to prove it for free. Each scenario plants one behaviour and asserts
// the outcome; a scenario that cannot fail is not a test, so the first one is run against a
// deliberately broken copy too (see `mutants` at the bottom).
//
//   node scripts/check-pipeline.mjs            exit 0 all held, 1 a scenario failed
import fs from 'node:fs'
import path from 'node:path'
import url from 'node:url'

const HERE = path.dirname(url.fileURLToPath(import.meta.url))
const SOURCE = fs.readFileSync(path.join(HERE, 'roadmap-pipeline.js'), 'utf8')
const MANAGER = fs.readFileSync(path.join(HERE, 'manager-pipeline.js'), 'utf8')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

const BASE = {
  project: '/p', skillDir: '.claude/skills/spec-driven-roadmap', downstream: 'tlc-spec-lean',
  downstreamDir: '.claude/skills/tlc-spec-lean', statusPath: 'docs/ROADMAP.md', mainBranch: 'main',
  gate: 'make check', lanes: 1, worktreeRoot: '/p.wt', push: false,
  effort: { implement: { A: 'xhigh', B: 'high', C: 'medium' }, prove: 'medium', verify: { A: 'high', B: 'high', C: 'medium' }, review: 'high', merge: 'medium', record: 'low' },
  maxAttempts: { A: 5, B: 4, C: 3 },
}

async function run(src, argsOver, behave) {
  const calls = []
  let merging = 0, maxMerging = 0
  const agent = async (prompt, opts) => {
    const [role, name, attempt] = opts.label.split(':')
    calls.push({ role, name, attempt: Number(attempt), effort: opts.effort, model: opts.model, prompt })
    if (role === 'merge') { merging++; maxMerging = Math.max(maxMerging, merging) }
    await new Promise(r => setTimeout(r, role === 'merge' ? 15 : 3))
    if (role === 'merge') merging--
    return behave(role, name, Number(attempt), prompt)
  }
  const parallel = fns => Promise.all(fns.map(f => f().catch(() => null)))
  const fn = new AsyncFunction('args', 'agent', 'parallel', 'phase', 'log', src.replace(/^export const meta/m, 'const meta'))
  let out, error = null
  try { out = await fn({ ...BASE, ...argsOver }, agent, parallel, () => {}, () => {}) } catch (e) { error = e.message }
  return { out, error, calls, maxMerging }
}

const ok = { build: { ready: true, summary: '', blockers: [] }, prove: { ready: true, notes: '', blockers: [] },
  verify: { gateExit: 0, pass: true, notMet: [], issues: [] }, review: { issues: [] },
  merge: { ok: true, before: 'b0', commit: 'c', notes: '' }, barrier: { ok: true, exitCode: 0, failures: [] }, record: { recorded: true } }
const pass = (overrides = {}) => (role, name, attempt) => {
  const o = overrides[role] && overrides[role](name, attempt)
  return o === undefined ? ok[role] : o
}
const feat = (name, tier = 'B', dependsOn = [], lane = 1) => ({ name, roadmap: 'docs/ROADMAP.md', tier, dependsOn, lane })
const line = (out, name) => (out || []).find(l => l.startsWith(name + ':')) || ''

const scenarios = {
  'every feature passes and is merged, in dependency order': async src => {
    const r = await run(src, { features: [feat('a'), feat('b', 'B', ['a'])] }, pass())
    const merges = r.calls.filter(c => c.role === 'merge').map(c => c.name)
    return !r.error && line(r.out, 'a').includes('merged') && line(r.out, 'b').includes('merged') && merges.join() === 'a,b'
  },
  'each attempt runs builder, then a fresh prover, then the verifier': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    return r.calls.map(c => c.role).join() === 'build,prove,verify,merge,record'
  },
  'a verifier that says pass while the gate exited non-zero is refused': async src => {
    const r = await run(src, { features: [feat('a', 'C')] }, pass({ verify: () => ({ gateExit: 1, pass: true, notMet: [], issues: [] }) }))
    return line(r.out, 'a').includes('blocked') && !r.calls.some(c => c.role === 'merge')
  },
  'a refused feature is retried up to its tier ceiling, then blocked': async src => {
    const r = await run(src, { features: [feat('a', 'C')] }, pass({ verify: () => ({ gateExit: 1, pass: false, notMet: ['AC-1'], issues: [] }) }))
    return r.calls.filter(c => c.role === 'build').length === 3 && line(r.out, 'a').includes('blocked')
  },
  'attempt 3 is told to write the invariant before any code': async src => {
    const r = await run(src, { features: [feat('a')] }, pass({ verify: (n, att) => att < 3 ? { gateExit: 1, pass: false, notMet: ['x'], issues: [] } : undefined }))
    const third = r.calls.find(c => c.role === 'build' && c.attempt === 3)
    return !!third && /invariant/.test(third.prompt) && line(r.out, 'a').includes('attempt 3')
  },
  'a dependant of a blocked feature is skipped, never built': async src => {
    const r = await run(src, { features: [feat('a', 'C'), feat('b', 'B', ['a'])] }, pass({ verify: n => n === 'a' ? { gateExit: 1, pass: false, notMet: ['x'], issues: [] } : undefined }))
    return line(r.out, 'b').includes('skipped') && !r.calls.some(c => c.name === 'b')
  },
  'tier A gets an independent reviewer, and its major issue refuses the attempt': async src => {
    const r = await run(src, { features: [feat('a', 'A')] }, pass({ review: (n, att) => att === 1 ? { issues: [{ severity: 'major', where: 'x', problem: 'p', fix: 'f' }] } : undefined }))
    return r.calls.some(c => c.role === 'review') && line(r.out, 'a').includes('attempt 2')
  },
  'tier B and C get no separate reviewer': async src => {
    const r = await run(src, { features: [feat('a', 'B'), feat('b', 'C')] }, pass())
    return !r.calls.some(c => c.role === 'review')
  },
  'efforts follow the role and the tier': async src => {
    const r = await run(src, { features: [feat('a', 'A'), feat('b', 'C')] }, pass())
    const e = (role, name) => (r.calls.find(c => c.role === role && c.name === name) || {}).effort
    return e('build', 'a') === 'xhigh' && e('build', 'b') === 'medium' && e('prove', 'a') === 'medium' && e('merge', 'b') === 'medium'
  },
  'with two lanes, merges never overlap': async src => {
    const r = await run(src, { lanes: 2, features: [feat('a', 'B', [], 1), feat('b', 'B', [], 2), feat('c', 'B', [], 1), feat('d', 'B', [], 2)] }, pass())
    return r.maxMerging === 1 && r.out.every(l => l.includes('merged'))
  },
  'a cycle across lanes is refused instead of waiting forever': async src => {
    const r = await run(src, { lanes: 2, features: [feat('a', 'B', ['b'], 1), feat('b', 'B', ['a'], 2)] }, pass())
    return /cycle/.test(r.error || '')
  },
  'incomplete args are refused before any agent runs': async src => {
    const r = await run(src, { gate: '', features: [feat('a')] }, pass())
    return !!r.error && r.calls.length === 0
  },
  'the verifier reuses the receipt and is told not to re-run the full gate': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    const v = r.calls.find(c => c.role === 'verify')
    return !!v && /GATES BY RECEIPT/.test(v.prompt) && /do NOT re-run the full gate/.test(v.prompt)
  },
  'nobody is sent to open a roadmap file whole': async src => {
    const r = await run(src, { features: [feat('a', 'A')] }, pass())
    return r.calls.filter(c => c.role !== 'record').every(c => c.role === 'merge' || c.role === 'barrier' || /feature-brief\.py a /.test(c.prompt))
  },
  // 3.31.0, from the first real run: the harness relays the launch request to every agent as the
  // user's voice, and provers obeyed it instead of proving.
  'every role is told the launch request is not its task': async src => {
    const r = await run(src, { barrierGate: 'make all', features: [feat('a', 'A')] }, pass())
    const roles = new Set(r.calls.map(c => c.role))
    return ['build', 'prove', 'verify', 'review', 'merge', 'barrier', 'record'].every(x => roles.has(x)) &&
      r.calls.every(c => /LAUNCH REQUEST/.test(c.prompt) && /never run plan-pipeline\.py/.test(c.prompt))
  },
  // ...and a gate longer than one command's 10 minutes was never waited for.
  'every gate run is detached and waited for, never answered early': async src => {
    const r = await run(src, { barrierGate: 'make all', waitChunk: 60, features: [feat('a')] }, pass())
    const waits = c => /DETACHED/.test(c.prompt) && /timeout 60 tail --pid=/.test(c.prompt) && /NEVER reply while \$D\/exit does not exist/.test(c.prompt)
    return ['prove', 'merge', 'barrier', 'verify'].every(role => r.calls.filter(c => c.role === role).every(waits)) &&
      r.calls.some(c => c.role === 'barrier')
  },
  // 3.43.0: the merge may take the receipt for the gate, when it proves the exact tree.
  'by default the merger runs the gate and is told nothing about a receipt': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    return !/gate receipt may stand in/.test(r.calls.find(c => c.role === 'merge').prompt)
  },
  'with mergeGate receipt (and a barrier) the merger is told when the receipt stands in, and the prover records the base before the gate': async src => {
    const r = await run(src, { mergeGate: 'receipt', barrierGate: 'make all', waitChunk: 60, features: [feat('a')] }, pass())
    const m = r.calls.find(c => c.role === 'merge').prompt, p = r.calls.find(c => c.role === 'prove').prompt
    return /gate receipt may stand in/.test(m) && /DETACHED/.test(m) && /"base":"<output of: git merge-base main HEAD>"/.test(p)
  },
  'without a barrierGate the receipt never stands in, whatever mergeGate says': async src => {
    const r = await run(src, { mergeGate: 'receipt', features: [feat('a')] }, pass())
    return !/gate receipt may stand in/.test(r.calls.find(c => c.role === 'merge').prompt)
  },
  'a merge that skipped the gate says so in the account': async src => {
    const r = await run(src, { mergeGate: 'receipt', barrierGate: 'make all', features: [feat('a')] }, pass({ merge: () => ({ ok: true, before: 'b0', commit: 'c', notes: 'gate skipped: receipt' }) }))
    return line(r.out, 'a').includes('[gate skipped: receipt]')
  },
  // 3.41.0: a model per role.
  'models name a model per role, and a role they do not name uses the one model': async src => {
    const r = await run(src, { model: 'opus', models: { build: 'haiku', verify: 'sonnet', merge: 'sonnet' }, barrierGate: 'make all', features: [feat('a', 'A')] }, pass())
    const m = role => r.calls.filter(c => c.role === role).map(c => c.model).join()
    return m('build') === 'haiku' && m('verify') === 'sonnet' && m('merge') === 'sonnet' && m('review') === 'opus' &&
      m('prove') === 'opus' && m('barrier') === 'opus' && m('record') === 'opus'
  },
  'the triage roles take the model of the role they play': async src => {
    let n = 0
    const r = await run(src, { managerMode: true, autonomy: 'unblock', models: { triage: 'T', build: 'B', verify: 'V', merge: 'M', barrier: 'R' }, barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => (n++ === 0 ? { ok: false, exitCode: 1, failures: ['tests/test_x.py::test_y'] } : undefined),
             triage: () => ({ items: [{ test: 'tests/test_x.py::test_y', command: 'pytest x', kind: 'preexisting', evidence: '{}' }] }),
             repair: () => ({ ready: true, fixed: ['t'], blockers: [] }), check: () => ({ ok: true, issues: [] }) }))
    const m = role => [...new Set(r.calls.filter(c => c.role === role).map(c => c.model))].join()
    return m('triage') === 'T' && m('repair') === 'B' && m('check') === 'V' && m('barrier') === 'R'
  },
  'with no models the session model is inherited by every role': async src => {
    const r = await run(src, { features: [feat('a', 'A')] }, pass())
    return r.calls.every(c => c.model === undefined)
  },
  // 3.39.0: the verifier's policy and its scoped rounds.
  'with no verifier policy the verifier is told nothing about mutants': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    return !/SENSOR POLICY/.test(r.calls.find(c => c.role === 'verify').prompt)
  },
  'a verifier policy caps the mutants by tier and sets what a survivor is': async src => {
    const r = await run(src, { verifier: { sensor: { A: 5, B: 3, C: 1 }, survivor: 'minor' }, features: [feat('a', 'A'), feat('b', 'C')] }, pass())
    const va = r.calls.find(c => c.role === 'verify' && c.name === 'a').prompt, vb = r.calls.find(c => c.role === 'verify' && c.name === 'b').prompt
    return /at most 5 mutants/.test(va) && /at most 1 mutant for/.test(vb) && /surviving mutant is a minor issue/.test(va)
  },
  'whether a round is a later one depends on a report, not on the attempt number': async src => {
    const r = await run(src, { features: [feat('a', 'C')] }, pass({ build: (n, att) => att < 2 ? { ready: false, summary: '', blockers: ['x'] } : undefined, verify: (n, att) => att < 3 ? { gateExit: 1, pass: false, notMet: ['AC-1'], issues: [] } : undefined }))
    const v = n => (r.calls.find(c => c.role === 'verify' && c.attempt === n) || {}).prompt || ''
    // attempt 2 is the first verification there has ever been: it must be told to look, not told it was refused
    return /Step 1: run git log/.test(v(2)) && /If it prints NOTHING, this is a FIRST verification/.test(v(2)) && !/already refused/.test(v(2)) && /ROUND 3\./.test(v(3)) && /SCOPED to/.test(v(3))
  },
  'rounds full turns the scoping off': async src => {
    const r = await run(src, { verifier: { rounds: 'full' }, features: [feat('a', 'C')] }, pass({ verify: (n, att) => att < 2 ? { gateExit: 1, pass: false, notMet: ['AC-1'], issues: [] } : undefined }))
    return r.calls.filter(c => c.role === 'verify').every(c => !/ROUND \d/.test(c.prompt))
  },
  'a builder on a branch an earlier run refused is told to read that report or note first': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    return /an earlier run refused this feature: read that report or note first/.test(r.calls.find(c => c.role === 'build').prompt)
  },
  // 3.38.0: verify-first spends the full gate only on a feature the verifier passed.
  'verify-first runs builder, verifier, then the prover, then the merge': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a')] }, pass())
    return r.calls.map(c => c.role).join() === 'build,verify,prove,merge,record'
  },
  'verify-first never runs the gate for a feature the verifier refuses': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a', 'C')] }, pass({ verify: () => ({ gateExit: 1, pass: false, notMet: ['AC-1'], issues: [] }) }))
    return r.calls.filter(c => c.role === 'build').length === 3 && !r.calls.some(c => c.role === 'prove') && line(r.out, 'a').includes('blocked')
  },
  'verify-first: a gate that refuses a passed feature costs an attempt and is said in the account': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a', 'C')] }, pass({ prove: () => ({ ready: false, notes: '', blockers: ['tests/test_x.py::test_y red'] }) }))
    const b3 = r.calls.find(c => c.role === 'build' && c.attempt === 2)
    return r.calls.filter(c => c.role === 'build').length === 3 && !r.calls.some(c => c.role === 'merge') &&
      !!b3 && /test_y red/.test(b3.prompt) && /PASS report that the gate refused/.test(line(r.out, 'a'))
  },
  'verify-first: the verifier is told not to run the full gate and finds no receipt': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a')] }, pass())
    const v = r.calls.find(c => c.role === 'verify'), p = r.calls.find(c => c.role === 'prove')
    return !!v && /RUNS AFTER YOU/.test(v.prompt) && !/GATES BY RECEIPT/.test(v.prompt) && !!p && /an independent verifier has passed it/.test(p.prompt)
  },
  'by default the prover still comes first and the verifier reuses its receipt': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    const v = r.calls.find(c => c.role === 'verify')
    return /GATES BY RECEIPT/.test(v.prompt) && !/RUNS AFTER YOU/.test(v.prompt) && !r.calls.find(c => c.role === 'prove').prompt.includes('has passed it')
  },
  // 3.37.0: three builders ended with a job running ("waiting for the monitor"), which spends the attempt.
  'a builder is told to wait for what it starts, never to watch it and reply': async src => {
    const r = await run(src, { waitChunk: 60, features: [feat('a')] }, pass())
    const b = r.calls.find(c => c.role === 'build')
    return !!b && /LONG COMMANDS/.test(b.prompt) && /never load or arm Monitor/.test(b.prompt) &&
      /never reply ready=false because something is still running/.test(b.prompt) && /timeout 60 tail --pid=/.test(b.prompt) &&
      /timeout parameter of 80000 milliseconds/.test(b.prompt)
  },
  'with a barrierGate, the barrier runs once, after the last merge, on its own command': async src => {
    const r = await run(src, { barrierGate: 'make all', features: [feat('a'), feat('b', 'B', ['a'])] }, pass())
    const roles = r.calls.map(c => c.role)
    const b = r.calls.filter(c => c.role === 'barrier')
    return b.length === 1 && roles.lastIndexOf('merge') < roles.indexOf('barrier') && /make all/.test(b[0].prompt) &&
      (r.out || []).some(l => l.startsWith('barrier: green after a, b'))
  },
  'barrierEvery N runs it after every N merges, and once more for the rest': async src => {
    const r = await run(src, { barrierGate: 'make all', barrierEvery: 2, features: [feat('a'), feat('b'), feat('c')] }, pass())
    return r.calls.filter(c => c.role === 'barrier').length === 2
  },
  'a red barrier holds every later feature: nothing more is built or merged': async src => {
    const r = await run(src, { barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b', 'B', ['a']), feat('c', 'B', ['b'])] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['tests/test_x.py::test_y'] }) }))
    return line(r.out, 'b').includes('held') && !r.calls.some(c => c.name === 'b') && line(r.out, 'c').includes('skipped') &&
      (r.out || []).some(l => l.startsWith('barrier: red') && l.includes('test_y'))
  },
  'the record is written on the main branch and committed there': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    const rec = r.calls.find(c => c.role === 'record')
    return !!rec && /git checkout main/.test(rec.prompt) && /commit exactly docs\/ROADMAP\.md and docs\/roadmap-history\.md on main/.test(rec.prompt)
  },
  'outside manager mode no test may be edited, and nobody is told otherwise': async src => {
    const r = await run(src, { features: [feat('a', 'C')] }, pass())
    const b = r.calls.find(c => c.role === 'build'), v = r.calls.find(c => c.role === 'verify')
    return /never edit, weaken, skip, delete/.test(b.prompt) && !/REVOKED/.test(b.prompt) && !/REVOKED/.test(v.prompt)
  },
  'in manager mode a revoked assertion may be corrected, and the verifier checks every test change': async src => {
    const r = await run(src, { managerMode: true, features: [feat('a', 'C')] }, pass())
    const b = r.calls.find(c => c.role === 'build'), v = r.calls.find(c => c.role === 'verify')
    return /REVOKED-TEST <file>:<test name>/.test(b.prompt) && /fix the code, not the test/.test(b.prompt) && /same strength/.test(b.prompt) && !/never edit, weaken/.test(b.prompt) &&
      /REVOKED TESTS \(manager mode\)/.test(v.prompt) && /is a blocker issue/.test(v.prompt) &&
      /states a behaviour the OLD assertion contradicts/.test(v.prompt)
  },
  // 3.35.0 — level unblock: a red barrier is triaged by script, repaired, checked, merged, re-run.
  'at level decide a red barrier is never triaged': async src => {
    const r = await run(src, { managerMode: true, barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }) }))
    return !r.calls.some(c => ['triage', 'repair', 'check'].includes(c.role)) && line(r.out, 'b').includes('held')
  },
  'outside manager mode a red barrier is never triaged, whatever the config says': async src => {
    const r = await run(src, { autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }) }))
    return !r.calls.some(c => c.role === 'triage') && line(r.out, 'b').includes('held')
  },
  'at level unblock a red barrier is triaged, repaired, checked, merged and run again — and the run goes on': async src => {
    let n = 0
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => (n++ === 0 ? { ok: false, exitCode: 1, failures: ['tests/test_x.py::test_y'] } : undefined),
             triage: () => ({ items: [{ test: 'tests/test_x.py::test_y', command: 'pytest x', kind: 'preexisting', evidence: '{}' }] }),
             repair: () => ({ ready: true, fixed: ['t: cause, change, 10/10'], blockers: [] }), check: () => ({ ok: true, issues: [] }) }))
    const seq = r.calls.map(c => c.role).join()
    return seq.includes('barrier,triage,repair,check,merge,barrier') && line(r.out, 'b').includes('merged') &&
      (r.out || []).some(l => l.startsWith('triage: repaired (cycle 1) — preexisting: tests/test_x.py::test_y'))
  },
  'triage runs the probe from the main branch before the first merge, over every merged range': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', features: [feat('a'), feat('b')] },
      pass({ merge: n => ({ ok: true, before: 'before-' + n, commit: 'after-' + n, notes: '' }), barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }),
             triage: () => ({ items: [] }) }))
    const t = r.calls.find(c => c.role === 'triage')
    return !!t && /triage-probe\.py/.test(t.prompt) && /--base before-a /.test(t.prompt) &&
      /--merged a:before-a:after-a/.test(t.prompt) && /--merged b:before-b:after-b/.test(t.prompt)
  },
  'a failure the probe cannot reproduce stops the run as level decide would': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }),
             triage: () => ({ items: [{ test: 't', command: 'c', kind: 'not-reproduced', evidence: '{}' }] }) }))
    return !r.calls.some(c => c.role === 'repair') && line(r.out, 'b').includes('held') &&
      (r.out || []).some(l => /triage: stopped \(cycle 1\) — a failure did not reproduce/.test(l))
  },
  'a repair the checker refuses never merges': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }),
             triage: () => ({ items: [{ test: 't', command: 'c', kind: 'regression', feature: 'a', evidence: '{}' }] }),
             repair: () => ({ ready: true, fixed: ['x'], blockers: [] }),
             check: () => ({ ok: false, issues: [{ severity: 'blocker', where: 't:1', problem: 'assertion loosened', fix: 'restore it' }] }) }))
    return !r.calls.some(c => c.role === 'merge' && c.name === 'triage-1') && line(r.out, 'b').includes('held')
  },
  'at most two triage cycles, then the run stops': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }),
             triage: () => ({ items: [{ test: 't', command: 'c', kind: 'preexisting', evidence: '{}' }] }),
             repair: () => ({ ready: true, fixed: ['x'], blockers: [] }), check: () => ({ ok: true, issues: [] }) }))
    return r.calls.filter(c => c.role === 'triage').length === 2 && line(r.out, 'b').includes('held')
  },
  'the repairer may never loosen a test, and the checker refuses one that does': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }),
             triage: () => ({ items: [{ test: 't', command: 'c', kind: 'preexisting', evidence: '{}' }] }),
             repair: () => ({ ready: true, fixed: ['x'], blockers: [] }), check: () => ({ ok: true, issues: [] }) }))
    const rp = r.calls.find(c => c.role === 'repair'), ck = r.calls.find(c => c.role === 'check')
    return /Never raise a timeout, never loosen, narrow or delete an assertion/.test(rp.prompt) && /Do not edit the test/.test(rp.prompt) &&
      /Refuse \(ok=false\) any change that raises a timeout, loosens, narrows or deletes an assertion/.test(ck.prompt) && /10 times in a row/.test(ck.prompt)
  },
  // 3.36.0, from a real run (Sales-ai): a feature unfinished in one run keeps its worktree, and the next
  // run's lane for it is another one; its builder used the old tree, its merger looked in the new lane.
  'a feature that already has a worktree is built, proved, verified and merged there, whatever its lane': async src => {
    const r = await run(src, { lanes: 2, worktreeRoot: '/p.wt', features: [{ ...feat('a', 'B', [], 1), worktree: '/p.wt/lane2/a' }, feat('b', 'B', [], 1)] }, pass())
    const of = (role, n) => r.calls.filter(c => c.role === role && c.name === n)
    return ['build', 'prove', 'verify', 'merge'].every(role => of(role, 'a').length && of(role, 'a').every(c => c.prompt.includes('/p.wt/lane2/a') && !c.prompt.includes('/p.wt/lane1/a'))) &&
      of('merge', 'b').every(c => c.prompt.includes('/p.wt/lane1/b'))
  },
  // 3.36.0: a barrier a run never finished is owed by the next one, before any feature.
  'a barrier owed by an earlier run runs first, from the commit proved last, and again records itself when green': async src => {
    const r = await run(src, { barrierGate: 'make all', barrierPending: { base: 'base0', head: 'head0' }, features: [feat('a')] }, pass())
    const roles = r.calls.map(c => c.role).join()
    const b = r.calls.find(c => c.role === 'barrier')
    return roles.startsWith('barrier,build') && /earlier run/.test(b.prompt) && /record-barrier\.py --root \/p --sha <that commit>/.test(b.prompt) && !/--barrier-green/.test(b.prompt) && /status --porcelain/.test(b.prompt) &&
      (r.out || []).some(l => l.startsWith('barrier: green after earlier-run'))
  },
  'every barrier is told to record the commit it ran on, only when it exits 0': async src => {
    const r = await run(src, { barrierGate: 'make all', features: [feat('a')] }, pass())
    const b = r.calls.find(c => c.role === 'barrier')
    return /git -C \/p rev-parse main/.test(b.prompt) && /record-barrier\.py --root \/p --sha <that commit>/.test(b.prompt) && /only if the barrier exited 0/.test(b.prompt)
  },
  'a red barrier owed by an earlier run holds every feature': async src => {
    const r = await run(src, { barrierGate: 'make all', barrierPending: { base: 'base0', head: 'head0' }, features: [feat('a'), feat('b', 'B', ['a'])] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }) }))
    return !r.calls.some(c => c.role === 'build') && line(r.out, 'a').includes('held') && line(r.out, 'b').includes('skipped')
  },
  'with nothing to build, an owed barrier still runs': async src => {
    const r = await run(src, { barrierGate: 'make all', barrierPending: { base: 'base0', head: 'head0' }, features: [] }, pass())
    return r.calls.map(c => c.role).join() === 'barrier,record'
  },
  'a barrier owed by an earlier run is triaged from the commit proved last': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierPending: { base: 'base0', head: 'head0' }, features: [] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }), triage: () => ({ items: [] }) }))
    const t = r.calls.find(c => c.role === 'triage')
    return !!t && /--base base0 /.test(t.prompt) && /--merged earlier-run:base0:head0/.test(t.prompt)
  },
  'no barrier is owed unless the args say so': async src => {
    const r = await run(src, { barrierGate: 'make all', features: [feat('a')] }, pass())
    return r.calls.filter(c => c.role === 'barrier').length === 1 && r.calls.map(c => c.role).join().startsWith('build')
  },
  // 3.36.0, from a real run: the repair added comment lines, the test moved from :157 to :161, and the
  // checker's command, a file:line selector, found no test; ten of ten "failures" refused a correct repair.
  'triage commands select a test by name, never by file:line': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }), triage: () => ({ items: [] }) }))
    const t = r.calls.find(c => c.role === 'triage')
    return /NAME or id/.test(t.prompt) && /never a file:line/.test(t.prompt) && /--grep/.test(t.prompt) && /-t /.test(t.prompt) && /::/.test(t.prompt)
  },
  'a checker whose command finds no test derives one from the name, and never reads "no tests" as a bad repair': async src => {
    const r = await run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')] },
      pass({ barrier: () => ({ ok: false, exitCode: 1, failures: ['t'] }),
             triage: () => ({ items: [{ test: 't', command: 'c', kind: 'preexisting', evidence: '{}' }] }),
             repair: () => ({ ready: true, fixed: ['x'], blockers: [] }), check: () => ({ ok: true, issues: [] }) }))
    const ck = r.calls.find(c => c.role === 'check'), rp = r.calls.find(c => c.role === 'repair')
    return /No tests found/.test(ck.prompt) && /never evidence/.test(ck.prompt) && /from its NAME/.test(ck.prompt) && /selects exactly that test/.test(ck.prompt) &&
      /never a file:line/.test(rp.prompt) && /keeps the test's name/.test(rp.prompt) &&
      /list or collect-only mode/.test(ck.prompt) && /rename or a move counts as a deletion/.test(ck.prompt) && /reply ok=false with a major issue/.test(ck.prompt)
  },
  'a model set in the config reaches every agent': async src => {
    const r = await run(src, { model: 'sonnet', barrierGate: 'x', features: [feat('a', 'A')] }, pass())
    const none = await run(src, { features: [feat('a')] }, pass())
    return r.calls.every(c => c.model === 'sonnet') && none.calls.every(c => c.model === undefined)
  },
}

// Deliberately broken copies: each must make at least one scenario fail.
const mutants = {
  'gate exit ignored': ['ver.pass && ver.gateExit === 0 &&', 'ver.pass &&'],
  'no merge lock': ['const m = await withMergeLock(doMerge)', 'const m = await doMerge()'],
  'reviewer ignored': ["(tier !== 'A' || (rev && serious(rev.issues).length === 0))", 'true'],
  'dependants not skipped': ['if (bad) {', 'if (false) {'],
  'red barrier ignored': ['if (!green) barrierRed = merged', 'if (false) barrierRed = merged'],
  'launch request not scoped': ['never ask.\n${LAUNCHED}', 'never ask.'],
  'gate not waited for': ['tail --pid=<that PID>', 'cat <that PID>'],
  'receipt merge ignored': ["const BY_RECEIPT = A.mergeGate === 'receipt'", 'const BY_RECEIPT = false'],
  'receipt records the base after the gate instead of the commit the tree was built on': ['git merge-base ${MAIN} HEAD>"', 'git rev-parse ${MAIN}>"'],
  'receipt without a barrier still stands in': ["A.mergeGate === 'receipt' && !!A.barrierGate", "A.mergeGate === 'receipt'"],
  'a skipped gate is not shown': ["${o.gateSkipped ? ' [gate skipped: receipt]' : ''}", ''],
  'models ignored': ["const modelFor = role => (A.models && A.models[role]) ? { model: A.models[role] } : MODEL", 'const modelFor = role => MODEL'],
  'the repairer not given the builder model': ["label: `repair:${cycle}`, schema: REPAIR_SCHEMA, effort: effortFor('implement', { tier: 'A' }), ...modelFor('build')", "label: `repair:${cycle}`, schema: REPAIR_SCHEMA, effort: effortFor('implement', { tier: 'A' }), ...MODEL"],
  'rounds full ignored': ["VP.rounds === 'full' ? '' : `ROUND", "false ? '' : `ROUND"],
  'verifier policy dropped': ['${ROUND(f, attempt)}${SENSOR_POLICY(f)}', '${ROUND(f, attempt)}'],
  'a round is decided by the attempt counter again': ['`ROUND ${attempt}. Step 1: run git log', '`ROUND ${attempt}. a verifier already refused this feature; run git log'],
  'builder not sent to an earlier refusal': ['an earlier run refused this feature: read that report or note first', 'the feature is new'],
  'verify-first ignored': ["const VERIFY_FIRST = A.gateOrder === 'verify-first'", 'const VERIFY_FIRST = false'],
  'verify-first gate result ignored': ['if (pass && VERIFY_FIRST) { pass = await proveStep(); gateRefused = !pass }', 'if (pass && VERIFY_FIRST) { await proveStep() }'],
  'verify-first runs the gate before the verdict anyway': ['if (!VERIFY_FIRST && !(await proveStep())) continue', 'if (!(await proveStep())) continue'],
  'builder not told to wait for a long command': ['${LONG_COMMANDS}\n${A.checklist ?', '${A.checklist ?'],
  'verifier not told to check test changes in manager mode': ["${MANAGED ? REVOKED_CHECK(f) + '\\n' : ''}", ''],
  'verifier not told the criterion must contradict the old assertion': ['states a behaviour the OLD assertion contradicts', 'exists'],
  'barrier only at the end': ['if (BARRIER_EVERY && sinceBarrier.length >= BARRIER_EVERY) await runBarrier()', ''],
  'unblock outside manager mode': ["const UNBLOCK = MANAGED && A.autonomy === 'unblock'", "const UNBLOCK = A.autonomy === 'unblock'"],
  'repair merged without the checker': ["if (!ck || !ck.ok || serious(ck.issues).length) return stop(", "if (false) return stop("],
  'triage cycles unbounded': ['for (let cycle = 1; cycle <= 2; cycle++) {', 'for (let cycle = 1; cycle <= 5; cycle++) {'],
  'an existing worktree ignored': ['const wt = f => LANES > 1 ? (f.worktree ||', 'const wt = f => LANES > 1 ? (false ||'],
  'an owed barrier seeds nothing': ['sinceBarrier = [EARLIER]', 'sinceBarrier = []'],
  'an owed barrier has no base for the triage': ['mergedAt[EARLIER] = {', "mergedAt['x'] = {"],
  'an owed barrier ignored without the guard': ['if (A.barrierGate && A.barrierPending && A.barrierPending.base) {', 'if (false) {'],
  'an owed barrier never run': ['await withMergeLock(runBarrier)\n\nawait parallel', 'await parallel'],
  'the barrier does not record itself': ['record-barrier.py --root ${P} --sha <that commit>', 'true'],
  'the barrier runs on a dirty tree': ['if \\`git -C ${P} status --porcelain\\`', 'if \\`git -C ${P} status --short\\`'],
  'checker told nothing about a command that finds no test': ['No tests found', 'Something else'],
  'triage allowed a line selector': ['never a file:line', 'any selector'],
  'a not-reproduced failure repaired anyway': ["if (items.some(i => i.kind === 'not-reproduced')) return stop(", "if (false) return stop("],
}

// ---- 3.43.1: clause by clause. A phrase of a prompt that no scenario reads can be deleted and nothing notices
// (a review deleted 28 of them and no scenario failed). Each clause below is asserted in the prompt of its role,
// and a mutant replaces the same text in the source by a neutral word, so the failure is the assertion's and not a
// syntax error. The text must occur once in the source: otherwise deleting the first copy proves nothing.
const refusedOnce = { verify: (n, att) => att < 2 ? { gateExit: 1, pass: false, notMet: ['AC-1'], issues: [] } : undefined }
const unblockRun = (src, over) => {
  let n = 0
  return run(src, { managerMode: true, autonomy: 'unblock', barrierGate: 'make all', barrierEvery: 1, features: [feat('a'), feat('b')], ...over },
    pass({ barrier: () => (n++ === 0 ? { ok: false, exitCode: 1, failures: ['t::x'] } : undefined),
           triage: () => ({ items: [{ test: 't::x', command: 'pytest x', kind: 'preexisting', evidence: '{}' }] }),
           repair: () => ({ ready: true, fixed: ['t'], blockers: [] }), check: () => ({ ok: true, issues: [] }) }))
}
const MERGE_ARGS = { mergeGate: 'receipt', barrierGate: 'make all' }
const CLAUSES = [
  ['merge: the receipt may stand in', 'merge', 'The gate receipt may stand in for the gate below', { args: MERGE_ARGS }],
  ['merge: the gate must be pass', 'merge', 'its gate is "pass"', { args: MERGE_ARGS }],
  ['merge: the receipt\'s command must be the pipeline\'s gate', 'merge', 'its command is the same command as the gate named in this step, not a lighter one', { args: MERGE_ARGS }],
  ['merge: the base must exist and equal main', 'merge', 'it has a base, and the base equals the output of', { args: MERGE_ARGS }],
  ['merge: the tree must be clean and the hash equal', 'merge', 'prints nothing; and its codeHash equals the hash this command prints', { args: MERGE_ARGS }],
  ['merge: all must hold, then skip', 'merge', 'If they all hold, do NOT run the gate', { args: MERGE_ARGS }],
  ['merge: the skip is written down', 'merge', 'write "gate skipped: receipt" in notes', { args: MERGE_ARGS }],
  ['merge: otherwise the receipt proves nothing', 'merge', 'or the file is missing or has no base, the receipt proves nothing', { args: MERGE_ARGS }],
  ['prove: the base is the commit the tree was built on', 'prove', 'which is what makes the receipt honest', {}],
  ['prove: verify-first does not verify again', 'prove', 'do not verify again', { args: { gateOrder: 'verify-first' } }],
  ['prove: verify-first leaves a note for the next builder', 'prove', 'gate-failure.md (the failing tests and the command', { args: { gateOrder: 'verify-first' } }],
  ['build: an earlier gate-failure note is read', 'build', 'or a gate-failure.md note) is committed', {}],
  ['verify: no report means verify everything and ignore the scope', 'verify', 'this is a FIRST verification: ignore the rest of this paragraph and verify everything', {}],
  ['verify: a first verification demotes nothing', 'verify', 'a clause of a criterion that no test exercises is not proven', {}],
  ['verify: inside the scope and in a first verification nothing is demoted', 'verify', 'Inside the scope, and in a first verification, nothing is demoted', { round2: true }],
  ['verify: a rebase brings main into scope', 'verify', 'what main gained in that rebase is new code too', { round2: true }],
  ['verify: other rows carry forward and say so', 'verify', 'Every other row carries forward and says so', { round2: true }],
  ['verify: proofs re-run in full', 'verify', 'The proofs re-run in full at HEAD', { round2: true }],
  ['verify: a killed mutant on untouched code carries forward', 'verify', 'a previous mutant that was killed', { round2: true }],
  ['verify: scope never lowers a severity', 'verify', 'Scope limits what you re-run, never what you may refuse', { round2: true }],
  ['verify: only an out-of-scope non-defect weakness is minor', 'verify', 'only a weakness that lies OUTSIDE the scope and is not a defect', { round2: true }],
  ['verify: a survivor graded minor does not refuse', 'verify', 'list it in the report, it does not refuse the feature', { args: { verifier: { survivor: 'minor' } } }],
  ['verify (manager): what a test file is', 'verify', 'test sources, fixtures, conftest, test configuration and the gate script', { args: { managerMode: true } }],
  ['verify (manager): decided before the branch', 'verify', 'it was decided BEFORE this branch', { args: { managerMode: true } }],
  ['verify (manager): not a decision when the branch wrote it', 'verify', 'it is not a decision', { args: { managerMode: true } }],
  ['verify (manager): the branch wrote it itself', 'verify', 'one the branch wrote itself', { args: { managerMode: true } }],
  ['verify (manager): a criterion written to explain the edit', 'verify', 'states nothing the product needed, is the same blocker', { args: { managerMode: true } }],
  ['build (manager): the criterion is decided before the build', 'build', 'decided before you started — never from a spec, plan or check that you wrote on this branch', { args: { managerMode: true } }],
  ['build (manager): the first line of the commit', 'build', 'whose FIRST LINE is REVOKED-TEST', { args: { managerMode: true } }],
  ['build (manager): red for another reason is the builder\'s defect', 'build', 'A test red for any other reason is a defect in your change', { args: { managerMode: true } }],
  ['repair: only the narrow exception, and a timing fix at its cause', 'repair', 'never raise a timeout, never add a retry. A test that is wrong about timing', { unblock: true }],
  ['repair: the correction carries the first line', 'repair', 'lets that assertion be corrected, in a commit of its own whose first line is REVOKED-TEST', { unblock: true }],
  ['repair: waits for what it starts', 'repair', 'LONG COMMANDS', { unblock: true }],
]
async function clauseRun(src, [, role, , o]) {
  if (o.unblock) return unblockRun(src, o.args || {})
  return run(src, { ...(o.args || {}), features: [feat('a', o.tier || 'B')] }, pass(o.round2 ? refusedOnce : {}))
}
const clauseMutants = {}
for (const c of CLAUSES) {
  const [name, role, text, o] = c
  scenarios['clause present — ' + name] = async src => {
    const r = await clauseRun(src, c)
    const call = r.calls.filter(x => x.role === role && (!o.round2 || x.attempt === 2)).pop()
    return !!call && call.prompt.includes(text)
  }
  if (role === 'repair') continue  // shares its text with the builder's: deleted below at the one site that matters
  if (SOURCE.split(text).length !== 2) { scenarios['clause text occurs once — ' + name] = async () => false; continue }
  clauseMutants['clause deleted — ' + name] = [text, 'XXXX']
}
clauseMutants['repair loses LONG_COMMANDS'] = ['${LONG_COMMANDS}\n${REPAIR_TESTS}', '${REPAIR_TESTS}']
clauseMutants['repair gets the wide rule again'] = ['${LONG_COMMANDS}\n${REPAIR_TESTS}', '${LONG_COMMANDS}\n${REVOKED_RULE}']
Object.assign(mutants, clauseMutants)

// ---- 3.44.0: the command that applies what merged code needs outside git (a database migration) ----
const PM = { postMerge: 'bash docs/process/migrate.sh' }
const okMerge = (postMerge) => ({ merge: () => ({ ok: true, before: 'b0', commit: 'c', notes: '', ...(postMerge === undefined ? {} : { postMerge }) }) })
Object.assign(scenarios, {
  'without postMerge the merger is told nothing about a post-merge command': async src => {
    const r = await run(src, { features: [feat('a')] }, pass())
    return !/post-merge/.test(r.calls.find(c => c.role === 'merge').prompt)
  },
  'with postMerge the merger runs it once after the fast-forward, detached, and never undoes the merge': async src => {
    const r = await run(src, { ...PM, features: [feat('a')] }, pass(okMerge(true)))
    const m = r.calls.find(c => c.role === 'merge').prompt
    const at = k => m.indexOf(k)
    return /bash docs\/process\/migrate\.sh/.test(m) && at('3b. Then, once') > at('3. Fast-forward') && at('3b. Then, once') < at('4. ') && /DETACHED/.test(m.slice(at('3b.'))) &&
      /post-merge command can take longer/.test(m) && /the merge STAYS: never undo the fast-forward/.test(m)
  },
  'a post-merge command that exited 0 changes nothing': async src => {
    const r = await run(src, { ...PM, features: [feat('a'), feat('b', 'B', ['a'])] }, pass(okMerge(true)))
    return line(r.out, 'a').includes('merged') && !line(r.out, 'a').includes('post-merge') && line(r.out, 'b').includes('merged')
  },
  'a post-merge command that failed leaves the feature merged, says so, and holds what follows': async src => {
    const r = await run(src, { ...PM, features: [feat('a'), feat('b', 'B', ['a']), feat('c', 'B', ['b'])] }, pass(okMerge(false)))
    return line(r.out, 'a').includes('merged') && line(r.out, 'a').includes('[post-merge command failed]') && !r.calls.some(c => c.name === 'b' && c.role === 'build') &&
      /held|skipped/.test(line(r.out, 'b')) && r.calls.filter(c => c.role === 'merge').length === 1
  },
  'a merger that does not answer postMerge is read as a failure': async src => {
    const r = await run(src, { ...PM, features: [feat('a'), feat('b')] }, pass(okMerge(undefined)))
    return line(r.out, 'a').includes('[post-merge command failed]') && line(r.out, 'b').includes('held') && line(r.out, 'b').includes('post-merge command failed after a')
  },
  'no barrier runs while the environment is out of step': async src => {
    const r = await run(src, { ...PM, barrierGate: 'make all', barrierEvery: 1, features: [feat('a')] }, pass(okMerge(false)))
    return !r.calls.some(c => c.role === 'barrier')
  },
  'the post-merge reply is asked for': async src => {
    const r = await run(src, { ...PM, features: [feat('a')] }, pass(okMerge(true)))
    return /and postMerge \(true only if the post-merge command exited 0\)/.test(r.calls.find(c => c.role === 'merge').prompt)
  },
})
Object.assign(mutants, {
  'a failed post-merge command is ignored': ["const postFailed = !!A.postMerge && m.postMerge !== true", "const postFailed = false"],
  'only an explicit false counts as a failure': ["!!A.postMerge && m.postMerge !== true", "!!A.postMerge && m.postMerge === false"],
  'features after a failed post-merge command are not held': ["if (barrierRed || postMergeFailed) { hold(f); return }", "if (barrierRed) { hold(f); return }"],
  'the merger is not told the merge stays': ['the merge STAYS: never undo the fast-forward', 'the merge is undone'],
  'the post-merge command is missing from the merger\'s prompt': ["${POST_MERGE}4. ", "4. "],
  'a barrier runs while the environment is out of step': ["|| postMergeFailed) return  // main is not in step", ") return  // main is not in step"],
})

Object.assign(scenarios, {
  'verify-first, tier A, two lanes: builder, then verifier and reviewer together, then the prover, then the merge': async src => {
    const r = await run(src, { gateOrder: 'verify-first', lanes: 2, features: [feat('a', 'A', [], 1), feat('b', 'A', [], 2)] }, pass())
    const seq = n => r.calls.filter(c => c.name === n).map(c => c.role)
    const ok = n => { const q = seq(n); return q[0] === 'build' && q.indexOf('prove') > q.indexOf('verify') && q.indexOf('prove') > q.indexOf('review') && q[q.length - 1] === 'merge' }
    return ok('a') && ok('b')
  },
  'a reviewer\'s refusal in verify-first keeps the gate from running': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a', 'A')] },
      pass({ review: () => ({ issues: [{ severity: 'major', where: 'x:1', problem: 'p', fix: 'f' }] }) }))
    return !r.calls.some(c => c.role === 'prove') && line(r.out, 'a').includes('blocked')
  },
  'the note about a PASS report the gate refused disappears once a later verification refuses': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a', 'C')] },
      pass({ prove: (n, att) => att === 1 ? { ready: false, notes: '', blockers: ['red'] } : undefined,
             verify: (n, att) => att >= 2 ? { gateExit: 1, pass: false, notMet: ['AC-1'], issues: [] } : undefined }))
    return line(r.out, 'a').includes('blocked') && !/PASS report/.test(line(r.out, 'a'))
  },
  'a gate that refuses a passed feature on the last attempt says so': async src => {
    const r = await run(src, { gateOrder: 'verify-first', features: [feat('a', 'C')] }, pass({ prove: () => ({ ready: false, notes: '', blockers: ['red'] }) }))
    return /PASS report that the gate refused/.test(line(r.out, 'a'))
  },
  'every role takes its own model, the triage roles included': async src => {
    const models = { build: 'MB', prove: 'MP', verify: 'MV', review: 'MR', merge: 'MM', record: 'MC', barrier: 'MX', triage: 'MT' }
    const r = await unblockRun(src, { models, features: [feat('a', 'A'), feat('b', 'A')] })
    const m = role => [...new Set(r.calls.filter(c => c.role === role).map(c => c.model))].join()
    return m('build') === 'MB' && m('prove') === 'MP' && m('verify') === 'MV' && m('review') === 'MR' && m('merge') === 'MM' &&
      m('record') === 'MC' && m('barrier') === 'MX' && m('triage') === 'MT' && m('repair') === 'MB' && m('check') === 'MV'
  },
})
// one mutant per agent() call site: the call keeps its role but loses its model
const siteMutants = {}
for (const [labelPart, role] of [['label: `prove:', 'prove'], ['label: `review:', 'review'], ['label: `merge:${f.name}`', 'merge'], ['label: \'record\'', 'record'],
                                  ['label: `merge:triage-', 'merge'], ['label: `build:', 'build'], ['label: `verify:', 'verify'], ['label: `triage:', 'triage'], ['label: `barrier:${merged', 'barrier']]) {
  const ln = SOURCE.split('\n').find(l => l.includes(labelPart) && l.includes(`...modelFor('${role}')`))
  if (ln) siteMutants['the model of the ' + role + ' call at ' + labelPart] = [ln, ln.replace(`...modelFor('${role}')`, '...MODEL')]
  else { scenarios['call site found — ' + labelPart] = async () => false }
}
Object.assign(mutants, siteMutants)

// ---- manager mode: manager-pipeline.js, with stubbed agents and a stubbed child pipeline ----
const MBASE = {
  project: '/p', skillDir: '/s', downstream: 'tlc-spec-lean', downstreamDir: '/d', statusPath: 'docs/ROADMAP-INDEX.md',
  mainBranch: 'main', pipelineScript: '/s/scripts/roadmap-pipeline.js', delegation: 'decide everything; I review later',
  delegatedOn: '2026-09-29', stopAt: [], sectionsPerRun: 4, effort: { decompose: 'xhigh', plan: 'low', final: 'medium' },
}
const sec = (slug, over = {}) => ({ slug, roadmap: `docs/ROADMAP-${slug}.md`, txt: `docs/roadmap-${slug}.txt`, dependsOn: [], decomposed: false, pending: [], ...over })
async function runManager(src, argsOver, child = () => ['x: merged (attempt 1)', 'barrier: green after x'], behave = {}) {
  const calls = [], children = []
  const agent = async (prompt, opts) => {
    const [role, slug] = opts.label.split(':')
    calls.push({ role, slug, prompt, model: opts.model, effort: opts.effort })
    if (behave[role]) { const r = behave[role](slug); if (r !== undefined) return r }
    if (role === 'decompose') return { ok: true, features: [slug + '-a'], decided: ['q? → a'] }
    if (role === 'plan') return { exitCode: 0, line: 'ok', argsJson: JSON.stringify({ features: [{ name: slug + '-a' }], roadmap: `docs/ROADMAP-${slug}.md` }) }
    if (role === 'final') return { recorded: true, summary: 's' }
  }
  const workflow = async (ref, a) => { const slug = a.roadmap.match(/ROADMAP-(.+)\.md/)[1]; children.push({ ref, slug, managerMode: a.managerMode, autonomy: a.autonomy }); return child(slug) }
  const fn = new AsyncFunction('args', 'agent', 'parallel', 'phase', 'log', 'workflow', src.replace(/^export const meta/m, 'const meta'))
  let out, error = null
  try { out = await fn({ ...MBASE, ...argsOver }, agent, fns => Promise.all(fns.map(f => f())), () => {}, () => {}, workflow) } catch (e) { error = e.message }
  return { out: out || [], error, calls, children }
}

const managerScenarios = {
  'manager: a section not yet decomposed is decomposed, planned, then built by the pipeline, in order': async src => {
    const r = await runManager(src, { sections: [sec('a'), sec('b', { decomposed: true, pending: ['b-a'] })] })
    const roles = r.calls.map(c => c.role + ':' + (c.slug || '')).join()
    return roles === 'decompose:a,plan:a,plan:b,final:' && r.children.map(c => c.slug).join() === 'a,b' &&
      r.children.every(c => c.ref.scriptPath === '/s/scripts/roadmap-pipeline.js')
  },
  'manager: every child pipeline runs in manager mode': async src => {
    const r = await runManager(src, { sections: [sec('a'), sec('b', { decomposed: true, pending: ['b-a'] })] })
    return r.children.length === 2 && r.children.every(c => c.managerMode === true)
  },
  'manager: the autonomy level reaches every child, decide by default': async src => {
    const d = await runManager(src, { sections: [sec('a')] })
    const u = await runManager(src, { autonomy: 'unblock', sections: [sec('a')] })
    return d.children[0].autonomy === 'decide' && u.children[0].autonomy === 'unblock'
  },
  'manager: at level unblock a doubtful section is classified, then built; at level decide it waits': async src => {
    const sections = [sec('a', { decomposed: true, pending: ['a-x'], doubtful: { 'a-x': 'has a validation.md the gate refuses' } })]
    const u = await runManager(src, { autonomy: 'unblock', sections }, undefined, { classify: () => ({ ok: true, decided: ['a-x → done, Decided by the manager: report PASS'] }) })
    const d = await runManager(src, { sections })
    const cl = u.calls.find(c => c.role === 'classify')
    return !!cl && /When in doubt, build/.test(cl.prompt) && /Never edit a report/.test(cl.prompt) && u.children.length === 1 &&
      u.out.some(l => /decisions made by the manager: 1/.test(l)) && !d.calls.some(c => c.role === 'classify') && d.children.length === 0
  },
  'manager: a finished section costs nothing': async src => {
    const r = await runManager(src, { sections: [sec('a', { decomposed: true, pending: [] }), sec('b')] })
    return !r.calls.some(c => c.slug === 'a') && r.out.some(l => l === 'a: already done')
  },
  // 3.36.0: a run paused inside its barrier left the main branch unproved, and the next run called the
  // section "already done" and built the following one on top of it.
  'manager: a finished section is not called done while a barrier is owed; the pipeline runs it': async src => {
    const owed = await runManager(src, { barrierPending: { base: 'b0', head: 'h0' }, sections: [sec('a', { decomposed: true, pending: [] }), sec('b', { decomposed: true, pending: [] })] })
    const none = await runManager(src, { sections: [sec('a', { decomposed: true, pending: [] })] })
    return owed.children.length === 1 && owed.children[0].slug === 'a' && owed.out.some(l => l === 'b: already done') && none.children.length === 0
  },
  'manager: it stops before a section the owner reserved (stopAt)': async src => {
    const r = await runManager(src, { stopAt: ['b'], sections: [sec('a'), sec('b'), sec('c')] })
    return r.children.map(c => c.slug).join() === 'a' && r.out.some(l => /stopped: b needs the owner/.test(l))
  },
  'manager: a section depending on one that did not finish is skipped; an independent one still runs': async src => {
    const r = await runManager(src, { sections: [sec('a'), sec('b', { dependsOn: ['a'] }), sec('c')] },
      slug => slug === 'a' ? ['a-a: blocked'] : ['x: merged (attempt 1)'])
    return !r.children.some(c => c.slug === 'b') && r.children.some(c => c.slug === 'c') && r.out.some(l => /^b: skipped/.test(l))
  },
  'manager: a section with a feature the gate cannot decide is not built, nor anything depending on it': async src => {
    const r = await runManager(src, { sections: [sec('a', { decomposed: true, pending: ['a-x'], doubtful: { 'a-x': 'has a validation.md the gate refuses' } }),
      sec('b', { dependsOn: ['a'] }), sec('c')] })
    return !r.calls.some(c => c.slug === 'a' || c.slug === 'b') && r.children.map(c => c.slug).join() === 'c' &&
      r.out.some(l => /^a: needs the owner — the gate cannot decide a-x/.test(l)) && r.out.some(l => /^b: skipped/.test(l))
  },
  // The exact child output of a real level-unblock run (3.35.0): red, repaired, green.
  'manager: a barrier the child repaired and ran again green does not stop the run': async src => {
    const r = await runManager(src, { autonomy: 'unblock', sections: [sec('a'), sec('b')] }, slug => slug === 'a'
      ? ['a-x: merged (attempt 1)', 'barrier: red after a-x — tests.test_tags...: returned [b, a]',
         'triage: repaired (cycle 1) — preexisting: tests.test_tags...', 'barrier: green after a-x']
      : ['b-x: merged (attempt 1)', 'barrier: green after b-x'])
    return r.children.map(c => c.slug).join() === 'a,b' && !r.out.some(l => /stopped/.test(l)) &&
      r.out.some(l => /a triage: repaired \(cycle 1\)/.test(l))
  },
  'manager: a red barrier stops the run': async src => {
    const r = await runManager(src, { sections: [sec('a'), sec('b')] }, slug => ['a-a: merged (attempt 1)', 'barrier: red after a-a — t'])
    return r.children.length === 1 && r.out.some(l => /stopped: the barrier is red after a/.test(l))
  },
  'manager: it builds at most sectionsPerRun sections, then says to launch again': async src => {
    const r = await runManager(src, { sectionsPerRun: 2, sections: [sec('a'), sec('b'), sec('c')] })
    return r.children.length === 2 && r.out.some(l => /sectionsPerRun \(2\) reached/.test(l))
  },
  'manager: a failed plan blocks the section and never builds it': async src => {
    const r = await runManager(src, { sections: [sec('a', { decomposed: true, pending: ['a-a'] })] }, undefined,
      { plan: () => ({ exitCode: 1, line: 'docs/ROADMAP-a.md: a is in the build order but has no entry', argsJson: '' }) })
    return r.children.length === 0 && r.out.some(l => /a: blocked — planning failed/.test(l))
  },
  'manager: every agent carries the launch scoping, and the decomposer the delegation and the marking': async src => {
    const r = await runManager(src, { sections: [sec('a')] })
    const d = r.calls.find(c => c.role === 'decompose')
    return r.calls.every(c => /LAUNCH REQUEST/.test(c.prompt)) && /decide everything; I review later/.test(d.prompt) &&
      /Decided by the manager/.test(d.prompt) && /Never leave a question open/.test(d.prompt)
  },
  'manager: no agent is told never to run the command its own role runs': async src => {
    const r = await runManager(src, { sections: [sec('a')] })
    const plan = r.calls.find(c => c.role === 'plan')
    return !!plan && /run python3 \/s\/scripts\/plan-pipeline\.py/.test(plan.prompt) && !/never run plan-pipeline\.py/.test(plan.prompt)
  },
  'manager: every decision reaches the final record': async src => {
    const r = await runManager(src, { sections: [sec('a'), sec('b')] })
    const f = r.calls.find(c => c.role === 'final')
    return !!f && /a: q\? → a/.test(f.prompt) && /b: q\? → a/.test(f.prompt) && r.out.some(l => /decisions made by the manager: 2/.test(l))
  },
  'manager: without the owner\'s delegation nothing runs': async src => {
    const r = await runManager(src, { delegation: '  ', sections: [sec('a')] })
    return !!r.error && r.calls.length === 0
  },
  'manager: the decomposer can run on its own model': async src => {
    const r = await runManager(src, { model: 'sonnet', decomposeModel: 'opus', sections: [sec('a')] })
    return r.calls.find(c => c.role === 'decompose').model === 'opus' && r.calls.filter(c => c.role !== 'decompose').every(c => c.model === 'sonnet')
  },
}
const managerMutants = {
  'dependants of an unfinished section not skipped': ['if (bad) { blockedSections.add', 'if (false) { blockedSections.add'],
  'a finished section called done with a barrier owed': ['if (s.decomposed && !(s.pending || []).length && !barrierOwed) {', 'if (s.decomposed && !(s.pending || []).length) {'],
  'stopAt ignored': ['if (STOP_AT.has(s.slug))', 'if (false)'],
  'red barrier ignored': ["if (stillRed) { stopped = `the barrier is red after ${s.slug}`; break }", ''],
  'decisions not marked': ['**Decided by the manager', '**Decided'],
  'the first barrier line decides': ["const red = [...out].reverse().find(l => l.startsWith('barrier: '))", "const red = out.find(l => l.startsWith('barrier: '))"],
  'doubtful features built anyway': ['if (doubt.length) {', 'if (false) {'],
  'child pipelines not told they run in manager mode': ['{ ...pargs, managerMode: true, autonomy: AUTONOMY }', 'pargs'],
  'doubtful features classified at level decide': ["if (doubt.length && AUTONOMY === 'unblock') {", "if (doubt.length) {"],
}

let failed = 0
for (const [name, test] of Object.entries(managerScenarios)) {
  let held
  try { held = await test(MANAGER) } catch (e) { held = false }
  console.log((held ? '  ok   ' : '  FAIL ') + name)
  if (!held) failed++
}
for (const [name, [from, to]] of Object.entries(managerMutants)) {
  if (!MANAGER.includes(from)) { console.log('  FAIL manager mutant anchor missing: ' + name); failed++; continue }
  const broken = MANAGER.replace(from, to)
  let caught = false
  for (const test of Object.values(managerScenarios)) {
    let held
    try { held = await test(broken) } catch (e) { held = false }
    if (!held) { caught = true; break }
  }
  console.log((caught ? '  ok   ' : '  FAIL ') + 'manager mutant caught: ' + name)
  if (!caught) failed++
}
for (const [name, test] of Object.entries(scenarios)) {
  let held
  try { held = await test(SOURCE) } catch (e) { held = false }
  console.log((held ? '  ok   ' : '  FAIL ') + name)
  if (!held) failed++
}
for (const [name, [from, to]] of Object.entries(mutants)) {
  if (!SOURCE.includes(from)) { console.log('  FAIL mutant anchor missing: ' + name); failed++; continue }
  const broken = SOURCE.replace(from, to)
  // every scenario builds its own state and waits only on timers, so they run side by side: a mutant is caught
  // when ANY scenario fails on it, and the order in which they finish does not matter
  const held = await Promise.all(Object.values(scenarios).map(test => Promise.resolve().then(() => test(broken)).catch(() => false)))
  const caught = held.some(h => !h)
  console.log((caught ? '  ok   ' : '  FAIL ') + 'mutant caught: ' + name)
  if (!caught) failed++
}
console.log(`\n${failed} failed`)
process.exit(failed ? 1 : 0)
