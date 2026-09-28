#!/usr/bin/env python3
"""Write the sub-agent definitions a roadmap loop dispatches, into the project.

Why this exists: a loop that coordinates — each feature built by a fresh builder
and checked by a fresh verifier — spends the user's quota in those sub-agents,
and how much depends on two settings the prompt text cannot carry. Claude Code
reads a sub-agent's model and reasoning effort from the frontmatter of
`.claude/agents/<name>.md` ("Effort level when this subagent is active. Overrides
the session effort level", code.claude.com/docs/en/sub-agents); there is no
per-call effort. So the loop names an agent type, and this writes the types.

Three definitions, each carrying the context budget in its own body so no
dispatching prompt has to repeat it:

  roadmap-builder-a   effort xhigh   a risk-tier A feature (where rework concentrated)
  roadmap-builder     effort high    tiers B and C — the effort the measured
                                     multi-agent build actually ran its builders at
  roadmap-verifier    effort high    tlc-spec-lean: "mid-to-high for the Verifier
                                     ... never the cheapest tier"

`model: inherit` everywhere: a cheaper model is the user's call, not this
script's. Those efforts are a starting point carried from one project, not a
measured optimum — measure-agents.py shows what they cost.

Never overwrites a file that differs from what it would write: an edited agent is
the user's. A file identical to the template is left alone.

    python3 write-agents.py --root <project-root>          # write what is missing
    python3 write-agents.py --root <project-root> --check  # report, write nothing
    python3 write-agents.py --selftest

Exit codes: 0 written or already current, 1 a differing file was left alone (or
--selftest failed), 2 usage.
"""

import argparse
import os
import shutil
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass

BUDGET = """Keep your context small: every turn you take re-reads all of it.
- Read the part of a file you need (offset and limit); grep for a symbol instead of reading a directory.
- Send long command output to a file and read back only the lines that matter; never paste a whole test log or diff.
- While you work, run only the tests related to what you touched; leave full gates to the skill's own cadence.
- Never re-read a file you already read unless it changed since.
- After two failed attempts at the same thing, write in one sentence the invariant the failures share before changing code."""

BUILDER_BODY = """You build ONE feature of this project's roadmap, exactly as the prompt that dispatched you says, and nothing else.

{budget}

Do not write the verification report: a separate verifier does. Reply with one line — the feature, its last commit, and anything you refused to do.
"""

VERIFIER_BODY = """You verify ONE feature you did not build, exactly as the prompt that dispatched you and the downstream skill's own verify or validate reference say. You write the report; you change no code.

{budget}

Reply with one line — the feature, the verdict you wrote, and the report's path.
"""

AGENTS = {
    "roadmap-builder-a": ("Builds one risk-tier A roadmap feature when a spec-driven-roadmap loop prompt dispatches it by name. Not for general use.",
                          "xhigh", BUILDER_BODY),
    "roadmap-builder": ("Builds one risk-tier B or C roadmap feature when a spec-driven-roadmap loop prompt dispatches it by name. Not for general use.",
                        "high", BUILDER_BODY),
    "roadmap-verifier": ("Verifies one roadmap feature it did not build, when a spec-driven-roadmap loop prompt dispatches it by name. Not for general use.",
                         "high", VERIFIER_BODY),
}


def render(name):
    desc, effort, body = AGENTS[name]
    return ("---\nname: %s\ndescription: %s\nmodel: inherit\neffort: %s\n---\n\n%s"
            % (name, desc, effort, body.format(budget=BUDGET)))


def plan(root):
    """[(name, path, state)] with state in {missing, current, differs}."""
    out = []
    for name in AGENTS:
        path = os.path.join(root, ".claude", "agents", name + ".md")
        if not os.path.exists(path):
            state = "missing"
        else:
            with open(path, encoding="utf-8") as fh:
                state = "current" if fh.read() == render(name) else "differs"
        out.append((name, path, state))
    return out


def write(root, check_only=False):
    rows = plan(root)
    for name, path, state in rows:
        if state == "missing" and not check_only:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(render(name))
            state = "written"
        print("%-18s %s  (%s)" % (name, state, os.path.relpath(path, root)))
    differs = [n for n, _p, s in rows if s == "differs"]
    if differs:
        print("left alone, because they differ from the template (an edited agent is yours): "
              + ", ".join(differs), file=sys.stderr)
    return 1 if differs else 0


def selftest():
    tmp = tempfile.mkdtemp(prefix="write-agents-selftest-")
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    try:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = write(tmp)
        files = sorted(os.listdir(os.path.join(tmp, ".claude", "agents")))
        expect("all three are written", rc == 0 and files == sorted(n + ".md" for n in AGENTS))
        text = open(os.path.join(tmp, ".claude", "agents", "roadmap-builder-a.md")).read()
        expect("frontmatter opens the file", text.startswith("---\nname: roadmap-builder-a\n"))
        expect("tier A builds at xhigh", "\neffort: xhigh\n" in text)
        expect("the model is inherited, never downgraded here", "\nmodel: inherit\n" in text)
        expect("the context budget is in the body", "offset and limit" in text)
        v = open(os.path.join(tmp, ".claude", "agents", "roadmap-verifier.md")).read()
        expect("the verifier changes no code", "you change no code" in v and "\neffort: high\n" in v)
        edited = os.path.join(tmp, ".claude", "agents", "roadmap-builder.md")
        with open(edited, "a") as fh:
            fh.write("\nmy own note\n")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = write(tmp)
        expect("an edited agent is never overwritten", rc == 1 and "my own note" in open(edited).read())
        os.remove(edited)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = write(tmp, check_only=True)
        expect("--check writes nothing", not os.path.exists(edited))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="the project root")
    ap.add_argument("--check", action="store_true", help="report what would be written, write nothing")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.root or not os.path.isdir(args.root):
        print("give --root <project-root>", file=sys.stderr)
        return 2
    return write(os.path.abspath(args.root), args.check)


if __name__ == "__main__":
    sys.exit(main())
