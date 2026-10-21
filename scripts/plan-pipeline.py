#!/usr/bin/env python3
"""Print the args for roadmap-pipeline.js: which features of one roadmap are still to build, and how.

Why this exists: a pipeline run spends the owner's quota for hours, and three of its inputs
must never be guessed. WHICH features are pending is decided by the downstream skill's own
completion gate, the same one the seed trusts — never by a report merely existing. HOW MUCH
verification each gets is the feature's risk tier, derived by the rule check-roadmap.py uses.
And the GATE COMMAND is the pipeline's authority on "done"; a command this script guessed
would make every PASS a guess, so it reads it from docs/process/pipeline.json and refuses until
a person has confirmed it there.

`gate` is what every feature must pass before it merges. A project that runs its whole suite only
at a batch barrier (its feature gate being the affected tests) sets `barrierGate` too: the pipeline
runs it on the merged main branch every `barrierEvery` merges (0 = once, at the end), and a red
barrier stops every later merge. `model` sets the model of every agent the pipeline starts; left
null they inherit the session's, which is how a run went out on a model nobody chose.

    python3 plan-pipeline.py --root <project> --init          # write pipeline.json to confirm
    python3 plan-pipeline.py --root <project> [--roadmap docs/ROADMAP-x.md] > args.json
    python3 plan-pipeline.py --root <project> --manager > args.json   # manager mode: every section
    python3 plan-pipeline.py --selftest

`--manager` (references/manager-mode.md) prints the args of scripts/manager-pipeline.js instead: every
section of docs/ROADMAP-INDEX.md in build order — read from its `## Roadmaps` table and `## Ordering`
list, never guessed — with whether it is decomposed and which of its features are still to build. It
refuses unless pipeline.json carries the owner's written delegation (`manager.delegation`): in that
mode the manager decides what would otherwise be asked, and only the owner can hand that over.

A feature that did not finish a run keeps its git worktree, and its lane: lanes are balanced once, and
after that the worktree git reports is the truth (`worktree` in the feature's args). The last green
barrier is recorded inside the git directory (record-barrier.py, which the barrier agent runs on a
green exit); code on the main branch after it makes the barrier owed, so a run paused inside its
barrier is not followed by one that builds on a main branch nobody proved (`barrierPending`).

One roadmap per run, as for the loop: across roadmaps, producer names are provisional until a
section is decomposed, and the seam between sections is where a person re-seeds.

Exit codes: 0 printed (or config written), 1 refused (unconfirmed config, nothing pending, a
gate that could not be run) or --selftest failed, 2 usage.
"""

import argparse
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
CONFIG = os.path.join("docs", "process", "pipeline.json")
PROFILES = {  # downstream skill -> (report, completion gate script)
    "tlc-spec-lean": ("verification.md", "validate_verification.py"),
    "tlc-spec-driven": ("validation.md", "validate_state.py"),
}
DEFAULT_CONFIG = {
    "confirmed": False,
    "gate": "",
    "barrierGate": None,
    "barrierEvery": 0,
    "gateOrder": "gate-first",
    "mergeGate": "rerun",
    "verifier": {"sensor": None, "survivor": None, "rounds": "scoped"},
    "model": None,
    "testHint": "",
    "setup": "",
    "push": False,
    "mainBranch": "main",
    "lanes": 1,
    "checklist": None,
    "effort": {"implement": {"A": "xhigh", "B": "high", "C": "medium"}, "prove": "medium",
               "verify": {"A": "high", "B": "high", "C": "medium"}, "review": "high",
               "merge": "medium", "record": "low"},
    "maxAttempts": {"A": 5, "B": 4, "C": 3},
    "manager": {"delegation": "", "delegatedOn": "", "autonomy": "decide", "stopAt": [], "sectionsPerRun": 4,
                "decomposeModel": None, "effort": {"decompose": "xhigh", "plan": "low", "final": "medium"}},
}


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CR = _load("check_roadmap", "check-roadmap.py")


def detect_gate(root):
    """A first guess for pipeline.json, always written unconfirmed."""
    pkg = os.path.join(root, "package.json")
    if os.path.isfile(pkg):
        try:
            scripts = json.load(open(pkg, encoding="utf-8")).get("scripts", {})
        except ValueError:
            scripts = {}
        runner = "pnpm" if os.path.isfile(os.path.join(root, "pnpm-lock.yaml")) else "npm run"
        parts = ["%s %s" % (runner, s) for s in ("typecheck", "lint", "test") if s in scripts]
        if parts:
            return " && ".join(parts)
    if os.path.isfile(os.path.join(root, "pyproject.toml")) or glob.glob(os.path.join(root, "tests", "test_*.py")):
        return "python3 -m pytest -q"
    if os.path.isfile(os.path.join(root, "Makefile")):
        return "make test"
    return ""


def git(root, *argv):
    r = subprocess.run(["git", "-C", root] + list(argv), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def detect_main(root):
    """The branch features merge into: `main` or `master` if one exists, else the current one."""
    for name in ("main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", "refs/heads/" + name) is not None:
            return name
    return git(root, "branch", "--show-current") or "main"


def feature_worktrees(root):
    """{branch: path} for every worktree git lists whose directory still exists.

    The lanes are not the truth about where a feature lives, the worktree is: a feature that did not
    finish a run keeps its worktree, and git refuses to check its branch out a second time."""
    here = os.path.realpath(root)
    found, path, branch, prunable = {}, None, None, False
    for line in (git(root, "worktree", "list", "--porcelain") or "").splitlines() + [""]:
        if line.startswith("worktree "):
            path, branch, prunable = line[len("worktree "):], None, False
        elif line.startswith("branch refs/heads/"):
            branch = line[len("branch refs/heads/"):]
        elif line.startswith("prunable"):
            prunable = True
        elif not line and path:
            if branch and not prunable and os.path.isdir(path) and os.path.realpath(path) != here:
                found[branch] = path
            path = None
    return found


BARRIER_FILE = "spec-driven-roadmap-barrier.json"


def barrier_state_path(root):
    """Where the last green barrier is kept: inside the git directory, so it is no commit, moves no
    HEAD, is shared by every worktree and is never merged into anything."""
    return os.path.join(root, git(root, "rev-parse", "--git-common-dir") or ".git", BARRIER_FILE)  # absolute stays


def record_barrier(root, main_branch, sha):
    """Record that the barrier passed on `sha`. Refuses a commit the main branch does not contain."""
    full = git(root, "rev-parse", "--verify", "--quiet", sha + "^{commit}")
    if full is None:
        raise RuntimeError("%s is not a commit of this repository" % sha)
    if subprocess.run(["git", "-C", root, "merge-base", "--is-ancestor", full, "refs/heads/" + main_branch],
                      capture_output=True).returncode != 0:
        raise RuntimeError("%s is not on %s: a barrier proves a commit of the main branch" % (sha, main_branch))
    path = barrier_state_path(root)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump({"main": main_branch, "sha": full}, fh)
    os.replace(path + ".tmp", path)
    return full


def barrier_pending(root, cfg):
    """{"base", "head"} when code reached the main branch after the last green barrier, else None.

    Only a project with a barrierGate has one, and only once a barrier has been recorded: with no record
    the state is unknown, and guessing a base for the triage would be worse than not running."""
    if not cfg.get("barrierGate"):
        return None
    main_branch = cfg.get("mainBranch") or "main"
    path = barrier_state_path(root)
    if not os.path.isfile(path):
        return None
    try:
        state = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        raise RuntimeError("%s exists but cannot be read: delete it once you know the current %s passes the barrier "
                           "gate (an unreadable record is not the same as no record)" % (path, main_branch))
    if not isinstance(state, dict):
        raise RuntimeError("%s is not a record: delete it, as above" % path)
    if state.get("main") != main_branch or not state.get("sha"):
        return None
    head = git(root, "rev-parse", "refs/heads/" + main_branch)
    if head is None or head == state["sha"]:
        return None
    if subprocess.run(["git", "-C", root, "merge-base", "--is-ancestor", state["sha"], head],
                      capture_output=True).returncode != 0:
        raise RuntimeError("the last green barrier, %s, is not an ancestor of %s: the main branch was rewritten. "
                           "Delete %s once you know the current %s passes the barrier gate"
                           % (state["sha"][:9], main_branch, barrier_state_path(root), main_branch))
    code = git(root, "diff", "--name-only", state["sha"], head, "--", ".", ":!docs", ":!.specs")
    return {"base": state["sha"], "head": head} if code else None


def downstream(root):
    for name in ("tlc-spec-lean", "tlc-spec-driven"):
        d = os.path.join(root, ".claude", "skills", name)
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            return name, d
    return None, None


def is_done(root, ds, ds_dir, name):
    """Done means the downstream gate says so; a missing directory is not done (no gate is run)."""
    if not os.path.isdir(os.path.join(root, ".specs", "features", name)):
        return False
    gate = os.path.join(ds_dir, "scripts", PROFILES[ds][1])
    if not os.path.isfile(gate):
        raise RuntimeError("%s has no %s; this script will not guess which features are done" % (ds, PROFILES[ds][1]))
    r = subprocess.run([sys.executable, gate, name, "--root", root], cwd=os.path.join(ds_dir, "scripts"),
                       capture_output=True, text=True)
    return r.returncode == 0


def deps_of(fields):
    dep = CR.field(fields, "depends on", "depends") or ""
    return re.findall(r"`?([a-z0-9]+(?:-[a-z0-9]+)+)`?", dep)


OWNER_WORDS = ("done", "build")


def classify(root, ds, ds_dir, entries, order, cfg, roadmap_rel):
    """(done, pending, discharged, doubtful) for one roadmap's build order.

    The downstream gate decides, except where it cannot: a feature whose report exists but that the
    gate refuses (a real FAIL, or a PASS written in a shape the script does not read), and a feature
    still "pending" that a finished feature depends on (which cannot be). On a real project seven
    such features sat in two closed sections, and an unattended run would have rebuilt all of them.
    Those are the owner's to classify, in pipeline.json's `featureStatus` ("done" or "build"); until
    then they are doubtful, and nothing plans around them."""
    owner = cfg.get("featureStatus") or {}
    bad = sorted(k for k, v in owner.items() if v not in OWNER_WORDS)
    if bad:
        raise RuntimeError("%s featureStatus takes \"done\" or \"build\"; not: %s" % (CONFIG, ", ".join(bad)))
    done, pending, discharged = [], [], []
    for name in order:
        fields = entries.get(name)
        if fields is None:
            raise RuntimeError("%s is in the build order but has no entry in %s" % (name, roadmap_rel))
        said = owner.get(name)
        if CR.field(fields, "discharge"):
            discharged.append(name)
        elif said == "done" or (said != "build" and is_done(root, ds, ds_dir, name)):
            done.append(name)
        else:
            pending.append(name)
    report = PROFILES[ds][0]
    doubtful = {}
    for name in pending:
        if owner.get(name) == "build":
            continue
        if os.path.isfile(os.path.join(root, ".specs", "features", name, report)):
            doubtful[name] = "has a %s the gate refuses" % report
            continue
        needers = [d for d in done if name in deps_of(entries[d])]
        if needers:
            doubtful[name] = "finished feature %s depends on it" % needers[0]
    return done, pending, discharged, doubtful


def doubtful_message(doubtful):
    return ("%d feature(s) the downstream gate cannot decide — classify each in %s \"featureStatus\" as "
            "\"done\" or \"build\" before an unattended run builds around it: %s"
            % (len(doubtful), CONFIG, "; ".join("%s (%s)" % kv for kv in sorted(doubtful.items()))))


def plan(root, roadmap_rel, cfg):
    ds, ds_dir = downstream(root)
    if not ds:
        raise RuntimeError("no tlc-spec-lean or tlc-spec-driven under %s/.claude/skills" % root)
    roadmap = os.path.join(root, roadmap_rel)
    txt = os.path.join(root, "docs", "roadmap.txt") if os.path.basename(roadmap) == "ROADMAP.md" else \
        os.path.join(root, "docs", "roadmap-%s.txt" % os.path.basename(roadmap)[len("ROADMAP-"):-len(".md")])
    order = CR.txt_names(txt)
    if not order:
        raise RuntimeError("no build order at %s" % os.path.relpath(txt, root))
    with open(roadmap, encoding="utf-8") as fh:
        text = fh.read()
    entries = {n: f for n, f, _b in CR.parse_features(text)}
    status = os.path.join("docs", "ROADMAP-INDEX.md") if os.path.isfile(os.path.join(root, "docs", "ROADMAP-INDEX.md")) \
        else os.path.join("docs", "ROADMAP.md")
    validate_config(cfg, ds)
    done, pending, discharged, doubtful = classify(root, ds, ds_dir, entries, order, cfg, roadmap_rel)
    if doubtful:
        raise RuntimeError(doubtful_message(doubtful))
    lanes = max(1, int(cfg.get("lanes") or 1))
    lane_of, load = {}, {n: 0 for n in range(1, lanes + 1)}
    # a feature with a worktree keeps it, and its lane: counted first, so the rest balance around it
    trees = feature_worktrees(root)
    if lanes == 1:
        stray = sorted(n for n in pending if "feat/" + n in trees)
        if stray:
            raise RuntimeError("lanes is 1, but %s still has a worktree from a run with more lanes (%s): git refuses to "
                               "check a branch out in two places. Finish it with lanes above 1, or remove it "
                               "(git worktree remove <path>, after saving what is in it)" % (stray[0], trees["feat/" + stray[0]]))
        trees = {}
    elif any(git(root, "branch", "--show-current") == "feat/" + n for n in pending):
        raise RuntimeError("the project root is on %s, a feature to build, and lanes is above 1: every lane builds in its "
                           "own worktree and git refuses the branch twice. Check out %s in the root first"
                           % (git(root, "branch", "--show-current"), cfg.get("mainBranch") or "main"))
    kept = {}
    for name in pending:
        path = trees.get("feat/" + name)
        if path:
            m = re.search(r"/lane(\d+)/[^/]+$", path.replace(os.sep, "/"))
            lane = int(m.group(1)) if m and 1 <= int(m.group(1)) <= lanes else None
            kept[name] = (path, lane)
            if lane:
                load[lane] += 1
    feats = []
    for name in pending:
        fields = entries[name]
        floor, _why = CR.derive_tier(fields)
        stated, _r = CR.stated_tier(fields)
        tier = stated if stated and CR.TIER_RANK[stated] >= CR.TIER_RANK[floor] else floor
        deps = [d for d in deps_of(fields) if d in pending and d != name]
        first = next((lane_of[d] for d in deps if d in lane_of), None)
        keeps = kept.get(name, (None, None))[1]
        lane = keeps or first or min(load, key=lambda k: (load[k], k))
        lane_of[name] = lane
        if not keeps:
            load[lane] += 1
        feats.append({"name": name, "roadmap": roadmap_rel, "tier": tier, "dependsOn": deps, "lane": lane})
        if name in kept:
            feats[-1]["worktree"] = kept[name][0]
    args = {
        "project": root, "skillDir": SKILL_DIR, "downstream": ds, "downstreamDir": ds_dir,
        "statusPath": status, "mainBranch": cfg.get("mainBranch") or "main", "gate": cfg["gate"],
        "barrierGate": (cfg.get("barrierGate") or "").strip() or None, "barrierEvery": int(cfg.get("barrierEvery") or 0),
        "model": cfg.get("model") or None, "gateOrder": cfg.get("gateOrder") or "gate-first", "mergeGate": cfg.get("mergeGate") or "rerun",
        "verifier": verifier_policy(cfg),
        **({"models": models_policy(cfg)} if models_policy(cfg) else {}),
        "testHint": cfg.get("testHint") or "", "setup": cfg.get("setup") or "", "push": bool(cfg.get("push")),
        "lanes": lanes, "worktreeRoot": root.rstrip("/") + ".lanes", "checklist": cfg.get("checklist"),
        "effort": cfg.get("effort") or DEFAULT_CONFIG["effort"],
        "maxAttempts": cfg.get("maxAttempts") or DEFAULT_CONFIG["maxAttempts"], "features": feats,
    }
    if cfg.get("waitChunk"):  # seconds per wait on a detached gate; only tests set it lower
        args["waitChunk"] = int(cfg["waitChunk"])
    owed = barrier_pending(root, cfg)
    if owed:
        args["barrierPending"] = owed
    return args, {"done": done, "discharged": discharged, "pending": pending, "downstream": ds}


SLUG_RE = re.compile(r"`?docs/ROADMAP-([A-Za-z0-9][\w-]*)\.md`?")


AUTONOMY = ("decide", "unblock")
GATE_ORDERS = ("gate-first", "verify-first")
MERGE_GATES = ("rerun", "receipt")
SURVIVOR_SEVERITIES = ("blocker", "major", "minor")
ROUND_MODES = ("scoped", "full")
TIERS = ("A", "B", "C")
MODEL_ROLES = ("build", "prove", "verify", "review", "merge", "record", "triage", "barrier")
VERIFIER_KEYS = ("sensor", "survivor", "rounds")
# Keys of `manager` that mean something. A key outside this list was silently ignored before 3.41.0, which
# is how a setting that does nothing gets trusted: "passes" was a local patch of one project, and is
# refused by name because ignoring it would let its owner believe a second pass happens.
MANAGER_KEYS = ("delegation", "delegatedOn", "autonomy", "stopAt", "sectionsPerRun", "decomposeModel", "effort")
MANAGER_EFFORT_KEYS = ("decompose", "plan", "final")


def _whole(n, least):
    return isinstance(n, int) and not isinstance(n, bool) and n >= least


def config_problems(cfg, ds=None):
    """Every problem with the pipeline.json values this script reads, as a list of sentences — each starts with
    the key it is about. A value that is present but falsy (0, false, "", [], {}) is a problem, not an absence:
    only a missing key or null means "unset". `ds` is the downstream skill, when known."""
    out = []

    def given(d, k):
        return isinstance(d, dict) and d.get(k) is not None

    def one_of(d, k, allowed, label):
        if given(d, k) and d[k] not in allowed:
            out.append("%s takes %s; not: %r" % (label, " or ".join(allowed), d[k]))
    one_of(cfg, "gateOrder", GATE_ORDERS, "gateOrder")
    one_of(cfg, "mergeGate", MERGE_GATES, "mergeGate")
    for key in ("barrierEvery", "lanes"):
        if given(cfg, key) and not _whole(cfg[key], 0 if key == "barrierEvery" else 1):
            out.append("%s takes a whole number%s; not: %r" % (key, " (0 = once, at the end)" if key == "barrierEvery" else " of at least 1", cfg[key]))
    if cfg.get("mergeGate") == "receipt":
        if not (isinstance(cfg.get("barrierGate"), str) and cfg["barrierGate"].strip()):
            out.append("mergeGate \"receipt\" needs a barrierGate: the receipt is written by an agent, and the barrier is the one run "
                       "of the project's checks that nobody's word stands in for")
        if not _whole(cfg.get("barrierEvery"), 1):
            out.append("mergeGate \"receipt\" needs barrierEvery of at least 1: with 0 the barrier runs once, at the end, and a run that "
                       "stops early would leave receipt-merged features that no barrier ever ran on")
    v = cfg.get("verifier")
    if v is not None and not isinstance(v, dict):
        out.append("verifier takes an object: {\"sensor\": {\"A\": n, \"B\": n, \"C\": n}, \"survivor\": ..., \"rounds\": ...}; not: %r" % (v,))
    elif isinstance(v, dict):
        stray = sorted(k for k in v if k not in VERIFIER_KEYS)
        if stray:
            out.append("verifier has no key %s; the keys are %s" % (", ".join(stray), ", ".join(VERIFIER_KEYS)))
        if given(v, "sensor"):
            sen = v["sensor"]
            if not isinstance(sen, dict):
                out.append("verifier.sensor takes an object of mutant caps per tier, such as {\"A\": 5, \"B\": 3}; not: %r" % (sen,))
            else:
                badtier = sorted(k for k in sen if k not in TIERS)
                badnum = sorted(k for k, n in sen.items() if k in TIERS and not _whole(n, 1))
                if badtier:
                    out.append("verifier.sensor has no tier %s; the tiers are A, B and C" % ", ".join(badtier))
                if badnum:
                    out.append("verifier.sensor.%s must be a whole number of at least 1 (a tier it does not name has no cap)" % ", ".join(badnum))
        one_of(v, "survivor", SURVIVOR_SEVERITIES, "verifier.survivor")
        one_of(v, "rounds", ROUND_MODES, "verifier.rounds")
        if v.get("survivor") == "minor" and ds == "tlc-spec-lean":
            out.append("verifier.survivor \"minor\" cannot be used with tlc-spec-lean (the downstream here, because it is installed: "
                       "when both skills are installed tlc-spec-lean is the one used): its completion gate refuses a PASS written above "
                       "a surviving mutant. Cap the mutants instead, or install only tlc-spec-driven")
    m = cfg.get("models")
    if m is not None and not isinstance(m, dict):
        out.append("models takes an object: {\"build\": \"<model>\", ...}; not: %r" % (m,))
    elif isinstance(m, dict):
        bad = sorted(k for k in m if k not in MODEL_ROLES)
        if bad:
            out.append("models has no role %s; the roles are %s" % (", ".join(bad), ", ".join(MODEL_ROLES)))
        empty = sorted(k for k, x in m.items() if k in MODEL_ROLES and not (isinstance(x, str) and x.strip()))
        if empty:
            out.append("models.%s must be a model name" % ", models.".join(empty))
    mgr = cfg.get("manager")
    if mgr is not None and not isinstance(mgr, dict):
        out.append("manager takes an object; not: %r" % (mgr,))
    elif isinstance(mgr, dict):
        stray = sorted(k for k in mgr if k not in MANAGER_KEYS)
        if stray:
            note = (" \"passes\" was a local patch of one project: a second pass would restart every unfinished feature at attempt 1, "
                    "which is only a second full budget - delete the key and raise the top-level maxAttempts instead" if "passes" in stray else "")
            out.append("manager has no key %s; the keys are %s.%s" % (", ".join(stray), ", ".join(MANAGER_KEYS), note))
        one_of(mgr, "autonomy", AUTONOMY, "manager.autonomy")
        if given(mgr, "sectionsPerRun") and not _whole(mgr["sectionsPerRun"], 1):
            out.append("manager.sectionsPerRun takes a whole number of at least 1; not: %r" % (mgr["sectionsPerRun"],))
        if given(mgr, "stopAt") and not (isinstance(mgr["stopAt"], list) and all(isinstance(x, str) for x in mgr["stopAt"])):
            out.append("manager.stopAt takes a list of section slugs; not: %r" % (mgr["stopAt"],))
        for k in ("delegation", "delegatedOn", "decomposeModel"):
            if given(mgr, k) and not isinstance(mgr[k], str):
                out.append("manager.%s takes a string; not: %r" % (k, mgr[k]))
        if given(mgr, "effort"):
            ef = mgr["effort"]
            if not isinstance(ef, dict):
                out.append("manager.effort takes an object with %s; not: %r" % (", ".join(MANAGER_EFFORT_KEYS), ef))
            else:
                badk = sorted(k for k in ef if k not in MANAGER_EFFORT_KEYS)
                if badk:
                    out.append("manager.effort has no key %s; the keys are %s" % (", ".join(badk), ", ".join(MANAGER_EFFORT_KEYS)))
    return out


def validate_config(cfg, ds=None):
    problems = config_problems(cfg, ds)
    if problems:
        raise RuntimeError("%s: %s" % (CONFIG, "; ".join(problems)))


def models_policy(cfg):
    """`models`, normalised (names trimmed) after validate_config accepted it. A role it does not name uses `model`."""
    m = cfg.get("models")
    return {k: v.strip() for k, v in m.items()} if isinstance(m, dict) and m else None


def verifier_policy(cfg):
    """`verifier`, normalised after validate_config accepted it: the cap of mutants per tier that was named, the
    severity of a survivor, and how a round after the first is verified."""
    v = cfg.get("verifier")
    if not isinstance(v, dict):
        return None
    out = {}
    if isinstance(v.get("sensor"), dict) and v["sensor"]:
        out["sensor"] = dict(v["sensor"])
    for k in ("survivor", "rounds"):
        if v.get(k):
            out[k] = v[k]
    return out or None


def index_sections(root):
    """Sections in build order from docs/ROADMAP-INDEX.md: its `## Roadmaps` table, ordered by the
    numbered list in `## Ordering` (table order when that list names none of them). A single-section
    project is one section: docs/ROADMAP.md, already decomposed by Phase 2."""
    path = os.path.join(root, "docs", "ROADMAP-INDEX.md")
    if not os.path.isfile(path):
        if os.path.isfile(os.path.join(root, "docs", "ROADMAP.md")):
            return [{"slug": "roadmap", "roadmap": "docs/ROADMAP.md", "txt": "docs/roadmap.txt", "dependsOn": []}]
        raise RuntimeError("no docs/ROADMAP-INDEX.md and no docs/ROADMAP.md: nothing for manager mode to build")
    text = open(path, encoding="utf-8").read()
    table = CR.block(text, "## Roadmaps")
    if table is None:
        raise RuntimeError("docs/ROADMAP-INDEX.md has no `## Roadmaps` table")
    rows = []
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not SLUG_RE.search(cells[1]):
            continue
        slug = SLUG_RE.search(cells[1]).group(1)
        txt = re.search(r"`?(docs/roadmap-[\w-]+\.txt)`?", cells[2])
        deps = re.findall(r"`([A-Za-z0-9][\w-]*)`", cells[4])
        rows.append({"slug": slug, "roadmap": "docs/ROADMAP-%s.md" % slug,
                     "txt": txt.group(1) if txt else "docs/roadmap-%s.txt" % slug, "dependsOn": deps})
    if not rows:
        raise RuntimeError("docs/ROADMAP-INDEX.md `## Roadmaps` has no row naming a docs/ROADMAP-<slug>.md")
    by = {r["slug"]: r for r in rows}
    ordering = CR.block(text, "## Ordering") or ""
    order = []
    for line in ordering.splitlines():
        m = re.match(r"^\s*\d+\.\s+.*?`([A-Za-z0-9][\w-]*)`", line)
        if m and m.group(1) in by and m.group(1) not in order:
            order.append(m.group(1))
    order += [r["slug"] for r in rows if r["slug"] not in order]
    return [by[s] for s in order]


def section_states(root, cfg=None):
    """Each section, with `decomposed`, the features still to build, and the doubtful ones."""
    ds, ds_dir = downstream(root)
    if not ds:
        raise RuntimeError("no tlc-spec-lean or tlc-spec-driven under %s/.claude/skills" % root)
    out = []
    for sec in index_sections(root):
        names = CR.txt_names(os.path.join(root, sec["txt"]))
        decomposed = bool(names) and os.path.isfile(os.path.join(root, sec["roadmap"]))
        pending, doubtful = [], {}
        if decomposed:
            with open(os.path.join(root, sec["roadmap"]), encoding="utf-8") as fh:
                entries = {n: f for n, f, _b in CR.parse_features(fh.read())}
            _d, pending, _q, doubtful = classify(root, ds, ds_dir, entries, names, cfg or {}, sec["roadmap"])
        out.append(dict(sec, decomposed=decomposed, pending=pending, doubtful=doubtful))
    return out, ds, ds_dir


def manager_args(root, cfg):
    ds_now, _d = downstream(root)
    validate_config(cfg, ds_now)
    mgr = dict(DEFAULT_CONFIG["manager"], **(cfg.get("manager") or {}))
    if not (mgr.get("delegation") or "").strip():
        raise RuntimeError("%s has no manager.delegation: manager mode decides what would otherwise be asked, "
                           "and only the owner can hand that over, in their own words" % CONFIG)
    if mgr.get("autonomy", "decide") not in AUTONOMY:
        raise RuntimeError("%s manager.autonomy takes \"decide\" or \"unblock\"" % CONFIG)
    secs, ds, ds_dir = section_states(root, cfg)
    owed = barrier_pending(root, cfg)
    status = os.path.join("docs", "ROADMAP-INDEX.md")
    if not os.path.isfile(os.path.join(root, status)):
        status = os.path.join("docs", "ROADMAP.md")
    return {
        "project": root, "skillDir": SKILL_DIR, "downstream": ds, "downstreamDir": ds_dir,
        "statusPath": status, "mainBranch": cfg.get("mainBranch") or "main",
        "pipelineScript": os.path.join(SKILL_DIR, "scripts", "roadmap-pipeline.js"),
        "model": cfg.get("model") or None, "decomposeModel": mgr.get("decomposeModel") or None,
        "delegation": mgr["delegation"].strip(), "delegatedOn": mgr.get("delegatedOn") or "",
        "autonomy": mgr.get("autonomy") or "decide",
        "stopAt": list(mgr.get("stopAt") or []), "sectionsPerRun": int(mgr.get("sectionsPerRun") or 4),
        "effort": dict(DEFAULT_CONFIG["manager"]["effort"], **(mgr.get("effort") or {})),
        "sections": secs,
        **({"barrierPending": owed} if owed else {}),
    }


# --------------------------------------------------------------------------- selftest

def selftest():
    tmp = tempfile.mkdtemp(prefix="plan-pipeline-selftest-")
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    try:
        root = os.path.join(tmp, "proj")
        gate_dir = os.path.join(root, ".claude", "skills", "tlc-spec-lean", "scripts")
        os.makedirs(gate_dir)
        open(os.path.join(root, ".claude", "skills", "tlc-spec-lean", "SKILL.md"), "w").write("x")
        # the fake gate passes exactly the features whose report says PASS
        open(os.path.join(gate_dir, "validate_verification.py"), "w").write(
            "import sys,os\nf=sys.argv[1]; r=sys.argv[sys.argv.index('--root')+1]\n"
            "p=os.path.join(r,'.specs','features',f,'verification.md')\n"
            "sys.exit(0 if os.path.isfile(p) and 'PASS' in open(p).read() else 1)\n")
        os.makedirs(os.path.join(root, "docs"))
        open(os.path.join(root, "docs", "roadmap.txt"), "w").write("n-done\nn-fail\nn-ask\nn-big\nn-next\n")
        open(os.path.join(root, "docs", "ROADMAP.md"), "w").write("""# R

## Status

x

### n-done

- **objective** — done.
- **size** — Small
- **implicit dimensions present** — none
- **external contract consumed** — none

### n-fail

- **objective** — built, refused.
- **size** — Medium
- **implicit dimensions present** — persistence/state
- **external contract consumed** — none

### n-ask

- **objective** — a question.
- discharge: no code — answered open question or context.md

### n-big

- **objective** — big.
- **depends on** — n-fail
- **size** — Large
- **implicit dimensions present** — persistence/state
- **external contract consumed** — none

### n-next

- **objective** — next.
- **depends on** — n-done
- **size** — Small
- **implicit dimensions present** — none
- **external contract consumed** — none
""")
        for n, verdict in (("n-done", "PASS"), ("n-fail", "FAIL")):
            os.makedirs(os.path.join(root, ".specs", "features", n))
            open(os.path.join(root, ".specs", "features", n, "verification.md"), "w").write("**Verdict**: %s\n" % verdict)
        subprocess.run(["git", "init", "-q", "-b", "master", root], check=True)
        subprocess.run(["git", "-C", root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "--allow-empty", "-m", "init"], check=True)
        cfg = dict(DEFAULT_CONFIG, confirmed=True, gate="make check", lanes=2)
        try:
            plan(root, os.path.join("docs", "ROADMAP.md"), cfg)
            refused = ""
        except RuntimeError as e:
            refused = str(e)
        expect("a feature with a report the gate refuses is doubtful until the owner classifies it",
               "n-fail (has a verification.md the gate refuses)" in refused and "featureStatus" in refused)
        cfg = dict(cfg, featureStatus={"n-fail": "build"})
        args, info = plan(root, os.path.join("docs", "ROADMAP.md"), cfg)
        names = [f["name"] for f in args["features"]]
        by = {f["name"]: f for f in args["features"]}
        expect("a feature whose gate passes is not pending", "n-done" in info["done"] and "n-done" not in names)
        expect("a feature whose report fails is pending", "n-fail" in names)
        expect("a question-only feature is never built", "n-ask" in info["discharged"] and "n-ask" not in names)
        expect("build order is kept", names == ["n-fail", "n-big", "n-next"])
        expect("tiers are derived by check-roadmap's rule", by["n-big"]["tier"] == "A" and by["n-next"]["tier"] == "C")
        expect("a dependency already done is dropped", by["n-next"]["dependsOn"] == [])
        expect("a pending dependency is kept, and shares its lane", by["n-big"]["dependsOn"] == ["n-fail"]
               and by["n-big"]["lane"] == by["n-fail"]["lane"])
        expect("an independent feature goes to the least-loaded lane", by["n-next"]["lane"] != by["n-fail"]["lane"])
        # 3.36.0, from a real run: a feature left unfinished kept its worktree in lane2, was handed lane1
        # on the next run, and its merger looked for the worktree where it was not
        rel_road = os.path.join("docs", "ROADMAP.md")
        held = os.path.join(root.rstrip("/") + ".lanes", "lane2", "n-big")
        subprocess.run(["git", "-C", root, "worktree", "add", "-q", "-b", "feat/n-big", held], check=True)
        byw = {f["name"]: f for f in plan(root, rel_road, cfg)[0]["features"]}
        expect("a feature that already has a worktree keeps that lane, whatever the balancing says",
               byw["n-big"]["lane"] == 2 and byw["n-fail"]["lane"] == 1)
        expect("and names that worktree, as git reports it",
               os.path.realpath(byw["n-big"].get("worktree", "")) == os.path.realpath(held) and "worktree" not in byw["n-fail"])
        shutil.rmtree(held)
        expect("a worktree whose directory is gone is not trusted",
               "worktree" not in {f["name"]: f for f in plan(root, rel_road, cfg)[0]["features"]}["n-big"])
        subprocess.run(["git", "-C", root, "worktree", "prune"], check=True)
        # lanes shrunk to 1 with a feature still in its lane worktree: git would refuse the branch twice
        subprocess.run(["git", "-C", root, "worktree", "add", "-q", held, "feat/n-big"], check=True)
        try:
            plan(root, rel_road, dict(cfg, lanes=1))
            shrunk = ""
        except RuntimeError as e:
            shrunk = str(e)
        expect("lanes shrunk to 1 refuses while a feature still holds a lane worktree, and says what to do",
               "n-big" in shrunk and "worktree remove" in shrunk)
        subprocess.run(["git", "-C", root, "worktree", "remove", "--force", held], check=True)
        # the root itself on a feature branch is no worktree to keep; with lanes above 1 it must be refused
        subprocess.run(["git", "-C", root, "checkout", "-q", "feat/n-big"], check=True)
        expect("the project root is never reported as a feature's worktree", "feat/n-big" not in feature_worktrees(root))
        try:
            plan(root, rel_road, cfg)
            onbranch = ""
        except RuntimeError as e:
            onbranch = str(e)
        expect("with lanes above 1 a root left on a feature branch is refused", "n-big" in onbranch and "Check out" in onbranch)
        expect("with one lane that root is the normal state, and is planned", "n-big" in
               {f["name"] for f in plan(root, rel_road, dict(cfg, lanes=1))[0]["features"]})
        subprocess.run(["git", "-C", root, "checkout", "-q", "master"], check=True)
        subprocess.run(["git", "-C", root, "branch", "-q", "-D", "feat/n-big"], check=True)
        expect("the gate comes from the confirmed config", args["gate"] == "make check" and args["downstream"] == "tlc-spec-lean")
        _a, info2 = plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, featureStatus={"n-fail": "done"}))
        expect("classified done, it is skipped without touching its report", "n-fail" in info2["done"]
               and "n-fail" not in info2["pending"])
        try:
            plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, featureStatus={"n-fail": "maybe"}))
            ok_word = False
        except RuntimeError as e:
            ok_word = "featureStatus" in str(e)
        expect("featureStatus takes only done or build", ok_word)
        expect("no barrier and no model unless the config sets them",
               args["barrierGate"] is None and args["barrierEvery"] == 0 and args["model"] is None)
        args2, _ = plan(root, os.path.join("docs", "ROADMAP.md"),
                        dict(cfg, barrierGate="make all", barrierEvery=3, model="sonnet"))
        expect("the gate runs first unless the config says otherwise", args["gateOrder"] == "gate-first")
        args3, _ = plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, gateOrder="verify-first"))
        expect("gateOrder verify-first reaches the args", args3["gateOrder"] == "verify-first")
        expect("the merge reruns the gate unless the config says otherwise", args["mergeGate"] == "rerun")
        mg, _ = plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, mergeGate="receipt", barrierGate="make all", barrierEvery=2))
        expect("mergeGate receipt reaches the args when a barrier exists", mg["mergeGate"] == "receipt")
        for label, bad in (("receipt without a barrierGate", dict(mergeGate="receipt")), ("an unknown mergeGate", dict(mergeGate="trust"))):
            try:
                plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, **bad))
                refused = False
            except RuntimeError as e:
                refused = "mergeGate" in str(e)
            expect("%s is refused" % label, refused)
        try:
            plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, gateOrder="gate-last"))
            ok_order = False
        except RuntimeError as e:
            ok_order = "gateOrder" in str(e)
        expect("gateOrder takes only gate-first or verify-first", ok_order)
        expect("no per-role models unless the config sets them", "models" not in args)
        m1, _ = plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, models={"build": "sonnet", "verify": "opus"}))
        expect("models reach the args", m1["models"] == {"build": "sonnet", "verify": "opus"})
        for label, bad in (("a role that does not exist", {"builder": "sonnet"}), ("an empty model name", {"build": ""}),
                           ("a list instead of an object", ["sonnet"])):
            try:
                plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, models=bad))
                refused = False
            except RuntimeError as e:
                refused = "models" in str(e)
            expect("models: %s is refused" % label, refused)
        def refused_with(label, over, word):
            try:
                plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, **over))
                said = ""
            except RuntimeError as e:
                said = str(e)
            expect("%s is refused, naming %s" % (label, word), word in said)
            return said
        for label, over, word in (
                ("a verifier that is 0", {"verifier": 0}, "verifier"), ("a verifier that is false", {"verifier": False}, "verifier"),
                ("a sensor that is 0", {"verifier": {"sensor": 0}}, "verifier.sensor"), ("a survivor that is an empty string", {"verifier": {"survivor": ""}}, "verifier.survivor"),
                ("a rounds that is false", {"verifier": {"rounds": False}}, "verifier.rounds"), ("a typo inside verifier", {"verifier": {"sensr": {"A": 3}}}, "sensr"),
                ("a sensor cap that is true", {"verifier": {"sensor": {"A": True}}}, "verifier.sensor.A"), ("a sensor cap of 3.0", {"verifier": {"sensor": {"A": 3.0}}}, "verifier.sensor.A"),
                ("models as a list", {"models": []}, "models"), ("a model name that is only spaces", {"models": {"build": "  "}}, "models.build"),
                ("barrierEvery that is a word", {"barrierEvery": "x"}, "barrierEvery"), ("lanes that is 0", {"lanes": 0}, "lanes"),
                ("receipt with a barrierGate that is only spaces", {"mergeGate": "receipt", "barrierGate": "  ", "barrierEvery": 1}, "barrierGate"),
                ("receipt with a barrier that runs once at the end", {"mergeGate": "receipt", "barrierGate": "make all", "barrierEvery": 0}, "barrierEvery"),
                ("a manager.effort with a role it does not have", {"manager": {"effort": {"deciding": "high"}}}, "deciding"),
                ("a manager.sectionsPerRun of -3", {"manager": {"sectionsPerRun": -3}}, "sectionsPerRun"),
                ("a manager.stopAt that is a bare string", {"manager": {"stopAt": "live"}}, "stopAt")):
            refused_with(label, over, word)
        many = refused_with("three mistakes together", {"gateOrder": "x", "models": {"zzz": "m"}, "verifier": {"rounds": "partial"}}, "gateOrder")
        expect("every problem is reported in one go, not one per run", "models has no role zzz" in many and "verifier.rounds" in many)
        trimmed, _ = plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, models={"build": " sonnet "}))
        expect("a model name is trimmed", trimmed["models"] == {"build": "sonnet"})
        expect("a barrierGate of spaces is no barrierGate", plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, barrierGate="  "))[0]["barrierGate"] is None)
        expect("an empty verifier object and an empty models object are no policy",
               plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, verifier={}, models={}))[0].get("verifier") is None)
        roles_all = {r: "m-" + r for r in ("build", "prove", "verify", "review", "merge", "record", "triage", "barrier")}
        expect("every role the pipeline can name is accepted", plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, models=roles_all))[0]["models"] == roles_all)
        expect("a sensor naming only one tier is accepted", plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, verifier={"sensor": {"A": 3}}))[0]["verifier"]["sensor"] == {"A": 3})
        said_ds = refused_with("a survivor that is only minor under tlc-spec-lean", {"verifier": {"survivor": "minor"}}, "tlc-spec-lean")
        expect("and the message says why this downstream was chosen", "because it is installed" in said_ds)
        try:
            manager_args(root, dict(cfg, manager={"delegation": "decide"}, gateOrder="gate-last", models={"bogus": "m"}))
            said_m = ""
        except RuntimeError as e:
            said_m = str(e)
        expect("manager mode checks the same keys before it spends anything", "gateOrder" in said_m and "models has no role bogus" in said_m)
        expect("no mutant cap and no survivor severity unless the config sets them",
               not (args["verifier"] or {}).get("sensor") and not (args["verifier"] or {}).get("survivor"))
        v1, _ = plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, verifier={"sensor": {"A": 5, "B": 3, "C": 1}, "survivor": "major"}))
        expect("a verifier policy reaches the args", v1["verifier"] == {"sensor": {"A": 5, "B": 3, "C": 1}, "survivor": "major"})
        try:
            plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, verifier={"survivor": "minor"}))
            lean_minor = False
        except RuntimeError as e:
            lean_minor = "tlc-spec-lean" in str(e)
        expect("a survivor that is only minor is refused under tlc-spec-lean, whose gate would refuse the report", lean_minor)
        for label, bad in (("a round mode that does not exist", {"rounds": "partial"}), ("a mutant cap of zero", {"sensor": {"A": 0}}), ("an unknown tier", {"sensor": {"D": 3}}),
                           ("an unknown severity", {"survivor": "fatal"}), ("a cap that is not a number", {"sensor": {"A": "5"}})):
            try:
                plan(root, os.path.join("docs", "ROADMAP.md"), dict(cfg, verifier=bad))
                refused = False
            except RuntimeError as e:
                refused = "verifier" in str(e)
            expect("%s is refused" % label, refused)
        expect("the barrier and the model reach the args",
               args2["barrierGate"] == "make all" and args2["barrierEvery"] == 3 and args2["model"] == "sonnet")
        rc = main(["--root", root])
        expect("without a confirmed pipeline.json nothing is printed", rc == 1)
        rc = main(["--root", root, "--init"])
        written = json.load(open(os.path.join(root, CONFIG)))
        expect("--init writes an unconfirmed config", rc == 0 and written["confirmed"] is False)
        expect("--init detects the real main branch", written["mainBranch"] == "master")
        expect("--init leaves the barrier and the model for the user to set",
               written["barrierGate"] is None and written["model"] is None)
        written.update(confirmed=True, gate="make check", mainBranch="main", featureStatus={"n-fail": "build"})
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = main(["--root", root])
        expect("a mainBranch that is not a branch is refused", rc == 1)
        written["mainBranch"] = "master"
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = main(["--root", root])
        expect("the summary line names the absolute scriptPath",
               rc == 0 and os.path.join(SKILL_DIR, "scripts", "roadmap-pipeline.js") in err.getvalue())

        # manager mode: sections come from the index, in the order its ## Ordering list gives
        open(os.path.join(root, "docs", "ROADMAP-INDEX.md"), "w").write("""# I

## Roadmaps

| Section | Roadmap file | Build-order file | Slug / prefix | Depends on |
|---|---|---|---|---|
| Later work | `docs/ROADMAP-late.md` | `docs/roadmap-late.txt` | `late` | `core` |
| Core | `docs/ROADMAP-core.md` | `docs/roadmap-core.txt` | `core` | — |

## Ordering

1. `core` — first.
2. `late` — needs core.
""")
        os.rename(os.path.join(root, "docs", "ROADMAP.md"), os.path.join(root, "docs", "ROADMAP-core.md"))
        os.rename(os.path.join(root, "docs", "roadmap.txt"), os.path.join(root, "docs", "roadmap-core.txt"))
        secs, _ds, _d = section_states(root)
        expect("sections come in ## Ordering's order, not the table's", [x["slug"] for x in secs] == ["core", "late"])
        expect("a section's dependencies are read from the table", secs[1]["dependsOn"] == ["core"])
        expect("a section with a roadmap and a build order is decomposed, and lists what is left",
               secs[0]["decomposed"] and "n-fail" in secs[0]["pending"] and "n-done" not in secs[0]["pending"])
        expect("a section with neither is not decomposed", not secs[1]["decomposed"] and secs[1]["pending"] == [])
        expect("without the owner's word a refused report makes the section doubtful",
               "n-fail" in section_states(root)[0][0]["doubtful"])
        # n-next is done and depends on n-done; make it depend on n-big (pending) instead
        core = os.path.join(root, "docs", "ROADMAP-core.md")
        body = open(core).read()
        open(core, "w").write(body.replace("- **depends on** — n-done", "- **depends on** — n-big"))
        os.makedirs(os.path.join(root, ".specs", "features", "n-next"))
        open(os.path.join(root, ".specs", "features", "n-next", "verification.md"), "w").write("**Verdict**: PASS\n")
        d2 = section_states(root, {"featureStatus": {"n-fail": "build"}})[0][0]["doubtful"]
        expect("a pending feature a finished one depends on is doubtful (a question gate with no discharge line)",
               d2.get("n-big", "").startswith("finished feature n-next depends on it"))
        open(core, "w").write(body)
        shutil.rmtree(os.path.join(root, ".specs", "features", "n-next"))
        written = json.load(open(os.path.join(root, CONFIG)))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = main(["--root", root, "--manager"])
        expect("manager mode refuses without the owner's written delegation", rc == 1)
        written["manager"] = dict(written.get("manager") or {}, delegation="decide everything; I review later",
                                  delegatedOn="2026-09-29", stopAt=["late"])
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(["--root", root, "--manager"])
        margs = json.loads(out.getvalue()) if rc == 0 else {}
        expect("with a delegation it prints the manager's args, delegation and stops included",
               rc == 0 and margs.get("delegation", "").startswith("decide everything") and margs.get("stopAt") == ["late"]
               and margs["pipelineScript"].endswith("roadmap-pipeline.js") and len(margs["sections"]) == 2)
        expect("its summary line names the manager's absolute scriptPath",
               os.path.join(SKILL_DIR, "scripts", "manager-pipeline.js") in err.getvalue())
        expect("autonomy is decide unless the owner raises it", margs.get("autonomy") == "decide")
        written["manager"]["autonomy"] = "unblock"
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            main(["--root", root, "--manager"])
        expect("the owner's unblock reaches the manager", json.loads(out.getvalue()).get("autonomy") == "unblock")
        written["manager"]["autonomy"] = "everything"
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = main(["--root", root, "--manager"])
        expect("an autonomy level that does not exist is refused", rc == 1)
        written["manager"]["autonomy"] = "decide"
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        os.remove(os.path.join(root, "docs", "ROADMAP-INDEX.md"))
        os.rename(os.path.join(root, "docs", "ROADMAP-core.md"), os.path.join(root, "docs", "ROADMAP.md"))
        os.rename(os.path.join(root, "docs", "roadmap-core.txt"), os.path.join(root, "docs", "roadmap.txt"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = main(["--root", root, "--manager"])
        one = json.loads(out.getvalue()) if rc == 0 else {}
        expect("a single-section project is one section, its roadmap the Status file",
               rc == 0 and [x["roadmap"] for x in one.get("sections", [])] == ["docs/ROADMAP.md"]
               and one.get("statusPath") == os.path.join("docs", "ROADMAP.md"))

        # 3.36.0: a barrier a run never finished is owed by the next one. The proof is the commit of the
        # last green barrier, kept outside the tree; code that landed after it has never been proved.
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

        def land(path, body="x\n"):
            os.makedirs(os.path.dirname(os.path.join(root, path)), exist_ok=True)
            open(os.path.join(root, path), "w").write(body)
            subprocess.run(["git", "-C", root, "add", path], check=True, env=env)
            subprocess.run(["git", "-C", root, "commit", "-qm", "add " + path], check=True, env=env)
            return git(root, "rev-parse", "master")
        gated = dict(cfg, barrierGate="make all", mainBranch="master")
        expect("with no barrier ever recorded nothing is owed (unknown, not unproven)", barrier_pending(root, gated) is None)
        h0 = git(root, "rev-parse", "master")
        record_barrier(root, "master", h0)
        expect("with the head proved nothing is owed", barrier_pending(root, gated) is None)
        h1 = land("src/a.py")
        expect("code merged after the last green barrier is owed a barrier, from that commit",
               barrier_pending(root, gated) == {"base": h0, "head": h1})
        expect("a project with no barrierGate is never owed one", barrier_pending(root, dict(gated, barrierGate=None)) is None)
        record_barrier(root, "master", h1)
        land("docs/notes.md")
        land(".specs/features/x/plan.md")
        expect("commits that only touch docs and .specs owe nothing", barrier_pending(root, gated) is None)
        h3 = land("src/b.py")
        orphan = subprocess.run(["git", "-C", root, "commit-tree", "-m", "orphan", git(root, "rev-parse", "master^{tree}")],
                                capture_output=True, text=True, env=env, check=True).stdout.strip()
        try:
            record_barrier(root, "master", orphan)
            refused = ""
        except RuntimeError as e:
            refused = str(e)
        expect("a commit that is not on the main branch cannot be recorded as proved", "not on master" in refused)
        expect("and the refused record left the old one standing", barrier_pending(root, gated) == {"base": h1, "head": h3})
        state = barrier_state_path(root)
        json.dump({"main": "master", "sha": orphan}, open(state, "w"))
        try:
            barrier_pending(root, gated)
            unreachable = ""
        except RuntimeError as e:
            unreachable = str(e)
        expect("a recorded commit the main branch no longer contains is refused, naming the file to delete",
               "not an ancestor" in unreachable and os.path.basename(state) in unreachable)
        json.dump({"main": "master", "sha": h1}, open(state, "w"))
        written = json.load(open(os.path.join(root, CONFIG)))
        written.update(barrierGate="make all", mainBranch="master",
                       featureStatus={"n-fail": "done", "n-big": "done", "n-next": "done"})
        json.dump(written, open(os.path.join(root, CONFIG), "w"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = main(["--root", root])
        owed = json.loads(out.getvalue()) if rc == 0 else {}
        expect("with nothing to build but a barrier owed, the args still print so the pipeline can run it",
               rc == 0 and owed.get("features") == [] and owed.get("barrierPending") == {"base": h1, "head": h3})
        mw = dict(written, manager={"delegation": "decide", "delegatedOn": "2026-10-06"})
        expect("manager mode is told too, so it does not call the section already done",
               manager_args(root, mw).get("barrierPending") == {"base": h1, "head": h3})
        for label, extra, word in (("passes", {"passes": 2}, "maxAttempts"), ("a misspelt key", {"sectionPerRun": 3}, "sectionPerRun")):
            try:
                manager_args(root, dict(written, manager=dict(mw["manager"], **extra)))
                said = ""
            except RuntimeError as e:
                said = str(e)
            expect("a manager key that means nothing is refused by name, not ignored (%s)" % label, word in said and "manager has no key" in said)
        record_barrier(root, "master", h3)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = main(["--root", root])
        expect("once the barrier is green and recorded, nothing to build is a refusal again", rc == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="the project root")
    ap.add_argument("--roadmap", help="the one roadmap to build (default docs/ROADMAP.md)")
    ap.add_argument("--init", action="store_true", help="write docs/process/pipeline.json to confirm")
    ap.add_argument("--manager", action="store_true", help="print manager-pipeline.js's args (manager mode)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.root or not os.path.isdir(a.root):
        print("give --root <project-root>", file=sys.stderr)
        return 2
    root = os.path.abspath(a.root)
    cfg_path = os.path.join(root, CONFIG)
    if a.init:
        if os.path.exists(cfg_path):
            print("%s exists; edit it rather than regenerating it" % CONFIG, file=sys.stderr)
            return 1
        cfg = dict(DEFAULT_CONFIG, gate=detect_gate(root), mainBranch=detect_main(root))
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=1)
        print("wrote %s with gate %r — confirm the command every feature must pass before it merges "
              "(typecheck, lint, the whole suite — or the affected tests, when the project keeps its whole "
              "suite for a batch barrier, which then goes in \"barrierGate\"), and set \"confirmed\": true "
              "before planning" % (CONFIG, cfg["gate"]), file=sys.stderr)
        return 0
    if not os.path.isfile(cfg_path):
        print("no %s: run with --init, then confirm it" % CONFIG, file=sys.stderr)
        return 1
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if cfg.get("confirmed") is not True or not cfg.get("gate"):
        print("%s is not confirmed: the gate command decides every PASS the pipeline records, so a "
              "person confirms it (set \"confirmed\": true) before anything runs" % CONFIG, file=sys.stderr)
        return 1
    if cfg.get("barrierGate") is not None and not isinstance(cfg.get("barrierGate"), str):
        print("%s: barrierGate must be a command or null" % CONFIG, file=sys.stderr)
        return 1
    main_branch = cfg.get("mainBranch") or "main"
    if git(root, "rev-parse", "--verify", "--quiet", "refs/heads/" + main_branch) is None:
        print("%s names mainBranch %r, which is not a branch of this repository — every merge would "
              "fail; set it to the branch features merge into" % (CONFIG, main_branch), file=sys.stderr)
        return 1
    if a.manager:
        try:
            margs = manager_args(root, cfg)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 1
        todo = [x for x in margs["sections"] if not x["decomposed"] or x["pending"]]
        if margs.get("barrierPending") and not todo:
            print("manager: nothing left to build, but the barrier owes a run: %s..%s carries code no green barrier proved"
                  % (margs["barrierPending"]["base"][:9], margs["barrierPending"]["head"][:9]), file=sys.stderr)
        doubt = {k: v for x in margs["sections"] for k, v in x["doubtful"].items()}
        print("manager (autonomy %s): %d section(s), %d with work left (%s); stops at %s; scriptPath %s" % (
              margs["autonomy"], len(margs["sections"]), len(todo),
              ", ".join("%s:%s" % (x["slug"], ("%d, %d needing the owner" % (len(x["pending"]), len(x["doubtful"]))
                                              if x["doubtful"] else len(x["pending"])) if x["decomposed"] else "to decompose")
                        for x in todo) or "none",
              ", ".join(margs["stopAt"]) or "nothing", os.path.join(SKILL_DIR, "scripts", "manager-pipeline.js")),
              file=sys.stderr)
        if doubt:
            print("a section with a feature that needs the owner is not built, nor is any section depending on "
                  "it. " + doubtful_message(doubt), file=sys.stderr)
        if not todo and not margs.get("barrierPending"):
            return 1
        print(json.dumps(margs, indent=1))
        return 0
    rel = a.roadmap or os.path.join("docs", "ROADMAP.md")
    if not os.path.isfile(os.path.join(root, rel)):
        print("no roadmap at %s; in multi-section mode pass --roadmap docs/ROADMAP-<slug>.md" % rel, file=sys.stderr)
        return 2
    try:
        args, info = plan(root, rel, cfg)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    print("%s: %d done, %d question-only, %d to build (%s); scriptPath %s" % (
          rel, len(info["done"]), len(info["discharged"]), len(info["pending"]),
          ", ".join("%s:%s" % (f["name"], f["tier"]) for f in args["features"]) or "none",
          os.path.join(SKILL_DIR, "scripts", "roadmap-pipeline.js")), file=sys.stderr)
    if args.get("barrierPending"):
        print("the barrier is owed: %s..%s carries code that no green barrier proved; it runs before anything is built"
              % (args["barrierPending"]["base"][:9], args["barrierPending"]["head"][:9]), file=sys.stderr)
    if not args["features"] and not args.get("barrierPending"):
        return 1
    print(json.dumps(args, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
