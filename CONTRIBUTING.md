# Contributing

Setting up to work on the skill, and the two things about this repository that a clone does not tell
you.

**The operating rules are in [`CLAUDE.md`](CLAUDE.md), not here.** What to run and when, what is
never edited by hand, what is never changed without saying so — that file, and this one does not
repeat any of it. A second copy of a rule is a second thing to keep in sync, which is the failure
this repository has committed more than any other.

---

## What a fresh clone is missing

Three directories are gitignored on purpose, and one of them matters immediately:

```
.claude/       vendored skills — NOT in the clone
.reference/    third-party material read while designing — not in the clone
.agents/       local skill-install bookkeeping — not in the clone
```

**`.claude/skills/tlc-spec-driven` is the one that breaks things.** `references/handoff-seed.md`
requires reading that skill's real field schema, exit codes and `validation.md` template **from
disk** — explicitly never from memory, because they change between its versions. Without it an agent
follows the "no downstream skill installed" branch, skips the whole seed, and writes nothing under
`.specs/`. That is a real run this repository has on record.

So install it, into the repository, before doing anything else:

```bash
npx @tech-leads-club/agent-skills install --skill tlc-spec-driven -a claude-code
npx @tech-leads-club/agent-skills install --skill not-your-babysitter -a claude-code
```

Both land under `.claude/skills/` and stay ignored. They are here to be **read**, not shipped: the
installers copy `SKILL.md`, `references/` and the runtime `scripts/`, and nothing else.

> That installer needs a git repository, and silently writes nothing outside one while still printing
> success. Verify with `ls .claude/skills/tlc-spec-driven` before moving on.

## Turn the hook on

```bash
bash scripts/hooks/install.sh
```

One `git config` for this clone, pointing at the tracked `scripts/hooks/`. `pre-commit` then runs
`check-consistency.py` whenever a commit touches `SKILL.md`, `references/`, `scripts/`, `guide/`, the
READMEs, `CLAUDE.md`, the installers or the plugin manifests — and stays out of the way otherwise.

It exists because the release gate was too rare a point. `bump-version.sh` already refuses to cut a
release on a failing check, but between two releases somebody can commit twenty times with nothing
looking at the invariants — and a fact edited in one file and left stale in another is a per-commit
failure, not a per-release one.

`git commit --no-verify` bypasses it. That is fair on a work-in-progress branch and not on `main`,
where the release gate will catch it later anyway — louder, and further from the change that caused
it.

## Requirements

`python3` for the scripts, `bash` for the installer, `git`. No package to install, no virtualenv, no
build. The scripts are standard library only, which is deliberate — a benchmark that needs a
dependency is a benchmark that stops running.

`pwsh` if you intend to touch `install.ps1`. **It has never been executed in this project's history**
— three static reviews, zero runs, because no Windows machine was available. If you have one, that is
the single most valuable hour anyone can spend here.

## Layout

| | |
|---|---|
| `SKILL.md` | the map, and the 13 non-negotiable rules |
| `references/` | the procedures — this is the skill; `SKILL.md` is a map to it |
| `scripts/` | two shipped to users (`convert-to-multi.py`, `check-roadmap.py`), the rest maintainer-only ([`CLAUDE.md`](CLAUDE.md) lists which) |
| `benchmark/` | frozen fixture, answer key, scoreboard — see [`benchmark/README.md`](benchmark/README.md) |
| `guide/` | the human guide, in three languages, kept at structural parity |
| `install.sh` / `install.ps1` | must stay behaviourally identical; a check enforces the payload |

**Where the skill actually lives.** `references/` holds the procedures an agent executes. `SKILL.md`
says outright that when the two disagree, **the reference wins** — so a change made only in
`SKILL.md` changes nothing.

## Testing a change

[`benchmark/README.md`](benchmark/README.md), in full, before the first run. The short version:

```bash
python3 scripts/run-benchmark.py setup 0a-single
#   ... a fresh agent executes the skill in the printed path ...
python3 scripts/run-benchmark.py score <path> --record
```

The part that decides whether a result means anything is **how the agent is launched** — fresh, not
told what changed, following the text literally, treating friction as the output. Those four rules
are in that README and they are not stylistic.

## The three languages

`guide/HOW-IT-WORKS.md` and the READMEs exist in English, Portuguese and Spanish at **exact
structural parity**: same headings in the same order, same code spans, same table rows.
`check-consistency.py` measures it, so a change to one is a change to three.

Paths, field names, trigger phrases and code-block contents are **never translated** — they are keys
the skill locates by exact name, and translating one breaks the handoff.

`CLAUDE.md` is the deliberate exception: English only, no variants. It instructs an agent rather than
being read as documentation, and its first paragraph tells that agent to answer in whatever language
the person is writing in.

## Releasing

`bash scripts/bump-version.sh <version>` writes the three declarations and runs the consistency check
as a gate. Write the `CHANGELOG.md` entry first — the gate checks it exists for the version being cut.

Then a tag: `git tag -a v<version>` and push it. From 3.5.0 onward every release has one; earlier
ones are not tagged retroactively, and `CHANGELOG.md` explains why.

## Two things worth knowing before you propose one

**A written procedure cannot be run against a test case.** Four rules in this repository became
scripts for that reason, and one of them was rejected three rounds running as prose before it was
correct as code. If what you are adding has an order of operations, a rollback path, or a derived
value, consider writing it as a check rather than a paragraph.

**The scoreboard is the argument.** `benchmark/RESULTS.md` records what each version captured out of
the seven planted ambiguities. A change that drops that number is a regression regardless of how good
the reasoning is, and a change that raises it needs no advocacy.
