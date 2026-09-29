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
  merge: { ok: true, commit: 'c', notes: '' }, barrier: { ok: true, exitCode: 0, failures: [] }, record: { recorded: true } }
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
  'barrier only at the end': ['if (BARRIER_EVERY && sinceBarrier.length >= BARRIER_EVERY) await runBarrier()', ''],
}

let failed = 0
for (const [name, test] of Object.entries(scenarios)) {
  let held
  try { held = await test(SOURCE) } catch (e) { held = false }
  console.log((held ? '  ok   ' : '  FAIL ') + name)
  if (!held) failed++
}
for (const [name, [from, to]] of Object.entries(mutants)) {
  if (!SOURCE.includes(from)) { console.log('  FAIL mutant anchor missing: ' + name); failed++; continue }
  const broken = SOURCE.replace(from, to)
  let caught = false
  for (const test of Object.values(scenarios)) {
    let held
    try { held = await test(broken) } catch (e) { held = false }
    if (!held) { caught = true; break }
  }
  console.log((caught ? '  ok   ' : '  FAIL ') + 'mutant caught: ' + name)
  if (!caught) failed++
}
console.log(`\n${failed} failed`)
process.exit(failed ? 1 : 0)
