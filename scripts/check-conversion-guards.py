#!/usr/bin/env python3
"""Exercise every path on which convert-to-multi.py must refuse.

The conversion is destructive: it renames the roadmap, moves two blocks into a
new index, and rewrites paths in a file another skill owns. Its refusals are the
only thing standing between a mistake and a project that has to be restored from
a backup directory. Refusals are also the half nobody runs by hand -- the happy
path gets exercised every time the conversion is used, and a guard that stopped
working would go unnoticed until the day it was needed.

Each case builds its own throwaway tree from benchmark/fixture/state, breaks one
thing, runs the real conversion against it, and asserts two things: it exited
non-zero, and it left the tree byte-for-byte as it found it. A guard that refuses
after writing something is worse than no guard, because the operator now has a
half-converted project and a message saying it did not happen.

Every tree is removed afterwards, whether the case passed or not. Leftovers are
how one test session contaminates the next.

    python3 scripts/check-conversion-guards.py

Exit codes: 0 every guard held, 1 at least one did not, 2 usage error.
"""

import os
import shutil
import subprocess
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASE = os.path.join(REPO, "benchmark", "fixture", "state")
CONVERT = os.path.join(HERE, "convert-to-multi.py")


def git(args, cwd):
    env = dict(os.environ,
               GIT_AUTHOR_NAME="guards", GIT_AUTHOR_EMAIL="guards@example.invalid",
               GIT_COMMITTER_NAME="guards", GIT_COMMITTER_EMAIL="guards@example.invalid")
    return subprocess.run(["git"] + args, cwd=cwd, env=env,
                          capture_output=True, text=True)


def build(mutate):
    parent = tempfile.mkdtemp(prefix="sdr-guards-")
    proj = os.path.join(parent, "project")
    shutil.copytree(BASE, proj)
    mutate(proj)
    for cmd in (["init", "-q", "."], ["add", "-A"], ["commit", "-qm", "fixture"]):
        git(cmd, proj)
    return parent, proj


# --- the breakages, one per guard ------------------------------------------

def odd_fences(proj):
    """D1 — an unclosed ``` fence makes the block extractor untrustworthy."""
    with open(os.path.join(proj, "docs", "ROADMAP.md"), "a", encoding="utf-8") as fh:
        fh.write("\n```\nthis fence is never closed\n")


def stale_txt(proj):
    """D3 — a name in the .txt that no `### ` entry carries."""
    with open(os.path.join(proj, "docs", "roadmap.txt"), "a", encoding="utf-8") as fh:
        fh.write("pauta-ghost-feature\n")


def section_without_index(proj):
    """Rule 9's contradiction — a section roadmap and no index is an interrupted run."""
    with open(os.path.join(proj, "docs", "ROADMAP-pauta.md"), "w", encoding="utf-8") as fh:
        fh.write("# squatter\n")


def already_multi(proj):
    """An index already on disk: the project is multi-section, or a run half-finished."""
    for name, body in (("ROADMAP-pauta.md", "# squatter\n"),
                       ("ROADMAP-INDEX.md", "# Index\n\n## Roadmaps\n")):
        with open(os.path.join(proj, "docs", name), "w", encoding="utf-8") as fh:
            fh.write(body)


def txt_target_taken(proj):
    """D5 — the lowercase rename target exists.

    This is the only shape that reaches D5. The `.md` half of the same guard is
    unreachable from outside: any tree carrying `docs/ROADMAP-<slug>.md` trips the
    section-without-index check first. Worth knowing rather than assuming, and
    worth keeping: D5 is what protects the rename if either earlier guard is ever
    narrowed.
    """
    with open(os.path.join(proj, "docs", "roadmap-pauta.txt"), "w", encoding="utf-8") as fh:
        fh.write("squatter\n")


CASES = [
    ("D1  an unclosed ``` fence", odd_fences),
    ("D3  a .txt naming a feature the roadmap lacks", stale_txt),
    ("R9  a section roadmap with no index", section_without_index),
    ("R9  an index already present", already_multi),
    ("D5  the lowercase rename target is taken", txt_target_taken),
]


def main():
    if not os.path.isdir(BASE):
        print("no fixture at %s" % BASE, file=sys.stderr)
        return 2

    failures = []
    for label, mutate in CASES:
        parent, proj = build(mutate)
        try:
            before = git(["status", "--porcelain"], proj).stdout
            run = subprocess.run([sys.executable, CONVERT, "--root", proj],
                                 capture_output=True, text=True)
            after = git(["status", "--porcelain"], proj).stdout
            refused = run.returncode != 0
            intact = before == after
            if refused and intact:
                print("  ✓ %s" % label)
            else:
                print("  ✗ %s" % label)
                if not refused:
                    print("      it converted instead of refusing (exit %d)" % run.returncode)
                if not intact:
                    print("      it wrote to the tree before refusing")
                failures.append(label)
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    # The happy path, so a guard that refuses everything cannot pass this file.
    parent, proj = build(lambda p: None)
    try:
        run = subprocess.run([sys.executable, CONVERT, "--root", proj],
                             capture_output=True, text=True)
        if run.returncode == 0 and os.path.isfile(
                os.path.join(proj, "docs", "ROADMAP-INDEX.md")):
            print("  ✓ control: a clean tree still converts")
        else:
            print("  ✗ control: a clean tree no longer converts (exit %d)" % run.returncode)
            failures.append("control")
    finally:
        shutil.rmtree(parent, ignore_errors=True)

    print("\n%d guards, %d failed" % (len(CASES) + 1, len(failures)))
    if failures:
        print("failed: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
