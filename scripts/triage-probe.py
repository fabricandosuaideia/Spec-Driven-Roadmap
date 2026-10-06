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

The test command must select by NAME (a pytest node id, `--grep` for Playwright, `-t` for jest and
vitest), never by `file:line`: a line moves when anyone adds one above it, and the command then runs no
test. A command with a `file.ext:LINE` selector is refused (exit 2) before anything runs.

Prints one JSON object on stdout. Exit codes: 0 classified, 2 usage or git failed, 1 --selftest failed.
"""

import argparse
import contextlib
import io
import json
import os
import re
import shlex
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


# A test named by file and line moves when anyone adds a line above it, and then selects nothing.
TEST_EXT = "py|pyi|pyx|js|jsx|ts|tsx|mjs|cjs|vue|coffee|rb|go|rs|java|kt|php|cs|c|cpp|exs?|swift|jl|feature|sh|bats"
LINE_SELECTOR = re.compile(r"\S+\.(?:%s):[0-9]+(?::[0-9]+)*" % TEST_EXT, re.I)


def line_selector(test):
    """The `path/file.ext:LINE` argument of a test command, or None. Judged token by token, so a quoted
    test name that happens to contain `a.ts:5`, a URL, an option's value or an env assignment is not one."""
    try:
        tokens = shlex.split(test)
    except ValueError:
        tokens = test.split()
    for tok in tokens:
        if tok.startswith("-") or "=" in tok or "://" in tok or re.search(r"\s", tok):
            continue
        m = LINE_SELECTOR.fullmatch(tok)
        if m:
            return m
    return None


class Trees:
    """Temporary detached worktrees, removed on exit whatever happens."""

    def __init__(self, root, setup=""):
        self.root, self.setup = root, setup
        self.made = []

    def at(self, commit):
        # Each tree is its own mkdtemp directory: a project that derives the names of its resources from
        # the basename of the directory it runs in must not see the same basename twice, here or in a
        # probe running beside this one.
        wt = tempfile.mkdtemp(prefix="triage-probe-")
        self.made.append(wt)
        git(self.root, "worktree", "add", "--detach", wt, commit)
        if self.setup and subprocess.run(self.setup, shell=True, cwd=wt, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL).returncode != 0:
            raise RuntimeError("the project's setup failed at %s" % commit)
        return wt

    def close(self):
        for wt in self.made:
            subprocess.run(["git", "-C", self.root, "worktree", "remove", "--force", wt], capture_output=True)
            shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(["git", "-C", self.root, "worktree", "prune"], capture_output=True)


NOTHING_RAN = re.compile(r"No tests found|no tests ran|collected 0 items|Ran 0 tests|no test files? found", re.I)


def fails(tree, test, runs):
    """How many of `runs` runs of the test failed in this tree. A command that selected no test is not
    a failing test: it exits non-zero on every tree, and counting that as a failure would call a test
    that never ran 'preexisting'."""
    n = 0
    for _ in range(runs):
        r = subprocess.run(test, shell=True, cwd=tree, capture_output=True, text=True, errors="replace")
        if r.returncode != 0 and NOTHING_RAN.search(r.stdout + r.stderr):
            raise RuntimeError("the test command selected no test (the runner said so): fix its selector — by name, "
                               "not by file and line — before the result means anything")
        n += r.returncode != 0
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
        # 3.36.0: a project that derives the names of its resources (a compose project, a port, a
        # database) from the basename of the directory it runs in collides with a probe running beside
        # it when every probe's trees are called t0, t1
        one, two = Trees(repo), Trees(repo)
        try:
            names = [os.path.basename(x) for x in (one.at(c0), one.at(a1), two.at(c0))]
        finally:
            one.close()
            two.close()
        expect("no two temporary worktrees share a basename, and none is a bare t<n>",
               len(set(names)) == 3 and not any(re.fullmatch(r"t\d+", n) for n in names))
        for sel in ("npx playwright test e2e/setup-checklist.spec.ts:157", "bundle exec rspec spec/a_spec.rb:12:3",
                    "go test ./... -run x pkg/a_test.go:40", "pytest tests/A_TEST.PY:9", "rspec spec/a_spec.rb:12", "run src/a.vue:5"):
            expect("a line-number selector is refused: %s" % sel, line_selector(sel) is not None)
        for ok in ("npx playwright test e2e/a.spec.ts -g \"renders a.ts:5\"", "jest -t 'a.js:3 works'", 
                   "FOO=a.go:5 pytest a.py::t", "curl http://x.io/a.py:8080 && pytest a.py::t", "pytest 'f.py::test[a.py:1]'",
                   "npx playwright test e2e/a.spec.ts -g \"setup checklist\"", "python3 -m pytest tests/test_x.py::test_y",
                   "npx vitest run a.test.ts -t name", "BASE=http://example.com:8080 pytest tests/test_x.py::t",
                   "curl 127.0.0.1:3000 && pytest a.py::b"):
            expect("a name selector is accepted: %s" % ok, line_selector(ok) is None)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["--root", repo, "--base", c0, "--test", "npx playwright test e2e/a.spec.ts:157"])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["--root", repo, "--base", c0, "--test", "python3 -c \"print('No tests found'); raise SystemExit(1)\""])
        expect("a command whose runner says it selected no test is not a failing test", rc == 2 and "selected no test" in err.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["--root", repo, "--base", c0, "--test", "npx playwright test e2e/a.spec.ts:157"])
        expect("the probe refuses a line-number command before running anything", rc == 2 and "line" in err.getvalue())
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
    sel = line_selector(a.test)
    if sel:
        print("the test command selects by file and line (%s): a line moves when anyone adds one above it and "
              "the command then runs no test. Select by name: a pytest node id (file.py::test_name), "
              "--grep/-g for Playwright, -t for jest and vitest" % sel.group(0), file=sys.stderr)
        return 2
    try:
        print(json.dumps(classify(os.path.abspath(a.root), a.base, a.head, a.test, max(1, a.runs), a.setup, a.merged)))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
