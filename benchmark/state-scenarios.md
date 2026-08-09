# State scenarios — the fixtures that still need building

The benchmark in [`README.md`](README.md) covers the four entry paths and the loop, and every one of
them starts from **input only**: a PRD, or a codebase with no scope document. Three scenarios cannot
be reached that way, because they need a project with a *past*:

| | needs |
|---|---|
| **Re-run over an existing roadmap** | a roadmap already written, features already named, a new wave arriving |
| **Seed with work in flight** | `.specs/features/*` at mixed states, and a `## Handoff` naming one that is started and not passed |
| **Conversion over generated output** | a single-section roadmap whose names are frozen by directories on disk |

Nobody has run any of the three. This file records what a fixture for them must look like, and it is
grounded in a real project rather than imagined — which turned out to matter more than expected.

## What a real six-month project looks like

Read from one, at v3.5.0, mid-flight. **Structure only; none of its content is here or ever will be —
it is a private repository.** The shapes:

```
37 directories in .specs/features/, 9 features in the current ROADMAP.md   -> 30 orphans
4 distinct wave prefixes                                                    -> four waves
1 entry marked SUPERSEDED in the .md
3 lines of divergence between the .md and the .txt
~5,900 tokens                                                               -> nearly 2x the threshold
Handoff: feature 6 of 8, Execute, T1-T3 done, Verifier pending
```

**Thirty of thirty-seven built features are not named by the current roadmap.** That is not neglect —
it is what four waves over six months produce, and it is the single most important shape a synthetic
fixture will not reproduce, because whoever writes one keeps the roadmap and the directories in step
without thinking about it.

## The finding that paid for reading it

The reports on disk carried **six distinct title forms**:

```
# <feature> Validation          # Validation Report — <feature>
# <feature> — Validação         # Validation: <feature>
# <feature> — Verifier Report   # Validação — <feature>
```

Step 2's selection rule matched headings whose text *starts with* `Validation`. **Four of the six
fail that test**, and the Portuguese one contains no `Validation` at all. The rule had even
documented the trap — *"the word comes last"* — for one form, without noticing there were six.

The Verifier writes prose, and prose varies. A synthetic fixture would have carried one form, written
by whoever built it, six times over. Fixed in v3.16.0: the selection matches the word **anywhere** in
the heading and accepts the translated and `Verifier` spellings.

**The lesson generalises past this bug.** Anywhere the skill reads an artifact another skill wrote,
the template is a *sample*, not a spec. A fixture built from a template tests the happy path only.

## What the fixtures must carry

Build them over the existing Pauta domain in [`fixture/`](fixture/) — same PRD, same features, at
different points in time. Nothing new to invent, no second answer key, and the domain is fictional.

**Shared skeleton, per scenario:**

- `docs/ROADMAP.md` + `docs/roadmap.txt`, deliberately **not** in step — one `SUPERSEDED` entry in
  the `.md` and absent from the `.txt` is the real shape.
- `.specs/features/<name>/validation.md` for the built ones, **using at least four of the six title
  forms above**, and at least one that is a genuine FAIL and one that is PASS with no `file:line`
  citation — which the completion test must read as not done.
- Feature directories that the roadmap no longer names, in a ratio near 3:1. Anything tidier is not
  what six months looks like.
- `.specs/STATE.md` with a `## Handoff` in the eight-field schema, including a field label carrying a
  parenthetical before its colon — `**In-progress** (file:line):` — which has already broken one
  parser here.
- `git init` and one commit, done by the runner rather than stored, so the conversion script's
  `git mv` path is exercised. Its `--rollback` unstages, and that branch has never run against a
  fixture with history.

**Per scenario, on top of that:**

1. **Re-run** — two wave prefixes, the second wave's scope arriving as a new source. Expected: the
   roadmap is extended, never regenerated; existing names and their relative order unchanged; the
   user is asked extend-versus-new-section.
2. **Work in flight** — the Handoff names a feature with `spec.md` and no real PASS. Expected: the
   seed writes `## Status` and **skips Step 6**, the `**Handoff**` line records
   `not rewritten this run`, and no prompt is handed over.
3. **Conversion** — single-section, over threshold, names frozen by directories. Expected: the slug is
   *derived* from the existing prefix and never chosen; `## Status` and `## Cross-Cutting Decisions`
   move to the index; a mandatory re-seed; and with work in flight, the documented exit taken rather
   than a silent skip.

## Why this is not a separate repository

Same reason the current benchmark is not: **the answer key changes when a rule changes**, and a
fixture in another repository keeps asserting the old expectation — green and wrong. Multiple
scenarios, one repository, one answer key versioned with the rules it tests.

The private project stays untouched and unreferenced. It was read once, for shapes. It is a live
environment with work in flight, and running a seed or a conversion against it would write over real
progress — the conversion script would refuse, but that refusal is not something to verify on
somebody's production backlog.
