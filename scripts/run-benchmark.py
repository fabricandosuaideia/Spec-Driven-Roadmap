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
import hashlib
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
    # The three that need a project with a PAST. Each is the frozen `state/`
    # tree plus a small overlay: a wave-2 source and a clean Handoff for the
    # re-run, nothing for the other two, which differ only in what the run is
    # asked to do with the same disk.
    "state-rerun": ("existing roadmap, a new wave arrives", ["state:state-rerun"]),
    "state-inflight": ("existing roadmap, work in flight", ["state:state-inflight"]),
    "state-conversion": ("oversize single-section, names frozen on disk", ["state:state-conversion"]),
    # The loop prompt's own fixture, wired here so the downstream skill actually
    # gets installed. Its `use the downstream skill` branch went unexercised
    # through nine runs for no better reason than the fixture having no
    # `.claude/skills/` — which the .gitignore forbids shipping, so it has to
    # happen at setup or not at all.
    "loop-build": ("the loop prompt's project, with a test that cannot pass", ["loop-fixture"]),
}

# Scenarios that must NOT get the downstream skill: their whole point is the
# branch this skill takes when none is installed.
NO_DOWNSTREAM = {"0b-interview"}

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
        if want.startswith("state:"):
            # The shared past, then the scenario's overlay on top of it. Copying
            # base-then-overlay rather than keeping three full trees is what stops
            # a fix landing in one and not the others — the drift this repository
            # commits most often, applied to its own fixtures.
            copy_tree(os.path.join(FIXTURE, "state"), proj)
            copy_tree(os.path.join(FIXTURE, want.split(":", 1)[1]), proj)
            continue
        if want == "loop-fixture":
            copy_tree(os.path.join(REPO, "benchmark", "loop-fixture"), proj)
            os.remove(os.path.join(proj, "README.md"))
            continue
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
    installed = install_skills(proj, args.scenario)

    if any(w.startswith("state:") for w in wants) or "loop-fixture" in wants:
        git_init(proj)
        os.makedirs(BASELINES, exist_ok=True)
        with open(os.path.join(BASELINES, stamp + ".snapshot.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(snapshot(proj), fh, indent=2)

    pre = pre_existing_hits(proj)
    save_baseline(stamp, args.scenario, pre)

    print("scenario : %s — %s" % (args.scenario, label))
    print("project  : %s" % proj)
    print("parent   : %s  (contains only this run)" % parent)
    print("skills   : %s" % installed)
    if pre:
        print("baseline : %d of 7 already present in the input — excluded from the"
              % len(pre))
        print("           score: %s" % ", ".join(pre))
    print("\nGive the agent that path and nothing else. benchmark/README.md has the")
    print("launch rules — fresh agent, follow literally, friction is the output,")
    print("never say what changed.")
    return 0


def snapshot(proj):
    """What the tree looked like before the agent touched it.

    The state scenarios are scored by comparison, not by grep: the question is
    never "does a word appear" but "did the run extend this without disturbing
    what was already built". A grep cannot tell an extension from a rewrite.
    """
    roadmaps = find_roadmaps(proj)
    heads, txt = [], {}
    for path in roadmaps:
        heads += re.findall(r"^###\s+`?([\w.-]+)`?\s*$", read(path), re.M)
    docs = os.path.join(proj, "docs")
    if os.path.isdir(docs):
        for f in sorted(os.listdir(docs)):
            if f.endswith(".txt"):
                txt[f] = [l.strip() for l in read(os.path.join(docs, f)).splitlines() if l.strip()]
    state = read(os.path.join(proj, ".specs", "STATE.md"))
    decisions = ""
    m = re.search(r"^##\s+Decisions\s*$(.*?)(?=^##\s|\Z)", state, re.M | re.S)
    if m:
        decisions = m.group(1).strip()
    feats = os.path.join(proj, ".specs", "features")
    return {
        "headings": heads,
        "txt": txt,
        "roadmap_files": sorted(os.path.basename(p) for p in roadmaps),
        "state_sha": hashlib.sha256(state.encode()).hexdigest(),
        "decisions_sha": hashlib.sha256(decisions.encode()).hexdigest(),
        "feature_dirs": sorted(os.listdir(feats)) if os.path.isdir(feats) else [],
    }


def copy_tree(src, dst):
    """Merge src into dst, overwriting files and keeping what is already there."""
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        out = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(out, exist_ok=True)
        for f in files:
            if f == ".keep":
                continue
            shutil.copyfile(os.path.join(root, f), os.path.join(out, f))


def install_skills(proj, scenario):
    """Put the skill under test, and its downstream, inside the run.

    Every run this session needed this and every one of them got it by hand,
    which is where setup mistakes come from -- a run scored against a project
    that had no skill in it measures the agent's improvisation, not the skill.
    Installing into the project rather than globally is also how this is used for
    real: one version per repository, nothing shared between them.
    """
    dest = os.path.join(proj, ".claude", "skills", "spec-driven-roadmap")
    os.makedirs(os.path.join(dest, "scripts"), exist_ok=True)
    shutil.copyfile(os.path.join(REPO, "SKILL.md"), os.path.join(dest, "SKILL.md"))
    copy_tree(os.path.join(REPO, "references"), os.path.join(dest, "references"))
    for name in ("check-roadmap.py", "convert-to-multi.py"):
        shutil.copyfile(os.path.join(REPO, "scripts", name),
                        os.path.join(dest, "scripts", name))

    if scenario in NO_DOWNSTREAM:
        return "spec-driven-roadmap only (this scenario tests the no-downstream branch)"

    vendored = os.path.join(REPO, ".claude", "skills")
    got = []
    for name in ("tlc-spec-driven", "not-your-babysitter"):
        src = os.path.join(vendored, name)
        if os.path.isdir(src):
            copy_tree(src, os.path.join(proj, ".claude", "skills", name))
            got.append(name)
    if "tlc-spec-driven" not in got:
        print("! no downstream skill at %s — a run without one takes the "
              "\"no downstream skill installed\" branch, which is a different "
              "test. See CONTRIBUTING.md." % vendored)
    return ", ".join(["spec-driven-roadmap"] + got)


def git_init(proj):
    """One commit, made here rather than stored.

    state-scenarios.md asks for it, and it is what makes the scenarios' central
    assertions mechanical: `git diff --exit-code -- .specs/STATE.md` is the whole
    work-in-flight test, and the conversion's `git mv` and `--rollback` paths have
    never run against a tree with history.
    """
    env = dict(os.environ, GIT_AUTHOR_NAME="benchmark", GIT_AUTHOR_EMAIL="b@example.invalid",
               GIT_COMMITTER_NAME="benchmark", GIT_COMMITTER_EMAIL="b@example.invalid")
    for cmd in (["init", "-q", "."], ["add", "-A"], ["commit", "-qm", "fixture"]):
        r = subprocess.run(["git"] + cmd, cwd=proj, env=env,
                           capture_output=True, text=True)
        if r.returncode != 0:
            die("git %s failed in the fixture: %s" % (cmd[0], r.stderr.strip()))


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


def load_snapshot(rundir):
    d = os.path.abspath(rundir).rstrip(os.sep)
    if os.path.basename(d) == "project":
        d = os.path.dirname(d)
    path = os.path.join(BASELINES, os.path.basename(d) + ".snapshot.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def score_state(proj, scenario, before):
    """Score a scenario that started from a project with a past.

    Every assertion here is a comparison against `before`. What these scenarios
    are for is the behaviour no input-only run can reach -- extending a roadmap
    without disturbing built work, refusing to overwrite a paused session,
    deriving a slug rather than choosing one -- and none of that is visible to
    the seven-ambiguity grep, which is why that scorer refuses them outright.
    """
    now = snapshot(proj)
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, ok, detail))

    # -- shared: built work is never disturbed, whatever the scenario asked for
    kept = [h for h in before["headings"] if h in now["headings"]]
    ck("every feature the roadmap already named survives",
       len(kept) == len(before["headings"]),
       "gone: " + ", ".join(h for h in before["headings"] if h not in now["headings"]))
    ck("their relative order is unchanged",
       kept == [h for h in now["headings"] if h in before["headings"]],
       "order moved")
    ck("no feature was renamed",
       set(before["feature_dirs"]) <= set(now["feature_dirs"]),
       "directories that vanished: "
       + ", ".join(sorted(set(before["feature_dirs"]) - set(now["feature_dirs"]))))
    ck("`## Decisions` was not touched",
       now["decisions_sha"] == before["decisions_sha"],
       "the downstream skill owns that block and this skill never writes it")

    if scenario == "state-rerun":
        # The scenario tests a FORK, and both answers are the user's to give:
        # extend the existing roadmap, or give the wave its own section. An
        # earlier version of this scorer asserted the extend branch outright and
        # failed a correct run that took the other one — grading the simulated
        # user's answer instead of the skill's behaviour, which is the same false
        # red this repository has now committed at three different layers.
        converted = any(f.startswith("ROADMAP-") and f != "ROADMAP-INDEX.md"
                        for f in now["roadmap_files"])
        print("  disposition: %s" % ("own section (converted)" if converted else "extended in place"))

        # The build order survives either way — under its own name, or under the
        # name the conversion renamed it to.
        for f, lines in before["txt"].items():
            after = now["txt"].get(f)
            if after is None and converted:
                cands = [v for k, v in now["txt"].items() if v[:len(lines)] == lines]
                after = cands[0] if cands else []
            ck("the pre-run build order survives in full and in order",
               (after or [])[:len(lines)] == lines,
               "%s: the pre-run order is not a prefix of any post-run .txt" % f)

        if converted:
            ck("the conversion produced an index",
               "ROADMAP-INDEX.md" in now["roadmap_files"], "")
            ck("the new wave got a section of its own",
               sum(1 for f in now["roadmap_files"]
                   if f.startswith("ROADMAP-") and f != "ROADMAP-INDEX.md") >= 2,
               "only one section roadmap exists, so the wave did not get its own")
        else:
            ck("nothing was converted behind the user's back",
               "ROADMAP-INDEX.md" not in now["roadmap_files"],
               "an index appeared although the answer was to extend in place")

        ck("the new wave actually landed",
           len(now["headings"]) > len(before["headings"]),
           "no feature was added — the wave-2 source produced nothing")

    if scenario == "state-inflight":
        ck("`.specs/STATE.md` was not rewritten",
           now["state_sha"] == before["state_sha"],
           "rule 11: a paused session's Handoff is never overwritten")
        status = ""
        for path in find_roadmaps(proj):
            m = re.search(r"^##\s+Status\s*$(.*?)(?=^##\s|\Z)", read(path), re.M | re.S)
            if m:
                status += m.group(1)
        ck("`## Status` records the work in flight",
           re.search(r"not rewritten this run", status, re.I) is not None,
           "the Status block never says the Handoff was left alone")

    if scenario == "state-conversion":
        sections = [f for f in now["roadmap_files"] if f.startswith("ROADMAP-")
                    and f != "ROADMAP-INDEX.md"]
        ck("the roadmap was converted", bool(sections), "no ROADMAP-<slug>.md exists")
        ck("an index was written", "ROADMAP-INDEX.md" in now["roadmap_files"], "")
        names = next(iter(before["txt"].values()), [])
        prefix = os.path.commonprefix(names).rstrip("-") if names else ""
        ck("the slug was DERIVED from the frozen prefix, not chosen",
           bool(prefix) and any(f == "ROADMAP-%s.md" % prefix for f in sections),
           "expected ROADMAP-%s.md from prefix %r, found %s"
           % (prefix, prefix, ", ".join(sections) or "nothing"))

    print("")
    failed = 0
    for name, ok, detail in checks:
        print("  %s %s" % ("✓" if ok else "✗", name))
        if not ok and detail:
            print("      " + detail)
        failed += 0 if ok else 1
    print("\n  %d passed, %d failed" % (len(checks) - failed, failed))
    return 1 if failed else 0


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
    if base and str(base.get("scenario", "")).startswith("state-"):
        print("scoring %s" % proj)
        print("  scenario : %s — compared against the tree as it was at setup"
              % base["scenario"])
        snap = load_snapshot(args.dir)
        if snap is None:
            die("no setup snapshot for this run — a state scenario is scored by "
                "comparison, so it cannot be scored without one. Re-run setup.", 2)
        return score_state(proj, base["scenario"], snap)

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


def cmd_clean(args):
    """Remove finished run trees, so the next test cannot inherit one.

    Leftovers are how a test session contaminates the next: a stale tree gets
    reused, an agent reads a previous run's answers, or a score is taken from a
    directory nobody created for it. Scored runs have already deposited their
    numbers in RESULTS.md, so the tree itself is spent — but deleting is not
    guessing, so this lists what it will remove and needs --yes to do it."""
    targets = []
    for root in (RUNROOT, BASELINES):
        if os.path.isdir(root):
            targets.append(root)
    if not targets:
        print("nothing to clean — no run trees on disk")
        return 0
    print("would remove:")
    total = 0
    for t in targets:
        n = sum(len(f) for _, _, f in os.walk(t))
        total += n
        print("  %s  (%d files)" % (t, n))
    if not args.yes:
        print("\nNothing was removed. Pass --yes to do it.")
        print("Keep a tree only when you mean to — say why, out loud, in the same breath.")
        return 0
    for t in targets:
        shutil.rmtree(t, ignore_errors=True)
    print("\nremoved %d files. The next run starts from a tree it created itself." % total)
    return 0


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

    cl = sub.add_parser("clean", help="remove finished run trees so the next test cannot inherit one")
    cl.add_argument("--yes", action="store_true", help="actually remove them")
    cl.set_defaults(fn=cmd_clean)

    l = sub.add_parser("list", help="scenarios, and runs on disk")
    l.set_defaults(fn=cmd_list)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
