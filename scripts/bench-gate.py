#!/usr/bin/env python3
"""Measure the project's full gate, serial against its parts run at once. Writes nothing.

Why this exists: the pipeline runs the full gate a fixed number of times per feature (the prover
once, the merger once), so its duration is paid on every feature. On one measured project,
running typecheck, lint and tests at the same time took 47-48 s against ~112 s in series — but
that is one project's number, and the same guide records three ways a timing lies: a command that
failed was timed as if it had worked, a single run in a busy minute was taken as the truth, and
the order of runs was not alternated. So this never prints a number to adopt; it measures yours,
refuses to compare runs that failed, alternates the order, and records the machine's load.

It reads the gate from docs/process/pipeline.json (or --gate). A gate of the form `a && b && c` is
run as written, and as its parts at once; parts must not depend on each other's output — that is
yours to know, and the report says so. How many workers your test runner should use is not
measured here: it is a flag of your runner, and on the project behind the guide the runner's own
default was the best or tied every time; measure it paired against that default.

    python3 bench-gate.py --root <project> [--runs 2] [--gate "<command>"]
    python3 bench-gate.py --root <project> --lanes 2     # can N features be proved at once here?
    python3 bench-gate.py --selftest

`--lanes N` answers the question the pipeline's `lanes` setting depends on and nothing else can: can
this project run its gate N times at once on this machine? It checks out HEAD into N temporary git
worktrees, runs the project's `setup` in each (pipeline.json), runs the gate once alone and then in
all N at the same time, and reports each exit and duration. One failure among the N is the answer: the
gate shares something it does not isolate per run — a database, a port, a queue, a pool — and lanes
above 1 would turn that into failed proofs and retries. That limit is the project's, not the
pipeline's; this reports it and changes nothing.

Exit codes: 0 measured, 1 a run failed (timings not compared) or --selftest failed, 2 usage.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass

CONFIG = os.path.join("docs", "process", "pipeline.json")


def load():
    try:
        return round(os.getloadavg()[0], 1)
    except (AttributeError, OSError):  # Windows has no load average
        return None


def run_serial(cmd, cwd):
    t = time.monotonic()
    r = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.monotonic() - t, [r.returncode]


def run_parallel(parts, cwd):
    t = time.monotonic()
    procs = [subprocess.Popen(p, shell=True, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for p in parts]
    codes = [p.wait() for p in procs]
    return time.monotonic() - t, codes


def run_in_trees(cmd, trees):
    t = time.monotonic()
    procs = [subprocess.Popen(cmd, shell=True, cwd=wt, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for wt in trees]
    codes = [p.wait() for p in procs]
    return time.monotonic() - t, codes


def bench_lanes(root, cmd, lanes, setup=""):
    """(alone seconds, alone exit, together seconds, together exits, load before/after)."""
    base = tempfile.mkdtemp(prefix="bench-gate-lanes-")
    trees = []
    try:
        for i in range(lanes):
            wt = os.path.join(base, "lane%d" % (i + 1))
            r = subprocess.run(["git", "-C", root, "worktree", "add", "--detach", wt, "HEAD"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("git worktree add failed: %s" % r.stderr.strip())
            trees.append(wt)
            if setup and subprocess.run(setup, shell=True, cwd=wt, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL).returncode != 0:
                raise RuntimeError("the project's setup failed in a worktree: %s" % setup)
        alone, codes = run_serial(cmd, trees[0])
        before = load()
        together, tcodes = run_in_trees(cmd, trees)
        return alone, codes[0], together, tcodes, [before, load()]
    finally:
        for wt in trees:
            subprocess.run(["git", "-C", root, "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(base, ignore_errors=True)


def report_lanes(lanes, alone, alone_exit, together, codes, loads):
    print("alone     %7.2f s   exit %s" % (alone, alone_exit))
    print("%d at once %7.2f s   exits %s   load %s -> %s" % (lanes, together, codes, loads[0], loads[1]))
    if alone_exit != 0:
        print("\nThe gate fails even alone, so nothing about lanes can be concluded. Fix it first.")
        return 1
    bad = [i + 1 for i, c in enumerate(codes) if c != 0]
    if bad:
        print("\n%d of %d gates run at once failed (lane %s). This project cannot prove %d features at once "
              "as it stands: its gate shares something it does not isolate per run (a database, a port, a "
              "queue, a pool). Keep \"lanes\" at 1, or make the gate isolate it and measure again."
              % (len(bad), lanes, ", ".join(map(str, bad)), lanes))
        return 1
    print("\nAll %d passed at once. Each took about %.1fx its time alone, so %d lanes prove independent "
          "features in about %.0f%% of the time one lane takes — for features that do not depend on each "
          "other; a chain gains nothing. One measurement says little about flakiness under load: run it "
          "again before relying on it." % (lanes, together / alone if alone else 0, lanes,
                                           100.0 * together / (alone * lanes) if alone else 0))
    return 0


def split_gate(cmd):
    return [p.strip() for p in cmd.split("&&") if p.strip()]


def bench(cmd, cwd, runs):
    parts = split_gate(cmd)
    rows = []
    for i in range(runs):  # alternate: S P, P S, ...
        order = ("serial", "parallel") if i % 2 == 0 else ("parallel", "serial")
        for kind in order:
            if kind == "parallel" and len(parts) < 2:
                continue
            before = load()
            secs, codes = run_serial(cmd, cwd) if kind == "serial" else run_parallel(parts, cwd)
            rows.append({"kind": kind, "seconds": round(secs, 2), "codes": codes, "load": [before, load()]})
    return parts, rows


def report(parts, rows, cpus):
    for r in rows:
        print("%-8s %7.2f s   exit %-12s load %s -> %s" % (r["kind"], r["seconds"], r["codes"], r["load"][0], r["load"][1]))
    failed = [r for r in rows if any(c != 0 for c in r["codes"])]
    if failed:
        print("\nA run failed, so no timing is compared: a failed command's duration says nothing about "
              "a passing one. Fix the gate (or the environment) and measure again.")
        return 1
    if len(parts) < 2:
        print("\nThe gate is one command, so there is nothing to run at once. Its duration is the number above.")
        return 0
    ser = [r["seconds"] for r in rows if r["kind"] == "serial"]
    par = [r["seconds"] for r in rows if r["kind"] == "parallel"]
    print("\nserial   %s   parallel %s   (%d CPUs)" % (ser, par, cpus))
    busy = [r for r in rows if r["load"][0] is not None and r["load"][0] > cpus]
    if busy:
        print("The machine's load exceeded its CPU count during %d run(s): treat the numbers as noisy "
              "and measure again when it is quieter." % len(busy))
    if len(ser) < 2 or len(par) < 2:
        print("One run of each says nothing about noise: measure with --runs 2 or more before comparing.")
        return 0
    # The gain has to beat the runs' own spread, or it is noise rather than a result. No fixed
    # threshold: a number chosen here would be one more unmeasured number.
    gain = min(ser) - max(par)
    spread = (max(ser) - min(ser)) + (max(par) - min(par))
    if gain > spread:
        print("Running the %d parts at once was faster in every run, by more than the runs varied among "
              "themselves (%.2f s against %.2f s of spread). If they do not depend on each other's output, a "
              "gate that runs them concurrently and fails when any fails is worth putting in %s — yours to "
              "write and confirm; this script changes nothing." % (len(parts), gain, spread, CONFIG))
    else:
        print("The difference (%.2f s) is within the runs' own spread (%.2f s): no case for changing the gate."
              % (gain, spread))
    return 0


def selftest():
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    tmp = tempfile.mkdtemp(prefix="bench-gate-selftest-")
    py = sys.executable.replace("\\", "/")
    slow = '"%s" -c "import time; time.sleep(0.4)"' % py
    bad = '"%s" -c "raise SystemExit(3)"' % py
    import io
    import contextlib
    parts, rows = bench("%s && %s" % (slow, slow), tmp, 2)
    kinds = [r["kind"] for r in rows]
    expect("the order of runs alternates", kinds == ["serial", "parallel", "parallel", "serial"])
    ser = [r["seconds"] for r in rows if r["kind"] == "serial"]
    par = [r["seconds"] for r in rows if r["kind"] == "parallel"]
    expect("two independent parts run at once take about one part's time", max(par) < min(ser))
    with contextlib.redirect_stdout(io.StringIO()) as out:
        rc = report(parts, rows, os.cpu_count() or 1)
    expect("a faster parallel run is reported, and nothing is written", rc == 0 and "changes nothing" in out.getvalue())
    parts, rows = bench("%s && %s" % (slow, bad), tmp, 1)
    with contextlib.redirect_stdout(io.StringIO()) as out:
        rc = report(parts, rows, os.cpu_count() or 1)
    expect("a failed run is never compared", rc == 1 and "no timing is compared" in out.getvalue())
    parts, rows = bench(slow, tmp, 1)
    expect("a one-command gate is only run serially", [r["kind"] for r in rows] == ["serial"])
    noisy = [{"kind": "serial", "seconds": 0.04, "codes": [0], "load": [None, None]},
             {"kind": "parallel", "seconds": 0.02, "codes": [0, 0], "load": [None, None]},
             {"kind": "parallel", "seconds": 0.03, "codes": [0, 0], "load": [None, None]},
             {"kind": "serial", "seconds": 0.05, "codes": [0], "load": [None, None]}]
    with contextlib.redirect_stdout(io.StringIO()) as out:
        report(["a", "b"], noisy, 4)
    expect("a gain inside the runs' own spread is called noise", "within the runs' own spread" in out.getvalue())
    os.rmdir(tmp)

    # --lanes: a gate that isolates nothing passes at once; one holding a shared lock does not
    repo = tempfile.mkdtemp(prefix="bench-gate-lanes-selftest-")
    lock = os.path.join(tempfile.gettempdir(), "bench-gate-selftest-lock-%d" % os.getpid())
    try:
        subprocess.run(["git", "init", "-q", repo], check=True)
        open(os.path.join(repo, "ok.sh"), "w").write("sleep 0.4\n")
        open(os.path.join(repo, "shared.sh"), "w").write(
            "mkdir %s 2>/dev/null || exit 7\nsleep 0.6\nrmdir %s\n" % (lock, lock))
        subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
        subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"], check=True)
        a, ae, t, codes, loads = bench_lanes(repo, "bash ok.sh", 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = report_lanes(2, a, ae, t, codes, loads)
        expect("a gate that isolates its runs passes at once, faster than twice alone",
               rc == 0 and codes == [0, 0] and t < 2 * a)
        a, ae, t, codes, loads = bench_lanes(repo, "bash shared.sh", 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = report_lanes(2, a, ae, t, codes, loads)
        expect("a gate sharing something it does not isolate fails at once, and lanes are refused",
               rc == 1 and 7 in codes and "cannot prove 2 features at once" in out.getvalue())
        wts = subprocess.run(["git", "-C", repo, "worktree", "list"], capture_output=True, text=True).stdout
        expect("the temporary worktrees are removed", wts.count("\n") == 1)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        if os.path.isdir(lock):
            os.rmdir(lock)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="the project root")
    ap.add_argument("--gate", help="the gate command (default: docs/process/pipeline.json's)")
    ap.add_argument("--runs", type=int, default=2, help="alternating rounds (default 2)")
    ap.add_argument("--lanes", type=int, default=0, help="run the gate N times at once in N worktrees of HEAD")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.root or not os.path.isdir(a.root):
        print("give --root <project-root>", file=sys.stderr)
        return 2
    cmd = a.gate
    if not cmd:
        path = os.path.join(a.root, CONFIG)
        if not os.path.isfile(path):
            print("no --gate and no %s" % CONFIG, file=sys.stderr)
            return 2
        cmd = json.load(open(path, encoding="utf-8")).get("gate") or ""
    if not cmd:
        print("the gate command is empty", file=sys.stderr)
        return 2
    print("gate: %s\n" % cmd)
    if a.lanes and a.lanes > 1:
        setup = ""
        path = os.path.join(a.root, CONFIG)
        if os.path.isfile(path):
            setup = json.load(open(path, encoding="utf-8")).get("setup") or ""
        try:
            res = bench_lanes(os.path.abspath(a.root), cmd, a.lanes, setup)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
        return report_lanes(a.lanes, *res)
    parts, rows = bench(cmd, os.path.abspath(a.root), max(1, a.runs))
    return report(parts, rows, os.cpu_count() or 1)


if __name__ == "__main__":
    sys.exit(main())
