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

The skill itself is markdown plus one Python 3 helper script (standard library only), so it is fully
cross-platform; only the installer differs by OS. That script is used for exactly one thing —
converting a single-roadmap project into section roadmaps — and it needs a working `python3` on
PATH. On Windows the bare `python3` is usually the Microsoft Store stub, which opens the Store
instead of running anything: install Python from python.org, after which its
`py -3` launcher works too.

### Is my roadmap sound?

The skill's own sanity checks, as a command. Run it on any roadmap it generated — including one that
has grown across several waves:

```bash
python3 ~/.claude/skills/spec-driven-roadmap/scripts/check-roadmap.py
```

It checks forward dependencies, duplicate names, the eight-task budget, the two-way agreement between
each feature's open questions and the roll-up, one ledger row per theme, `uncovered: none`, the
build-order `.txt` agreeing with the roadmap, size thresholds, and name uniqueness against every
other roadmap and every `.specs/features/` directory. A failure is a question for you, not a verdict.

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
assumption is [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills), paired with its
companion skill [`not-your-babysitter`](https://github.com/tech-leads-club/agent-skills):

```bash
git init   # only if this folder has no version control yet — see note below
npx @tech-leads-club/agent-skills install --skill tlc-spec-driven -a claude-code
npx @tech-leads-club/agent-skills install --skill not-your-babysitter -a claude-code
```

> **This installer requires a git repository — but you likely already have one.** If you're running
> this inside a project you're already versioning (it has a `.git` folder, however it got there —
> `git init`, `git clone`, etc.), skip the `git init` line; the requirement is already satisfied.
> `git init` is only needed as a one-time fix for a brand-new, not-yet-versioned folder.
>
> Outside a git repository, the installer prints `✅ Successfully installed` and exits 0 while
> writing nothing to `.claude/skills/` — no error, so the gap is easy to miss. Verify with
> `ls .claude/skills/tlc-spec-driven` and `ls .claude/skills/not-your-babysitter` before moving on.
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
`ROADMAP-INDEX.md` with one roadmap per section, if you pick multi-section mode). Backlog position
lives in a `## Status` block that gets refreshed on every run.

When the run finishes, the skill hands you this prompt with the feature name and paths already
resolved — paste it into a fresh session to start feature one:

```
specify feature <name> — create it at `.specs/features/<name>/` using that exact directory name.
Spec source: docs/ROADMAP.md. Read docs/ROADMAP.md `## Cross-Cutting Decisions` before Discuss and
treat it as settled — do not re-decide what it answers.
```

That is option A, one feature at a time. Option B is a single `/loop` prompt that builds the whole
roadmap unattended. It is always offered; what it needs first is a roadmap with no open
questions, which the skill closes with you before handing the prompt over — the guide explains
what it trades away.

## How it fits with tlc-spec-driven

The two skills own different files and never collide:

- **This skill** owns `docs/` — the roadmap, the build order, the backlog status.
- **tlc-spec-driven** owns `.specs/` — specs, designs, tasks, validation reports, decisions.

The only shared surface is one write to `.specs/STATE.md`'s `## Handoff`, in that skill's own field
schema, pointing back at the roadmap. Feature completion is read from
`.specs/features/<name>/validation.md`, never tracked by hand — so the two never disagree about
what's done.
