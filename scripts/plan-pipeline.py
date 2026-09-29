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
    "manager": {"delegation": "", "delegatedOn": "", "stopAt": [], "sectionsPerRun": 4,
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
    done, pending, discharged, doubtful = classify(root, ds, ds_dir, entries, order, cfg, roadmap_rel)
    if doubtful:
        raise RuntimeError(doubtful_message(doubtful))
    lanes = max(1, int(cfg.get("lanes") or 1))
    lane_of, load = {}, {n: 0 for n in range(1, lanes + 1)}
    feats = []
    for name in pending:
        fields = entries[name]
        floor, _why = CR.derive_tier(fields)
        stated, _r = CR.stated_tier(fields)
        tier = stated if stated and CR.TIER_RANK[stated] >= CR.TIER_RANK[floor] else floor
        deps = [d for d in deps_of(fields) if d in pending and d != name]
        first = next((lane_of[d] for d in deps if d in lane_of), None)
        lane = first or min(load, key=lambda k: (load[k], k))
        lane_of[name] = lane
        load[lane] += 1
        feats.append({"name": name, "roadmap": roadmap_rel, "tier": tier, "dependsOn": deps, "lane": lane})
    args = {
        "project": root, "skillDir": SKILL_DIR, "downstream": ds, "downstreamDir": ds_dir,
        "statusPath": status, "mainBranch": cfg.get("mainBranch") or "main", "gate": cfg["gate"],
        "barrierGate": cfg.get("barrierGate") or None, "barrierEvery": int(cfg.get("barrierEvery") or 0),
        "model": cfg.get("model") or None,
        "testHint": cfg.get("testHint") or "", "setup": cfg.get("setup") or "", "push": bool(cfg.get("push")),
        "lanes": lanes, "worktreeRoot": root.rstrip("/") + ".lanes", "checklist": cfg.get("checklist"),
        "effort": cfg.get("effort") or DEFAULT_CONFIG["effort"],
        "maxAttempts": cfg.get("maxAttempts") or DEFAULT_CONFIG["maxAttempts"], "features": feats,
    }
    if cfg.get("waitChunk"):  # seconds per wait on a detached gate; only tests set it lower
        args["waitChunk"] = int(cfg["waitChunk"])
    return args, {"done": done, "discharged": discharged, "pending": pending, "downstream": ds}


SLUG_RE = re.compile(r"`?docs/ROADMAP-([A-Za-z0-9][\w-]*)\.md`?")


def index_sections(root):
    """Sections in build order from docs/ROADMAP-INDEX.md: its `## Roadmaps` table, ordered by the
    numbered list in `## Ordering` (table order when that list names none of them)."""
    path = os.path.join(root, "docs", "ROADMAP-INDEX.md")
    if not os.path.isfile(path):
        raise RuntimeError("no docs/ROADMAP-INDEX.md: manager mode needs a multi-section project")
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
    mgr = dict(DEFAULT_CONFIG["manager"], **(cfg.get("manager") or {}))
    if not (mgr.get("delegation") or "").strip():
        raise RuntimeError("%s has no manager.delegation: manager mode decides what would otherwise be asked, "
                           "and only the owner can hand that over, in their own words" % CONFIG)
    secs, ds, ds_dir = section_states(root, cfg)
    status = os.path.join("docs", "ROADMAP-INDEX.md")
    return {
        "project": root, "skillDir": SKILL_DIR, "downstream": ds, "downstreamDir": ds_dir,
        "statusPath": status, "mainBranch": cfg.get("mainBranch") or "main",
        "pipelineScript": os.path.join(SKILL_DIR, "scripts", "roadmap-pipeline.js"),
        "model": cfg.get("model") or None, "decomposeModel": mgr.get("decomposeModel") or None,
        "delegation": mgr["delegation"].strip(), "delegatedOn": mgr.get("delegatedOn") or "",
        "stopAt": list(mgr.get("stopAt") or []), "sectionsPerRun": int(mgr.get("sectionsPerRun") or 4),
        "effort": dict(DEFAULT_CONFIG["manager"]["effort"], **(mgr.get("effort") or {})),
        "sections": secs,
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
        doubt = {k: v for x in margs["sections"] for k, v in x["doubtful"].items()}
        print("manager: %d section(s), %d with work left (%s); stops at %s; scriptPath %s" % (
              len(margs["sections"]), len(todo),
              ", ".join("%s:%s" % (x["slug"], ("%d, %d needing the owner" % (len(x["pending"]), len(x["doubtful"]))
                                              if x["doubtful"] else len(x["pending"])) if x["decomposed"] else "to decompose")
                        for x in todo) or "none",
              ", ".join(margs["stopAt"]) or "nothing", os.path.join(SKILL_DIR, "scripts", "manager-pipeline.js")),
              file=sys.stderr)
        if doubt:
            print("a section with a feature that needs the owner is not built, nor is any section depending on "
                  "it. " + doubtful_message(doubt), file=sys.stderr)
        if not todo:
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
    if not args["features"]:
        return 1
    print(json.dumps(args, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
