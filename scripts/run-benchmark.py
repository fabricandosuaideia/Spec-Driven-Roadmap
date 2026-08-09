#!/usr/bin/env python3
"""Set up an isolated benchmark run, and score it afterwards.

This script does NOT execute the skill. The skill is a procedure an agent reads
and follows, so an agent runs it; what a script can do is the two things around
that, and those are exactly the two that went wrong when they were done by hand:

  setup   a clean directory whose PARENT holds nothing else. Seven finished runs
          once sat side by side under one parent, and any of them could `ls ..`
          and read the others' answers to the same PRD.
  score   check the seven planted ambiguities reached the destinations
          benchmark/expected.md names, and append the result to RESULTS.md.

Usage:
    python3 scripts/run-benchmark.py setup 0a-single     # prints the path to work in
    python3 scripts/run-benchmark.py score <dir> [--version X] [--record]
    python3 scripts/run-benchmark.py list

Exit codes: 0 scored clean, 1 a planted ambiguity is missing, 2 usage error.
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIXTURE = os.path.join(REPO, "benchmark", "fixture")
RESULTS = os.path.join(REPO, "benchmark", "RESULTS.md")

# Where a run happens. Deliberately outside the repository: a benchmark run
# writes docs/ and .specs/, and those must never land in the skill's own tree.
RUNROOT = os.path.expanduser("~/.cache/sdr-benchmark")

SCENARIOS = {
    "0a-single": ("PRD in docs/, single-section", ["PRD.md"]),
    "0a-multi": ("PRD in docs/, multi-section", ["PRD.md"]),
    "0b-interview": ("empty project, no downstream skill", []),
    "0c-brownfield": ("working code, no scope document", ["brownfield"]),
    "loop": ("PRD in docs/, single-section, option B", ["PRD.md"]),
}

# The seven, keyed to how they surface in a roadmap. Each pattern list is
# alternatives in the languages the skill may write in — it follows the source
# document's language, and this fixture's PRD is Portuguese.
PLANTED = [
    ("1 password rule", r"senha|password|contrase"),
    ("2 role permissions", r"pap[ée]|role|rol\b|permiss|permis"),
    ("3 vote tie-break", r"empat|tie[- ]break|desempat"),
    ("4 votes after edit", r"(voto|vote).{0,60}(edi|alterad)|(edi|edit).{0,60}(voto|vote)"),
    ("5 notification channel", r"canal|channel|e-?mail|smtp|push|in-?app"),
    ("6 public API auth", r"(api).{0,50}(auth|token|chave|key)|(auth|token|chave|key).{0,50}(api)"),
    ("7 retention / deletion", r"reten[cç]|retention|exclus|delete|soft.?delete|purg"),
]


def die(msg, code=2):
    print("✗ " + msg, file=sys.stderr)
    sys.exit(code)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


# --------------------------------------------------------------------------


def cmd_setup(args):
    if args.scenario not in SCENARIOS:
        die("unknown scenario %r. Known: %s" % (args.scenario, ", ".join(SCENARIOS)))
    if not os.path.isdir(FIXTURE):
        die("no benchmark/fixture at %s" % FIXTURE)

    label, wants = SCENARIOS[args.scenario]
    stamp = args.label or args.scenario
    # One run per parent. Nothing else is ever placed beside it, which is the
    # whole point: `ls ..` from inside must reveal no other run's answers.
    parent = os.path.join(RUNROOT, stamp)
    proj = os.path.join(parent, "project")
    if os.path.exists(parent):
        if not args.force:
            die("%s already exists. Pass --force to replace it, or use --label to "
                "name this run differently." % parent)
        shutil.rmtree(parent)
    os.makedirs(proj)

    for want in wants:
        src = os.path.join(FIXTURE, want)
        if want == "PRD.md":
            os.makedirs(os.path.join(proj, "docs"), exist_ok=True)
            shutil.copyfile(src, os.path.join(proj, "docs", "PRD.md"))
        else:
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(proj, item)
                shutil.copytree(s, d) if os.path.isdir(s) else shutil.copyfile(s, d)

    print("scenario : %s — %s" % (args.scenario, label))
    print("project  : %s" % proj)
    print("parent   : %s  (contains only this run)" % parent)
    print("\nGive the agent that path and nothing else. benchmark/README.md has the")
    print("launch rules — fresh agent, follow literally, friction is the output,")
    print("never say what changed.")
    return 0


def find_roadmaps(proj):
    docs = os.path.join(proj, "docs")
    if not os.path.isdir(docs):
        return []
    out = []
    for f in sorted(os.listdir(docs)):
        if f == "ROADMAP.md" or (f.startswith("ROADMAP-") and f != "ROADMAP-INDEX.md"):
            out.append(os.path.join(docs, f))
    idx = os.path.join(docs, "ROADMAP-INDEX.md")
    if os.path.isfile(idx):
        out.append(idx)
    return out


def cmd_score(args):
    proj = os.path.abspath(args.dir)
    if os.path.isdir(os.path.join(proj, "project")):
        proj = os.path.join(proj, "project")
    roadmaps = find_roadmaps(proj)
    if not roadmaps:
        die("no docs/ROADMAP*.md under %s — did the run finish?" % proj, 1)

    corpus = "\n".join(read(p) for p in roadmaps)
    body = corpus.lower()

    print("scoring %s" % proj)
    print("  files: %s\n" % ", ".join(os.path.basename(p) for p in roadmaps))

    found, missing = [], []
    for name, pattern in PLANTED:
        hit = re.search(pattern, body, re.I | re.S) is not None
        (found if hit else missing).append(name)
        print("  %s %s" % ("✓" if hit else "✗", name))

    # A planted ambiguity present as prose but at no destination is not captured.
    # Destinations are: a feature's `open questions`, the roll-up, or a ledger row.
    has_rollup = "## open questions" in body
    has_ledger = "## cross-cutting decisions" in body or any(
        "## cross-cutting decisions" in read(p).lower() for p in roadmaps)
    print("\n  destinations present: roll-up=%s ledger=%s"
          % ("yes" if has_rollup else "NO", "yes" if has_ledger else "NO"))

    lint = subprocess.run(
        [sys.executable, os.path.join(HERE, "check-roadmap.py"), "--root", proj],
        capture_output=True, text=True)
    lastline = [l for l in lint.stdout.strip().splitlines() if "passed" in l]
    print("  check-roadmap: %s" % (lastline[-1] if lastline else "did not report"))

    score = "%d/7" % len(found)
    print("\n  planted ambiguities captured: %s" % score)
    if missing:
        print("  missing: " + ", ".join(missing))
        print("\n  A miss is a regression against benchmark/expected.md. Read that file")
        print("  before changing anything — the destination may have moved with a rule.")

    if args.record:
        record(args.version or skill_version(), args.dir, score, lastline, missing)
        print("\n  appended to benchmark/RESULTS.md")
    return 1 if missing else 0


def skill_version():
    m = re.search(r"^\s*version:\s*\"?([^\"\s]+)", read(os.path.join(REPO, "SKILL.md")), re.M)
    return m.group(1) if m else "unknown"


def record(version, run, score, lintline, missing):
    if not os.path.isfile(RESULTS):
        with open(RESULTS, "w", encoding="utf-8") as fh:
            fh.write("# Benchmark results\n\n"
                     "Appended by `scripts/run-benchmark.py score --record`. Never edit by hand:\n"
                     "a scoreboard someone can rewrite measures nothing.\n\n"
                     "`captured` is out of the seven planted ambiguities in\n"
                     "[`expected.md`](expected.md). A drop is a regression.\n\n"
                     "| date | version | run | captured | linter | missing |\n"
                     "|---|---|---|---|---|---|\n")
    row = "| %s | %s | %s | %s | %s | %s |\n" % (
        datetime.date.today().isoformat(), version, os.path.basename(run.rstrip("/")),
        score, (lintline[-1] if lintline else "—"), ", ".join(missing) if missing else "—")
    with open(RESULTS, "a", encoding="utf-8") as fh:
        fh.write(row)


def cmd_list(args):
    print("scenarios:")
    for k, (label, _) in SCENARIOS.items():
        print("  %-14s %s" % (k, label))
    print("\nruns under %s:" % RUNROOT)
    if os.path.isdir(RUNROOT):
        for d in sorted(os.listdir(RUNROOT)):
            print("  " + d)
    else:
        print("  (none yet)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="create an isolated project for one scenario")
    s.add_argument("scenario")
    s.add_argument("--label", help="name this run (default: the scenario name)")
    s.add_argument("--force", action="store_true", help="replace an existing run")
    s.set_defaults(fn=cmd_setup)

    c = sub.add_parser("score", help="score a finished run against expected.md")
    c.add_argument("dir")
    c.add_argument("--version", help="skill version (default: read from SKILL.md)")
    c.add_argument("--record", action="store_true", help="append to benchmark/RESULTS.md")
    c.set_defaults(fn=cmd_score)

    l = sub.add_parser("list", help="scenarios, and runs on disk")
    l.set_defaults(fn=cmd_list)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
