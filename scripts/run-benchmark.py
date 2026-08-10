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
import json
import os
import re
import shutil
import subprocess
import sys

# Windows consoles default to cp1252, which has no ✓ ✗ ! · or em-dash: printing
# a failure marker raised UnicodeEncodeError and killed the run at exactly the
# moment it had something to report. Reconfiguring is enough — a terminal that
# cannot render a glyph now shows a replacement instead of taking the process
# down with it. Found by the first execution of this project on Windows.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass



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
    # 7 is not a word grep, and cannot be. The run writes prose in the source
    # document's language, so a correct Portuguese answer — "Nada é apagado de
    # verdade: item retirado fica com marca de retirado" — matched no English or
    # cognate pattern and scored as a miss on a roadmap that had done everything
    # right. A false red on the headline metric is as damaging as an empty green:
    # it teaches people to stop reading the number, and invites someone to
    # "repair" correct behaviour. Anchor on what never translates instead — the
    # rubric theme name is a machine-read key and stays English in every language.
    ("7 retention / deletion", None),
]

# The theme #7 must land on, and the row state that means the run never looked.
# Step 7a lets a genuinely inapplicable theme be dismissed with `N/A because`;
# for this PRD it applies — accounts close, C6 withdraws an item, A5 removes a
# person — so `N/A` is the run reading the document instead of enumerating the
# entities it implies, which is exactly what this ambiguity was planted to catch.
LIFECYCLE_THEME = r"data lifecycle"


def lifecycle_row_decided(roadmaps):
    """True when the `Data lifecycle` ledger row exists and is not dismissed."""
    for path in roadmaps:
        for line in read(path).splitlines():
            if not line.strip().startswith("|"):
                continue
            if not re.search(LIFECYCLE_THEME, line, re.I):
                continue
            body = "|".join(line.split("|")[2:])
            if re.search(r"\bN/?A\b", body, re.I):
                return False
            # Strip the dashes a placeholder cell uses, not just spaces and
            # pipes: `| Data lifecycle | | — |` otherwise read as a decision.
            return bool(body.strip(" |-\u2014\u2013\t"))
    return False


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
    if getattr(args, "agents", 1) < 1:
        die("--agents must be at least 1")
    if getattr(args, "agents", 1) > 1:
        return setup_many(args, label, wants)
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

    # What the INPUT already answers, before any agent touches it.
    #
    # cmd_score greps the finished roadmaps for the seven planted ambiguities. On
    # the five input-only scenarios nothing is pre-populated, so every hit is the
    # run's work. A scenario that ships a roadmap already written — which every
    # state scenario in benchmark/state-scenarios.md must — hands cmd_score the
    # answers at setup, and it would print 7/7 and exit 0 whatever the run did.
    # That is the empty green: a gate switching off the attention of whoever
    # reads it. Record the baseline here so the score can subtract it.
    pre = pre_existing_hits(proj)
    save_baseline(stamp, args.scenario, pre)

    print("scenario : %s — %s" % (args.scenario, label))
    print("project  : %s" % proj)
    print("parent   : %s  (contains only this run)" % parent)
    if pre:
        print("baseline : %d of 7 already present in the input — excluded from the"
              % len(pre))
        print("           score: %s" % ", ".join(pre))
    print("\nGive the agent that path and nothing else. benchmark/README.md has the")
    print("launch rules — fresh agent, follow literally, friction is the output,")
    print("never say what changed.")
    return 0


def setup_many(args, label, wants):
    """One freshly created copy per agent, each under its own parent.

    Hand-rolled setups are where isolation fails. Three agents were once given a
    single directory and overwrote each other until the run was unattributable and
    had to be thrown away -- the third time this repository broke its own
    isolation rule, after directory level and file level. Making the right thing
    one flag is worth more than restating the rule a fourth time."""
    base = args.label or args.scenario
    made = []
    for i in range(1, args.agents + 1):
        sub = argparse.Namespace(**vars(args))
        sub.agents = 1
        sub.label = "%s-%d" % (base, i)
        if cmd_setup(sub) != 0:
            return 1
        made.append(os.path.join(RUNROOT, sub.label, "project"))
        print("")
    print("%d isolated copies. Give each agent exactly one of these paths, and never"
          % len(made))
    print("the same one to two agents -- a shared tree does not produce two results,")
    print("it produces none. Score them separately.")
    return 0


# A sibling of RUNROOT, never a child: cmd_list enumerates RUNROOT verbatim, so a
# child appeared in the list as though it were a run — and `setup --label .baselines`
# would then have rmtree'd the whole baseline store on its way to creating it.
BASELINES = RUNROOT + "-baselines"


def pre_existing_hits(proj):
    """Which planted ambiguities the input already contains, before the run."""
    roadmaps = find_roadmaps(proj)
    corpus = "\n".join(read(p) for p in roadmaps).lower()
    if not corpus.strip():
        return []
    return [name for name, pattern in PLANTED
            if (lifecycle_row_decided(roadmaps) if pattern is None
                else re.search(pattern, corpus, re.I | re.S))]


def save_baseline(stamp, scenario, hits):
    os.makedirs(BASELINES, exist_ok=True)
    # Outside the run's parent on purpose. The parent holds one run and nothing
    # else so that `ls ..` from inside reveals no answers — and a file naming
    # which ambiguities are already present is exactly such an answer.
    with open(os.path.join(BASELINES, stamp + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"scenario": scenario, "pre_existing": hits}, fh, indent=2)


def load_baseline(rundir):
    """Baseline for a run directory, or None when setup never recorded one."""
    d = os.path.abspath(rundir).rstrip(os.sep)
    if os.path.basename(d) == "project":
        d = os.path.dirname(d)
    path = os.path.join(BASELINES, os.path.basename(d) + ".json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


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

    base = load_baseline(args.dir)
    if base is None:
        print("  ! no setup baseline recorded for this run — every hit below is")
        print("    being credited to the run. That is right only if the scenario")
        print("    started from input with no roadmap in it.\n")
        pre = []
    else:
        pre = base.get("pre_existing") or []

    # A pattern the input already carried proves nothing about the run.
    scored = [(n, p) for n, p in PLANTED if n not in pre]
    if not scored:
        die("all seven planted ambiguities were already present in this scenario's "
            "input, so this score would measure nothing. Give the state scenarios "
            "their own scorer rather than reusing the seven-ambiguity grep.", 2)

    found, missing = [], []
    for name, pattern in scored:
        hit = (lifecycle_row_decided(roadmaps) if pattern is None
               else re.search(pattern, body, re.I | re.S) is not None)
        (found if hit else missing).append(name)
        print("  %s %s" % ("✓" if hit else "✗", name))
    for name in pre:
        print("  · %s (present in the input — not scored)" % name)

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

    # Multi-section decomposition is lazy by design: a correct run may cover one
    # section and leave the rest `NOT YET DECOMPOSED`. Its planted ambiguities
    # then live in sections nobody has reached, and grading that as a miss calls
    # correct behaviour a regression — the empty green pointed the other way, and
    # just as good at teaching people to stop reading the number.
    pending = []
    idx = os.path.join(proj, "docs", "ROADMAP-INDEX.md")
    for line in read(idx).splitlines():
        if "NOT YET DECOMPOSED" in line.upper() and line.strip().startswith("-"):
            pending.append(line.strip().lstrip("- ").split("—")[0].strip())
    if pending:
        print("\n  PARTIAL — %d section(s) not yet decomposed:" % len(pending))
        for p in pending:
            print("    %s" % p)
        print("  Ambiguities belonging to those sections cannot have been placed yet,")
        print("  so this score is not comparable with a fully decomposed run.")

    score = "%d/%d" % (len(found), len(scored))
    print("\n  planted ambiguities captured: %s" % score)
    if missing:
        print("  missing: " + ", ".join(missing))
        print("\n  A miss is a regression against benchmark/expected.md. Read that file")
        print("  before changing anything — the destination may have moved with a rule.")

    if args.record and pending:
        # A partial run on the scoreboard reads as a regression forever after.
        print("\n  NOT recorded: a partially decomposed run does not belong on the")
        print("  scoreboard. Decompose the remaining sections and score again.")
    elif args.record:
        record(args.version or skill_version(), args.dir, score, lastline, missing)
        print("\n  appended to benchmark/RESULTS.md")
    return 1 if (missing and not pending) else 0


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
    s.add_argument("--agents", type=int, default=1,
                   help="create this many isolated copies, one per agent — never give "
                        "two agents the same tree")
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
