#!/usr/bin/env python3
"""Record that the project's batch barrier passed on one commit of the main branch.

Why this exists: a run that stops inside its barrier leaves merges no green barrier proved, and the
next run must not build on top of them. plan-pipeline.py reads the commit recorded here to know
whether the barrier is owed. The barrier agent runs this on a green exit, and it is a script of its
own — not a flag of plan-pipeline.py — because the Workflow harness relays the request that launched
the run to every agent, and that request says to run plan-pipeline.py: a role told to run it too
cannot be told from one obeying the relay.

    python3 record-barrier.py --root <project> --sha <commit the barrier ran on>
    python3 record-barrier.py --selftest

The record lives inside the git directory (no commit, no HEAD moved, shared by every worktree). It
refuses a commit the main branch (`mainBranch` in docs/process/pipeline.json, default main) does not
contain. Exit codes: 0 recorded, 1 refused or --selftest failed, 2 usage.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def _plan():
    spec = importlib.util.spec_from_file_location("plan_pipeline", os.path.join(HERE, "plan-pipeline.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record(root, sha):
    plan = _plan()
    cfg_path = os.path.join(root, plan.CONFIG)
    cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.isfile(cfg_path) else {}
    return plan.record_barrier(root, cfg.get("mainBranch") or "main", sha)


def selftest():
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    repo = tempfile.mkdtemp(prefix="record-barrier-selftest-")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    try:
        def git(*a):
            return subprocess.run(["git", "-C", repo] + list(a), capture_output=True, text=True, env=env, check=True).stdout.strip()
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
        git("commit", "-q", "--allow-empty", "-m", "one")
        h1 = git("rev-parse", "HEAD")
        git("commit", "-q", "--allow-empty", "-m", "two")
        plan = _plan()
        expect("nothing is recorded to begin with", not os.path.isfile(plan.barrier_state_path(repo)))
        rc = main(["--root", repo, "--sha", h1])
        expect("a commit of the main branch is recorded", rc == 0 and json.load(open(plan.barrier_state_path(repo)))["sha"] == h1)
        orphan = git("commit-tree", "-m", "orphan", git("rev-parse", "HEAD^{tree}"))
        rc = main(["--root", repo, "--sha", orphan])
        expect("a commit the main branch does not contain is refused, and the old record stands",
               rc == 1 and json.load(open(plan.barrier_state_path(repo)))["sha"] == h1)
        expect("a name that is no commit is refused", main(["--root", repo, "--sha", "nope"]) == 1)
        expect("the record is no tracked file", git("status", "--porcelain") == "")
    finally:
        shutil.rmtree(repo, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root")
    ap.add_argument("--sha", help="the main-branch commit the barrier ran on and passed")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.root and a.sha and os.path.isdir(a.root)):
        print("give --root <project-root> and --sha <commit>", file=sys.stderr)
        return 2
    try:
        print("recorded: the barrier passed on %s" % record(os.path.abspath(a.root), a.sha)[:9], file=sys.stderr)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
