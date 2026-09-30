#!/usr/bin/env python3
"""Classify a failing test by where it fails: before the merges, after them, or neither. Writes nothing.

Why this exists: manager mode at level `unblock` repairs what would otherwise stop it — a red batch
barrier above all. Letting an agent turn a red barrier green is only safe if the call "this is a
regression" or "this was already broken" is not the agent's opinion. On a real project a barrier went
red three times on one test whose inputs were identical to a green run's; the evidence that settled it
was a comparison between two trees, and a comparison is a script's job.

It checks out BASE (the main branch before the merges being judged) and HEAD into temporary git
worktrees and runs the one test command RUNS times in each:

  regression      fails on HEAD, passes every run on BASE — the merges broke it. With --merged, the
                  commits between BASE and HEAD are bisected (RUNS runs per probe) and the first one
                  where it fails is named, with the merged feature that owns it.
  preexisting     fails on BASE too — it was broken, or flaky, before these merges.
  not-reproduced  passes every run on both — nothing here explains the red; a person looks.

    python3 triage-probe.py --root <project> --base <commit> --test "<command>" [--head HEAD]
        [--runs 3] [--setup "<command>"] [--merged <feature>:<before>:<after> ...]
    python3 triage-probe.py --selftest

Prints one JSON object on stdout. Exit codes: 0 classified, 2 usage or git failed, 1 --selftest failed.
"""

import argparse
import json
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


def git(root, *argv):
    r = subprocess.run(["git", "-C", root] + list(argv), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (argv[0], r.stderr.strip()))
    return r.stdout.strip()


class Trees:
    """Temporary detached worktrees, removed on exit whatever happens."""

    def __init__(self, root, setup=""):
        self.root, self.setup, self.base = root, setup, tempfile.mkdtemp(prefix="triage-probe-")
        self.made = []

    def at(self, commit):
        wt = os.path.join(self.base, "t%d" % len(self.made))
        git(self.root, "worktree", "add", "--detach", wt, commit)
        self.made.append(wt)
        if self.setup and subprocess.run(self.setup, shell=True, cwd=wt, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL).returncode != 0:
            raise RuntimeError("the project's setup failed at %s" % commit)
        return wt

    def close(self):
        for wt in self.made:
            subprocess.run(["git", "-C", self.root, "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(self.base, ignore_errors=True)


def fails(tree, test, runs):
    """How many of `runs` runs of the test failed in this tree."""
    n = 0
    for _ in range(runs):
        n += subprocess.run(test, shell=True, cwd=tree, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode != 0
    return n


def classify(root, base, head, test, runs, setup="", merged=()):
    trees = Trees(root, setup)
    try:
        base_sha, head_sha = git(root, "rev-parse", base), git(root, "rev-parse", head)
        on_head = fails(trees.at(head_sha), test, runs)
        on_base = fails(trees.at(base_sha), test, runs)
        out = {"test": test, "base": base_sha, "head": head_sha, "runs": runs,
               "failedOnHead": on_head, "failedOnBase": on_base}
        if on_base:
            out["kind"] = "preexisting"
        elif on_head:
            out["kind"] = "regression"
            commits = git(root, "rev-list", "--reverse", "%s..%s" % (base_sha, head_sha)).split()
            lo, hi = 0, len(commits) - 1  # the first commit where it fails; HEAD fails, BASE does not
            while lo < hi:
                mid = (lo + hi) // 2
                if fails(trees.at(commits[mid]), test, runs):
                    hi = mid
                else:
                    lo = mid + 1
            culprit = commits[lo] if commits else head_sha
            out["commit"] = culprit
            out["subject"] = git(root, "log", "-1", "--format=%s", culprit)
            for spec in merged:
                name, before, after = spec.split(":", 2)
                inside = git(root, "rev-list", "%s..%s" % (before, after)).split()
                if culprit in inside:
                    out["feature"] = name
                    break
        else:
            out["kind"] = "not-reproduced"
        return out
    finally:
        trees.close()


# --------------------------------------------------------------------------- selftest

def selftest():
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    repo = tempfile.mkdtemp(prefix="triage-probe-selftest-")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")

    def commit(msg, files):
        for path, body in files.items():
            with open(os.path.join(repo, path), "w") as fh:
                fh.write(body)
        subprocess.run(["git", "-C", repo, "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", repo, "commit", "-qm", msg], check=True, env=env)
        return git(repo, "rev-parse", "HEAD")
    try:
        subprocess.run(["git", "init", "-q", repo], check=True)
        test = "python3 -c \"import calc,sys; sys.exit(0 if calc.add(2,2)==4 else 1)\""
        c0 = commit("base", {"calc.py": "def add(a, b):\n    return a + b\n", "notes.txt": "0\n"})
        a1 = commit("feat(a): notes", {"notes.txt": "1\n"})
        b1 = commit("feat(b): tidy add", {"calc.py": "def add(a, b):\n    return a + b + 1\n"})
        b2 = commit("feat(b): comment", {"notes.txt": "2\n"})
        merged = ["feature-a:%s:%s" % (c0, a1), "feature-b:%s:%s" % (a1, b2)]
        r = classify(repo, c0, "HEAD", test, 2, merged=merged)
        expect("a test the merges broke is a regression", r["kind"] == "regression"
               and r["failedOnHead"] == 2 and r["failedOnBase"] == 0)
        expect("bisection names the first failing commit", r.get("commit") == b1)
        expect("and the merged feature that owns it", r.get("feature") == "feature-b")
        r = classify(repo, a1, "HEAD", "python3 -c \"import sys; sys.exit(1)\"", 2)
        expect("a test failing before the merges too is preexisting", r["kind"] == "preexisting")
        r = classify(repo, c0, a1, test, 2)
        expect("a test passing on both is not reproduced", r["kind"] == "not-reproduced")
        expect("every temporary worktree is removed",
               git(repo, "worktree", "list").count("\n") == 0)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root")
    ap.add_argument("--base", help="the main branch's commit before the merges being judged")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--test", help="one command that runs the failing test and exits non-zero on failure")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--setup", default="", help="run in each temporary worktree first (pipeline.json setup)")
    ap.add_argument("--merged", action="append", default=[], help="<feature>:<before>:<after>, repeatable")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.root and a.base and a.test):
        print("give --root, --base and --test", file=sys.stderr)
        return 2
    try:
        print(json.dumps(classify(os.path.abspath(a.root), a.base, a.head, a.test, max(1, a.runs), a.setup, a.merged)))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
