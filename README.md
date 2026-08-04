# Spec-Driven-Roadmap

Roadmap and Product Plan Creator compatible with the TLC Spec-Driven Framework.

A Claude Code skill that turns a system's scope — an existing document, an interview when you don't
have one yet, or a scan of an existing codebase — into a dependency-ordered features backlog for a
spec-driven workflow (default: `tlc-spec-driven`) to build, one feature at a time.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
```

Installs into `.claude/skills/spec-driven-roadmap/` in the current project. Add `--global` to
install into `~/.claude/skills/spec-driven-roadmap/` instead.

## What's in v3.0.0

- **Interview Mode** — no document yet and not sure what to build? The skill interviews you
  (one question at a time) and produces `docs/PROJECT.md` as the roadmap source, no separate tool
  needed.
- **Brownfield Mode** — existing codebase, no scope doc? The skill reuses whatever the downstream
  spec-driven skill (or `codenavi`) already knows about the code, or does a light scan of its own,
  and produces `docs/CODEBASE-SUMMARY.md` as the roadmap source.
- Both fall straight through into the same Phase 0/1/2/Handoff pipeline as a hand-provided PRD or
  architecture doc — see [SKILL.md](SKILL.md).
