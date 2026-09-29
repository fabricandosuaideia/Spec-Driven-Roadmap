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
  const workflow = async (ref, a) => { const slug = a.roadmap.match(/ROADMAP-(.+)\.md/)[1]; children.push({ ref, slug }); return child(slug) }
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
  'manager: a finished section costs nothing': async src => {
    const r = await runManager(src, { sections: [sec('a', { decomposed: true, pending: [] }), sec('b')] })
    return !r.calls.some(c => c.slug === 'a') && r.out.some(l => l === 'a: already done')
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
  'stopAt ignored': ['if (STOP_AT.has(s.slug))', 'if (false)'],
  'red barrier ignored': ["if (red) { stopped = `the barrier is red after ${s.slug}`; break }", ''],
  'decisions not marked': ['**Decided by the manager', '**Decided'],
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
