# Spec-Driven-Roadmap

🌐 **Available in:** [English](README.md) · [Português](README.pt-BR.md) · [Español](README.es.md)

Roadmap and Product Plan Creator compatible with the TLC Spec-Driven Framework.

A Claude Code skill that decides **what to build and in what order**, then hands off. It turns a
system's scope — an existing document, an interview when you don't have one, or an existing codebase
— into a dependency-ordered feature backlog, and seeds the downstream spec-driven skill so it can
start building feature one.

It is a **prequel** to the build cycle. It never writes specs, designs, tasks, or code.

📖 **New here? Read the how-it-works guide first:**
[English](guide/HOW-IT-WORKS.md) · [Português](guide/HOW-IT-WORKS.pt-BR.md) · [Español](guide/HOW-IT-WORKS.es.md)

## Install

### As a plugin (recommended)

Works on every OS Claude Code runs on, and it is the **only install path with updating built in** —
the plain-skill path below has no self-update, so upgrading there means re-running the installer.
Install once, then `/plugin update` keeps it current:

```
/plugin marketplace add fabricandosuaideia/Spec-Driven-Roadmap
/plugin install spec-driven-roadmap@fabricandosuaideia
```

### As a plain skill

```bash
curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
```

Installs into `.claude/skills/spec-driven-roadmap/` in the current project.

With flags — note the `-s --`, which is required when piping into bash:

```bash
curl -fsSL .../install.sh | bash -s -- --global   # install to ~/.claude/skills/
curl -fsSL .../install.sh | bash -s -- --force    # overwrite an existing install
```

### Windows

`install.sh` needs bash, so it works in Git Bash and WSL. For native PowerShell (5.1+, ships with
Windows 10 and later) use `install.ps1` instead — it needs no curl, tar, bash or WSL:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 | iex
```

The piped form cannot take parameters. For `-Global` or `-Force`, download it first:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 -OutFile install.ps1
.\install.ps1 -Global -Force
```

The skill itself is markdown plus eight Python 3 helper scripts (standard library only), so it is
fully cross-platform; only the installer differs by OS. They convert a single-roadmap project into
section roadmaps, check a roadmap, measure what agent runs cost, print one feature's slice of the
roadmap for its builder, keep the roadmap's status block small, write the sub-agent definitions a loop
dispatches, plan a pipeline run, and time your project's full gate; each needs a working `python3` on PATH. In Claude Code the skill
also ships a Workflow script that builds a roadmap with a fresh agent per role — builder, prover,
verifier, reviewer, merger — and it runs only when you ask for it. On Windows the bare `python3` is usually the Microsoft Store stub, which opens the Store
instead of running anything: install Python from python.org, after which its
`py -3` launcher works too.

### Is my roadmap sound?

Ask — *"check my roadmap"* — and the skill runs its own sanity checks over what it generated,
including a roadmap that has grown across several waves. It reports what failed, what it warns about,
and what it could not judge; nothing is edited.

It covers forward dependencies, duplicate names, the eight-task budget, the two-way agreement between
each feature's open questions and the roll-up, one ledger row per theme, `uncovered: none`, every
feature's risk tier at or above its floor, the build-order `.txt` agreeing with the roadmap, size thresholds, and name uniqueness against every other
roadmap and every `.specs/features/` directory — including a built feature no roadmap names any more.
A failure is a question for you, not a verdict.

Phase 2 runs the same checks whenever it closes a roadmap, so this is for asking later.

### Where did my quota go?

Ask — *"measure my agent cost"* — and the skill reads this project's own Claude Code transcripts and
shows where the tokens went: by role, by retry, and how much of each conversation is context piling
up turn after turn. It edits nothing and runs nothing else. Save a baseline before you change how
agents run, and compare after: a saving nobody measured is a guess.

### Which version do I have?

The version lives in the `metadata.version` field of the skill's own `SKILL.md` frontmatter.

If you installed **the plugin**, the answer is `/plugin update` — the one install path that updates
itself.

If you installed **the plain skill** (`install.sh` or `install.ps1`), compare your copy against the
one published on `main`:

```bash
gh_version=$(curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/SKILL.md | sed -n 's/^ *version: *//p' | head -1 | tr -d '"')
printf 'installed: %s\ngithub:    %s\n' \
  "$(for f in .claude/skills/spec-driven-roadmap/SKILL.md ~/.claude/skills/spec-driven-roadmap/SKILL.md; do [ -f "$f" ] && { sed -n 's/^ *version: *//p' "$f" | head -1 | tr -d '"'; break; }; done || echo 'not installed')" \
  "${gh_version:-unreachable}"
```

It prints two lines — for example, a copy left behind on an older release:

```
installed: 3.1.0
github:    3.5.0
```

Those numbers are illustrative. What tells you anything is the comparison between the two lines, not
the values themselves.

The command checks the **project** install first and falls back to the **global** one — the same
precedence Claude Code applies when both exist — and prints `not installed` on the first line when
it finds neither. A second line reading `unreachable` means the download failed rather than that
you are current — check the network and run it again. On Windows, run it from Git Bash or WSL. When
the two lines differ, re-run the installer with `--force` (`-Force` for `install.ps1`).

A project install lives in `.claude/skills/spec-driven-roadmap/` and a global one in
`~/.claude/skills/`; the two can sit at different versions at the same time, and the version that
counts is always the copy Claude Code loaded.

[`CHANGELOG.md`](CHANGELOG.md) is the record of what changed in each version.

## Prerequisite

The roadmap hands off to a downstream spec-driven skill, which does the actual building. Default
assumption is [`tlc-spec-lean`](https://github.com/tech-leads-club/agent-skills), the Tech Leads
Club's current spec-driven skill; [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills)
is also fully supported, and a project already using it keeps using it. Two companions are worth
installing beside it: [`tlc-discover`](https://github.com/tech-leads-club/agent-skills), which takes
over the interview when you have no scope document yet, and
[`not-your-babysitter`](https://github.com/tech-leads-club/agent-skills):

```bash
git init   # only if this folder has no version control yet — see note below
npx @tech-leads-club/agent-skills install --skill tlc-spec-lean -a claude-code
npx @tech-leads-club/agent-skills install --skill tlc-discover -a claude-code
npx @tech-leads-club/agent-skills install --skill not-your-babysitter -a claude-code
```

> **This installer requires a git repository — but you likely already have one.** If you're running
> this inside a project you're already versioning (it has a `.git` folder, however it got there —
> `git init`, `git clone`, etc.), skip the `git init` line; the requirement is already satisfied.
> `git init` is only needed as a one-time fix for a brand-new, not-yet-versioned folder.
>
> Outside a git repository, the installer prints `✅ Successfully installed` and exits 0 while
> writing nothing to `.claude/skills/` — no error, so the gap is easy to miss. Verify with
> `ls .claude/skills/tlc-spec-lean` and `ls .claude/skills/tlc-discover` before moving on.
> (The two installers above have no such requirement — they work in any directory, git or not.)

Without a downstream skill installed, the roadmap is still generated — only the handoff step is
skipped, and it tells you so.

## Use

Three entry points, depending on what you already have:

| You have | Say | It produces |
|---|---|---|
| A PRD, architecture doc, ADRs, flowchart export | `generate a roadmap from docs/PRD.md` | the roadmap directly |
| Nothing, and no clear idea yet | `plan product` / `I don't know what to build yet` | `docs/PROJECT.md` via interview, then the roadmap |
| An existing codebase, no scope doc | `map this codebase into a roadmap source` | `docs/CODEBASE-SUMMARY.md`, then the roadmap |

Output lands in `docs/` — a `ROADMAP.md` plus a machine-readable `roadmap.txt` build order (or a
`ROADMAP-INDEX.md` with one roadmap per section, if you pick multi-section mode). Every feature carries
a risk tier — A, B or C, derived from its size and what it touches — that sets how much verification
and how many attempts it gets. Backlog position lives in a `## Status` block the skill rewrites on
every seed and keeps small: whatever earlier runs wrote into it moves, verbatim, to
`docs/roadmap-history.md`. The handoff it writes into `.specs/STATE.md` is kept small the same way —
the old one, and any old copies runs left beside it, go to that same file.

When the run finishes, the skill asks how you want to build and hands you a prompt with the names and
paths already resolved. Paste it into a fresh session.

- **A — one feature at a time.** With `tlc-spec-lean` it reads:

  ```
  specify feature <name> — create it at `.specs/features/<name>/` using that exact directory name.
  Plan source: run `python3 .claude/skills/spec-driven-roadmap/scripts/feature-brief.py <name>` — it prints the
  entry from docs/ROADMAP.md, its risk tier and what that tier sets (follow it), the questions naming it and docs/ROADMAP.md `## Cross-Cutting Decisions`,
  which are settled before planning: do not re-decide what they answer. Do not open docs/ROADMAP.md whole;
  if the script cannot run, read only its `### <name>` entry and the lines naming <name>.
  ```

  The builder reads only its feature's slice of the roadmap, never the whole file: every turn of an
  agent re-reads what it has already read.
- **B — one `/loop` over one roadmap**, unattended. The loop's own session only coordinates: each
  feature is built by a fresh sub-agent and verified by another, and the skill writes
  `.claude/agents/roadmap-*.md` so each role runs at its own effort. Every open question in that
  roadmap is closed with you first, because nobody is there to answer later.
- **C — a pipeline run, Claude Code only.** A Workflow script the skill ships builds the roadmap with a
  fresh agent per role — builder, a prover that runs your gate once, the verifier, a reviewer for
  risk tier A, a merger, and your batch barrier (`barrierGate`) if you keep the whole suite for one —
  and returns one line per feature. You confirm the gate commands once; a gate longer than one
  command's 10 minutes is run detached and waited for; `bench-gate.py` can time it for you.

The [guide](guide/HOW-IT-WORKS.md) explains what each option trades away.

**Manager mode — the whole backlog, unattended.** In a multi-section project, in Claude Code, you can
ask for *"manager mode"*: a Workflow walks every section still to do, in build order, decomposes each
one just before building it — **deciding the open questions itself and marking every decision
`Decided by the manager`** for you to review — and builds it with option C's pipeline. It runs only
on your written delegation (`manager.delegation` in `docs/process/pipeline.json`), stops before the
sections you reserve (`stopAt`), on a red barrier, and never builds on a section that did not finish.
Outside manager mode the skill never decides for you.

## Upgrading a project that already uses the skill

New projects need nothing here. A project an earlier version planned gets the new behaviour in one
run:

1. Install the new version in that project — re-run the installer, or `/plugin update` for a plugin.
2. In that project, ask *"upgrade this project"* (or type `/spec-driven-roadmap upgrade this project`).

The skill then saves a cost baseline from the project's own transcripts
(`docs/process/cost-baseline.json`), lints the roadmap, re-runs its seed — which moves the old
`## Status` and the old handoff, copies included, into `docs/roadmap-history.md` — offers to replace old bridge lines
in your `CLAUDE.md` (only on your yes), and asks how you want to build. It never regenerates the
roadmap or renames a feature. You can ask Claude Code for both steps in one sentence: *"reinstall
spec-driven-roadmap in this project, then upgrade this project"*. Once a few features are built, ask
*"measure my agent cost"* again: the comparison with that baseline is the only proof the upgrade saved
anything.

Two things to know. Sub-agent types in `.claude/agents/` load when a session starts in the project,
so start a new session after option B writes them. And a `CLAUDE_CODE_EFFORT_LEVEL` set in your
environment overrides the effort each of them sets.

## Working on the skill itself

[`CONTRIBUTING.md`](CONTRIBUTING.md) — environment setup, and the two directories a clone does not
get. [`CLAUDE.md`](CLAUDE.md) — the operating rules an agent follows here. [`benchmark/`](benchmark/)
— a frozen fixture with seven planted ambiguities, an answer key, and a scoreboard per version.

## How it fits with the TLC skills

The two own different files and never collide:

- **This skill** owns `docs/` — the roadmaps, the build order, the backlog status, its history
  (`docs/roadmap-history.md`) and the pipeline's config (`docs/process/pipeline.json`, option C). With
  option B and sub-agents it also writes `.claude/agents/roadmap-*.md`.
- **The downstream skill** — `tlc-spec-lean` by default, `tlc-spec-driven` also supported — owns
  `.specs/`: plans or specs, checks or tasks, verification reports, decisions.

The only write into `.specs/` is `.specs/STATE.md`'s `## Handoff`, in that skill's own field schema,
pointing back at the roadmap. Feature completion is read from each feature's report
(`verification.md` for `tlc-spec-lean`, `validation.md` for `tlc-spec-driven`) and that skill's own
completion gate, never tracked by hand — so the two never disagree about what's done.
