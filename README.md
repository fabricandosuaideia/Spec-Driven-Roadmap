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

Works on every OS Claude Code runs on, and gives you `/plugin update`:

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

The skill itself is plain markdown and is fully cross-platform; only the installer differs by OS.

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

Then hand off to the build cycle:

```
specify feature <name> — spec source: docs/ROADMAP.md
```

## How it fits with tlc-spec-driven

The two skills own different files and never collide:

- **This skill** owns `docs/` — the roadmap, the build order, the backlog status.
- **tlc-spec-driven** owns `.specs/` — specs, designs, tasks, validation reports, decisions.

The only shared surface is one write to `.specs/STATE.md`'s `## Handoff`, in that skill's own field
schema, pointing back at the roadmap. Feature completion is read from
`.specs/features/<name>/validation.md`, never tracked by hand — so the two never disagree about
what's done.
