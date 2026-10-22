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
                  main branch's state after each merge is tested and the first that fails names the
                  feature; its commits are bisected (RUNS runs per probe) when they are one line of
                  states, and otherwise that state is named with a note. A break after every merged
                  state names no feature. Without --merged, BASE..HEAD is bisected the same way. A test
                  the merges added is absent on BASE: that counts as passing there.
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


def fails(tree, test, runs, absent=None):
    """How many of `runs` runs of the test failed in this tree. A command that selected no test is not
    a failing test: it exits non-zero on every tree, and counting that as a failure would call a test
    that never ran 'preexisting'. On HEAD that is a broken selector and an error. On a tree from before
    the test existed (`absent` given) it is a state that does not fail it: the merges being judged added
    the test, and the old probe stopped there with a misleading "fix its selector" (review of 3.48.0's draft)."""
    n = 0
    for _ in range(runs):
        r = subprocess.run(test, shell=True, cwd=tree, capture_output=True, text=True, errors="replace")
        if r.returncode != 0 and NOTHING_RAN.search(r.stdout + r.stderr):
            if absent is not None:
                absent.append(tree)
                return 0
            raise RuntimeError("the test command selected no test (the runner said so): fix its selector — by name, "
                               "not by file and line — before the result means anything")
        n += r.returncode != 0
    return n


def classify(root, base, head, test, runs, setup="", merged=()):
    trees = Trees(root, setup)
    try:
        base_sha, head_sha = git(root, "rev-parse", base), git(root, "rev-parse", head)
        specs = [spec.split(":", 2) for spec in merged]
        if any(len(sp) != 3 for sp in specs):
            raise RuntimeError("--merged takes <feature>:<before>:<after>")
        afters = [git(root, "rev-parse", sp[2]) for sp in specs]
        for x, y, sx, sy in zip(afters, afters[1:], specs, specs[1:]):
            # the bisect over these states assumes the order the main branch had them in (review of 3.48.0's draft)
            if subprocess.run(["git", "-C", root, "merge-base", "--is-ancestor", x, y]).returncode != 0:
                raise RuntimeError("--merged must be given in merge order: %s's state is not an ancestor of %s's" % (sx[0], sy[0]))
        on_head = fails(trees.at(head_sha), test, runs)
        absent = []
        on_base = fails(trees.at(base_sha), test, runs, absent)
        out = {"test": test, "base": base_sha, "head": head_sha, "runs": runs,
               "failedOnHead": on_head, "failedOnBase": on_base}
        if absent:
            out["absentOnBase"] = True  # the test came with these merges
        if on_base:
            out["kind"] = "preexisting"
        elif on_head:
            out["kind"] = "regression"

            def first_failing(states):
                """Index of the first state that fails, when the last one fails and the history before it passed."""
                lo, hi = 0, len(states) - 1
                while lo < hi:
                    mid = (lo + hi) // 2
                    if fails(trees.at(states[mid]), test, runs, []):
                        hi = mid
                    else:
                        lo = mid + 1
                return lo

            def line_of_states(a, b):
                """The commits of a..b that descend from a, oldest first, when each is built on the one before —
                a merge of the main branch into a feature branch qualifies, its other parent being older than a.
                None when two branches that ran side by side both lie inside: their trees are not one sequence,
                and a bisect over them can blame either."""
                rows = [r.split() for r in git(root, "rev-list", "--reverse", "--topo-order", "--parents",
                                               "--ancestry-path", "%s..%s" % (a, b)).splitlines()]
                inside, prev, line = {r[0] for r in rows}, git(root, "rev-parse", a), []
                for c, *parents in rows:
                    if [p for p in parents if p in inside or p == prev] != [prev]:
                        return None
                    line.append(c)
                    prev = c
                return line

            def bisect(a, b):
                """The first failing commit of a..b, b failing and a passing; or b, with the reason, when the
                stretch is not one line of states."""
                line = line_of_states(a, b)
                if line is None:
                    return git(root, "rev-parse", b), ("branches that ran side by side merged between %s and %s, so "
                                                        "no commit inside is named: the one given is the last state" % (a[:9], b[:9]))
                if not line:
                    return git(root, "rev-parse", b), ("no commit lies on a path from %s to %s (the same commit, or not built on it): "
                                                        "the one given is the last state" % (a[:9], b[:9]))
                return line[first_failing(line)], None

            # 3.48.0: the main branch's own states first. A feature branch that took the main branch by a merge
            # (roadmap-pipeline.js, BRING_MAIN) lands with commits forked before BASE, whose trees lack what BASE had:
            # a commit-by-commit bisect then blamed a feature merged earlier, or ran a test those trees did not have yet
            # (review of 3.47.0). The tree each merge left the main branch in is a state it really had; the first one
            # that fails names the feature, and the stretch inside it is bisected only when it is one line of states.
            # The last state is tested, never assumed: in a second triage cycle the first cycle's repair is merged
            # after every one of them, and a break it made belongs to no feature (review of 3.48.0's draft).
            note = None
            if specs and (afters[-1] == head_sha or fails(trees.at(afters[-1]), test, runs, [])):
                name, before, after = specs[first_failing(afters)]
                out["feature"] = name
                culprit, note = bisect(before, after)
            elif specs:
                culprit, note = bisect(afters[-1], head_sha)
                note = "every merged state passes: it broke after them" + ("; " + note if note else "")
            else:
                culprit, note = bisect(base_sha, head_sha)
            if note:
                out["note"] = note
            out["commit"] = culprit
            out["subject"] = git(root, "log", "-1", "--format=%s", culprit)
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
        # 3.48.0, the review of 3.47.0's repository: feature b's branch forked at c0, broke add() in b1, then took the
        # main branch (feature a, merged meanwhile) by a merge before it fast-forwarded. The old bisect blamed feature a.
        repo2 = tempfile.mkdtemp(prefix="triage-probe-selftest-merge-")
        try:
            g = lambda *a: subprocess.run(["git", "-C", repo2] + list(a), check=True, env=env, capture_output=True)
            subprocess.run(["git", "init", "-q", "-b", "main", repo2], check=True)
            def put(path, body, msg):
                with open(os.path.join(repo2, path), "w") as fh:
                    fh.write(body)
                g("add", "-A"); g("commit", "-qm", msg)
                return git(repo2, "rev-parse", "HEAD")
            m0 = put("calc.py", "def add(a, b):\n    return a + b\n", "base")
            g("checkout", "-qb", "feat/b")
            put("calc.py", "def add(a, b):\n    return a + b + 1\n", "feat(b): tidy add")
            g("checkout", "-q", "main")
            ma = put("notes.txt", "a\n", "feat(a): notes")
            g("checkout", "-q", "feat/b"); g("merge", "-q", "--no-edit", "main")
            mb = git(repo2, "rev-parse", "HEAD")
            g("checkout", "-q", "main"); g("merge", "-q", "--ff-only", "feat/b")
            r = classify(repo2, m0, "HEAD", test, 2, merged=["feature-a:%s:%s" % (m0, ma), "feature-b:%s:%s" % (ma, mb)])
            expect("after a branch that took main by a merge, the regression is its feature's, not the one merged before it",
                   r["kind"] == "regression" and r.get("feature") == "feature-b" and r.get("commit") == mb)
            # The review of 3.48.0's draft: an earlier run whose feature b forked before it and took main by a merge
            # is still one line of states from its base (b's own first commit lies outside), so a commit inside
            # the run is named — here feature a's, which broke add() before b merged.
            g("checkout", "-q", "main"); mB = put("calc.py", "def add(a, b):\n    return a + b\n", "run base: add fixed")
            g("checkout", "-qb", "feat/d", m0); put("d.txt", "d\n", "feat(d): file")
            g("checkout", "-q", "main"); a1x = put("calc.py", "def add(a, b):\n    return a * b + 1\n", "feat(c): rewrite add")
            put("notes.txt", "c\n", "feat(c): notes")
            g("checkout", "-q", "feat/d"); g("merge", "-q", "--no-edit", "main"); put("d.txt", "d2\n", "feat(d): more")
            g("checkout", "-q", "main"); g("merge", "-q", "--ff-only", "feat/d"); rec = put("STATUS", "x\n", "docs: record pipeline run")
            r = classify(repo2, mB, "HEAD", test, 2, merged=["earlier-run:%s:%s" % (mB, rec)])
            expect("an earlier run with a merge from main inside it is bisected to the commit that broke it",
                   r.get("feature") == "earlier-run" and r.get("commit") == a1x and "note" not in r)
            # Two branches built side by side from the run's base, then merged: their trees are not one sequence.
            mC = put("calc.py", "def add(a, b):\n    return a + b\n", "fix add")
            g("checkout", "-qb", "feat/e"); put("e.txt", "e\n", "feat(e): file")
            g("checkout", "-q", "main"); put("calc.py", "def add(a, b):\n    return 0\n", "feat(f): break add")
            g("checkout", "-q", "feat/e"); g("merge", "-q", "--no-edit", "main"); me = git(repo2, "rev-parse", "HEAD")
            g("checkout", "-q", "main"); g("merge", "-q", "--ff-only", "feat/e")
            r = classify(repo2, mC, "HEAD", test, 2, merged=["earlier-run:%s:%s" % (mC, me)])
            expect("two branches side by side inside the stretch: the last state is named, and the note says why",
                   r.get("commit") == me and "side by side" in r.get("note", ""))
        finally:
            shutil.rmtree(repo2, ignore_errors=True)
        # The review of 3.48.0's draft, three more paths, in a repository of their own.
        repo3 = tempfile.mkdtemp(prefix="triage-probe-selftest-order-")
        try:
            h = lambda *a: subprocess.run(["git", "-C", repo3] + list(a), check=True, env=env, capture_output=True)
            subprocess.run(["git", "init", "-q", "-b", "main", repo3], check=True)
            def put3(path, body, msg):
                with open(os.path.join(repo3, path), "w") as fh:
                    fh.write(body)
                h("add", "-A"); h("commit", "-qm", msg)
                return git(repo3, "rev-parse", "HEAD")
            t3 = "sh -c 'if [ -f t.txt ]; then grep -q ok t.txt; else echo \"no tests ran\"; exit 5; fi'"
            q0 = put3("x.txt", "0\n", "base, before the test exists")
            q1 = put3("t.txt", "bad\n", "feat(t): add its test, failing")
            q2 = put3("x.txt", "1\n", "feat(u): other")
            r = classify(repo3, q0, "HEAD", t3, 2, merged=["feature-t:%s:%s" % (q0, q1), "feature-u:%s:%s" % (q1, q2)])
            expect("a failing test the merges added is absent on BASE, and the feature that added it is named",
                   r["kind"] == "regression" and r.get("absentOnBase") and r.get("feature") == "feature-t" and r.get("commit") == q1)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = main(["--root", repo3, "--base", q0, "--test", t3, "--merged", "feature-u:%s:%s" % (q1, q2),
                           "--merged", "feature-t:%s:%s" % (q0, q1)])
            expect("--merged out of merge order is refused, not answered wrong", rc == 2 and "merge order" in err.getvalue())
            h("checkout", "-qb", "side", q0); qs = put3("x.txt", "s\n", "side"); h("checkout", "-q", "main")
            r = classify(repo3, qs, "main", t3, 2)
            expect("a BASE the head is not built on names the head, and says why",
                   r.get("commit") == q2 and r.get("note", "").startswith("no commit lies on a path"))
        finally:
            shutil.rmtree(repo3, ignore_errors=True)
        r = classify(repo, c0, "HEAD", test, 2, merged=["feature-a:%s:%s" % (c0, a1)])
        expect("a break after every merged state (a second cycle's repair) is pinned on no feature",
               r["kind"] == "regression" and "feature" not in r and r.get("commit") == b1
               and r.get("note", "").startswith("every merged state passes"))
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
    ap.add_argument("--merged", action="append", default=[], help="<feature>:<before>:<after>, repeatable, in merge order")
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
