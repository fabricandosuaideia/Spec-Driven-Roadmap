#!/usr/bin/env python3
"""Measure where a project's agent runs spend tokens. Read-only.

Why this exists: the cost of an agent build is almost never where it looks. On
the project that motivated this (2,629 transcripts, 2026-09-28) the model's own
output was 1.9% of the relative cost and re-reading cached context was 75%, so
the cost of a conversation grows with its length times its accumulated context.
Every lever that attacks that — a fresh agent per phase, a context budget, fewer
retries, a leaner orchestrator — is a hypothesis until the same decomposition
is measured before and after. This script is that measurement.

It reads Claude Code's transcripts for one project (JSONL, one line per event)
and prints, never message content, only counts:

  - token classes (cache read / cache write / output / fresh input) as shares;
  - cost by kind of conversation: main sessions, Agent-tool subagents, and
    Workflow agents;
  - cost by role, taken from each agent's `.meta.json` label. Workflow labels of
    the form `role:feature:attempt` also give cost per attempt and per feature;
  - per role: turns, context at the first turn, average context, and the share
    of context tokens that is GROWTH beyond the first turn — the measured form of
    "long conversations cost quadratically";
  - the orchestrator: how many task notifications its session processed.

    python3 measure-agents.py                       # project = current directory
    python3 measure-agents.py --project /path/to/repo --since 2026-09-01
    python3 measure-agents.py --save-baseline docs/process/cost-baseline.json
    python3 measure-agents.py --baseline docs/process/cost-baseline.json
    python3 measure-agents.py --selftest

The relative cost uses API list-price ratios (input 1, cache write 1.25, cache
read 0.1, output 5) because they are public. How a subscription plan weighs the
same tokens against its quota is NOT published; compare shares and before/after
ratios, never read the unit as money or as quota.

Exit codes: 0 measured, 1 --selftest failed, 2 nothing could be measured (no
transcripts, or none in the window) — an empty measurement is not a result.
"""

import argparse
import collections
import json
import os
import re
import shutil
import statistics
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass

# Public API list-price ratios. Overridable; see the module docstring for why
# these are neither money nor quota.
DEFAULT_WEIGHTS = (1.0, 1.25, 0.1, 5.0)  # input, cache write, cache read, output
TOKEN_CLASSES = ("inp", "cw", "cr", "out")
CLASS_NAMES = {"inp": "fresh input", "cw": "cache write", "cr": "cache read", "out": "output"}
NOTIFICATION_MARK = "<task-notification>"
BASELINE_VERSION = 1


# --------------------------------------------------------------------------- locate

def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def encode_project(path):
    """Claude Code stores a project's sessions under a directory named after the
    absolute path with every character outside [A-Za-z0-9-] replaced by '-'."""
    return re.sub(r"[^A-Za-z0-9-]", "-", os.path.abspath(path))


def transcript_dirs(project, extra):
    found = []
    auto = os.path.join(config_dir(), "projects", encode_project(project))
    if os.path.isdir(auto):
        found.append(auto)
    for d in extra:
        d = os.path.abspath(os.path.expanduser(d))
        if os.path.isdir(d) and d not in found:
            found.append(d)
    return found, auto


# --------------------------------------------------------------------------- classify

def read_meta(jsonl_path):
    meta = jsonl_path[:-len(".jsonl")] + ".meta.json"
    if not os.path.isfile(meta):
        return {}
    try:
        with open(meta, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def classify(path, root):
    """(kind, role, feature, attempt) for one transcript file."""
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    meta = read_meta(path)
    if "/workflows/" in "/" + rel:
        kind = "workflow-agent"
    elif "/subagents/" in "/" + rel:
        kind = "subagent"
    else:
        return "main-session", "main-session", None, None
    desc = (meta.get("description") or "").strip()
    atype = meta.get("agentType") or "unknown"
    if kind == "workflow-agent" and ":" in desc:
        parts = desc.split(":")
        attempt = int(parts[-1]) if parts[-1].isdigit() and len(parts) >= 3 else None
        feature = parts[1] if len(parts) >= 3 else None
        return kind, parts[0].strip().lower() or "unlabelled", feature, attempt
    if kind == "workflow-agent":
        return kind, "unlabelled", None, None
    return kind, "agent:" + atype, None, None


# --------------------------------------------------------------------------- scan

def scan(path, since, until):
    """Per-turn context sizes and token totals for one transcript.

    One API response is written as several JSONL lines (one per content block),
    each carrying the same usage; counting lines instead of responses inflates
    every number, so responses are de-duplicated by message id."""
    seen = set()
    totals = collections.Counter()
    ctx = []
    notifications = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if NOTIFICATION_MARK in line and '"type":"user"' in line.replace(" ", ""):
                try:
                    d = json.loads(line)
                except ValueError:
                    d = None
                if d and in_window(d.get("timestamp"), since, until):
                    notifications += 1
                continue
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "assistant" or not in_window(d.get("timestamp"), since, until):
                continue
            msg = d.get("message") or {}
            usage = msg.get("usage") or {}
            key = msg.get("id") or d.get("requestId") or d.get("uuid")
            if key in seen:
                continue
            seen.add(key)
            inp = usage.get("input_tokens") or 0
            cw = usage.get("cache_creation_input_tokens") or 0
            cr = usage.get("cache_read_input_tokens") or 0
            out = usage.get("output_tokens") or 0
            totals.update(inp=inp, cw=cw, cr=cr, out=out)
            ctx.append(inp + cw + cr)
    return ctx, totals, notifications


def in_window(ts, since, until):
    if not (since or until):
        return True
    if not ts:
        return False
    day = ts[:10]
    return (not since or day >= since) and (not until or day <= until)


# --------------------------------------------------------------------------- aggregate

def cost_of(totals, weights):
    return sum(w * totals.get(k, 0) for k, w in zip(TOKEN_CLASSES, weights))


def measure(dirs, since, until, weights):
    roles = collections.defaultdict(lambda: {
        "kind": None, "agents": 0, "turns": [], "first_ctx": [], "ctx_sum": 0,
        "growth_sum": 0, "totals": collections.Counter()})
    attempts = collections.Counter()
    features = collections.defaultdict(lambda: {"cost": 0.0, "max_attempt": 0})
    classes = collections.Counter()
    notifications = 0
    files = 0
    for root in dirs:
        for dp, _dirs, fs in os.walk(root):
            for f in fs:
                if not f.endswith(".jsonl"):
                    continue
                path = os.path.join(dp, f)
                kind, role, feature, attempt = classify(path, root)
                ctx, totals, notes = scan(path, since, until)
                if kind == "main-session":
                    notifications += notes
                if not ctx:
                    continue
                files += 1
                r = roles[role]
                r["kind"] = kind
                r["agents"] += 1
                r["turns"].append(len(ctx))
                r["first_ctx"].append(ctx[0])
                r["ctx_sum"] += sum(ctx)
                r["growth_sum"] += sum(c - ctx[0] for c in ctx if c > ctx[0])
                r["totals"].update(totals)
                classes.update(totals)
                c = cost_of(totals, weights)
                if attempt is not None:
                    attempts[attempt] += c
                if feature:
                    features[feature]["cost"] += c
                    features[feature]["max_attempt"] = max(features[feature]["max_attempt"], attempt or 0)
    return {"roles": roles, "attempts": attempts, "features": features,
            "classes": classes, "notifications": notifications, "files": files}


def summarise(m, weights):
    total = cost_of(m["classes"], weights)
    out = {"version": BASELINE_VERSION, "weights": list(weights), "files": m["files"],
           "total_units": total, "notifications": m["notifications"],
           "class_share": {}, "kind_share": {}, "roles": {}, "attempt_share": {},
           "features": len(m["features"]), "per_feature_units": None, "retry_share": None}
    if not total:
        return out
    for k in TOKEN_CLASSES:
        out["class_share"][k] = dict(zip(TOKEN_CLASSES, weights))[k] * m["classes"][k] / total
    kinds = collections.Counter()
    for name, r in m["roles"].items():
        c = cost_of(r["totals"], weights)
        kinds[r["kind"]] += c
        turns = sum(r["turns"])
        out["roles"][name] = {
            "kind": r["kind"], "agents": r["agents"], "turns": turns,
            "median_turns": statistics.median(r["turns"]),
            "first_ctx": statistics.median(r["first_ctx"]),
            "avg_ctx": r["ctx_sum"] / max(turns, 1),
            "growth_share": r["growth_sum"] / max(r["ctx_sum"], 1),
            "share": c / total}
    out["kind_share"] = {k: v / total for k, v in kinds.items()}
    att_total = sum(m["attempts"].values())
    if att_total:
        out["attempt_share"] = {str(a): c / total for a, c in sorted(m["attempts"].items())}
        out["retry_share"] = sum(c for a, c in m["attempts"].items() if a >= 2) / total
    if m["features"]:
        out["per_feature_units"] = sum(f["cost"] for f in m["features"].values()) / len(m["features"])
        hist = collections.Counter(f["max_attempt"] for f in m["features"].values())
        out["features_by_max_attempt"] = {str(k): v for k, v in sorted(hist.items())}
    return out


# --------------------------------------------------------------------------- report

def pct(x):
    return "%5.1f%%" % (100 * x) if x is not None else "   - "


def kilo(x):
    return "%dk" % round(x / 1000)


def report(s, top, base=None):
    print("transcripts: %d with at least one turn in the window" % s["files"])
    print("relative cost: %.0fM units (API price ratios - not money, not quota)" % (s["total_units"] / 1e6))
    print("token classes: " + "  ".join(
        "%s %s" % (CLASS_NAMES[k], pct(s["class_share"].get(k, 0)).strip()) for k in ("cr", "cw", "out", "inp")))
    print("by kind:       " + "  ".join(
        "%s %s" % (k, pct(v).strip()) for k, v in sorted(s["kind_share"].items(), key=lambda kv: -kv[1])))
    print("")
    print("%-24s %6s %8s %6s %7s %7s %7s %7s" % (
        "role", "agents", "turns", "med.t", "ctx@1", "avg.ctx", "growth", "cost"))
    ranked = sorted(s["roles"].items(), key=lambda kv: -kv[1]["share"])
    for name, r in ranked[:top]:
        line = "%-24s %6d %8d %6d %7s %7s %7s %7s" % (
            name[:24], r["agents"], r["turns"], r["median_turns"], kilo(r["first_ctx"]),
            kilo(r["avg_ctx"]), pct(r["growth_share"]).strip(), pct(r["share"]).strip())
        if base and name in base.get("roles", {}):
            line += "   was %s" % pct(base["roles"][name]["share"]).strip()
        print(line)
    if len(ranked) > top:
        rest = sum(r["share"] for _, r in ranked[top:])
        print("%-24s %s" % ("(%d more roles)" % (len(ranked) - top), pct(rest).strip()))
    print("")
    main = s["roles"].get("main-session")
    if main:
        print("orchestrator/main sessions: %d, %d turns, avg context %s, %d task notifications processed"
              % (main["agents"], main["turns"], kilo(main["avg_ctx"]), s["notifications"]))
    if s["retry_share"] is not None:
        print("retries (attempt 2+): %s of total cost" % pct(s["retry_share"]).strip()
              + (("   was %s" % pct(base["retry_share"]).strip()) if base and base.get("retry_share") is not None else ""))
        hist = s.get("features_by_max_attempt") or {}
        print("features by highest attempt reached: " + "  ".join("%s:%s" % kv for kv in hist.items()))
    if s["per_feature_units"]:
        line = "cost per labelled feature: %.1fM units over %d features" % (s["per_feature_units"] / 1e6, s["features"])
        if base and base.get("per_feature_units"):
            line += "   was %.1fM (%+.0f%%)" % (base["per_feature_units"] / 1e6,
                                               100 * (s["per_feature_units"] / base["per_feature_units"] - 1))
        print(line)
    print("")
    print("growth = share of a role's context tokens beyond each agent's first turn. High growth")
    print("with many turns is what a fresh agent per phase attacks; a high main-session share is")
    print("what a leaner orchestrator attacks; a high retry share is what the attempt policy attacks.")


# --------------------------------------------------------------------------- selftest

def _write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for d in lines:
            fh.write(json.dumps(d) + "\n")


def _turn(mid, ts, inp, cw, cr, out):
    return {"type": "assistant", "timestamp": ts, "message": {"id": mid, "usage": {
        "input_tokens": inp, "cache_creation_input_tokens": cw,
        "cache_read_input_tokens": cr, "output_tokens": out}}}


def selftest():
    tmp = tempfile.mkdtemp(prefix="measure-agents-selftest-")
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    try:
        root = os.path.join(tmp, "proj")
        sess = "s1"
        # Main session: one response split over two lines (must count once), a
        # task notification, and one turn outside the window.
        _write(os.path.join(root, sess + ".jsonl"), [
            _turn("m1", "2026-09-10T10:00:00Z", 10, 100, 0, 5),
            _turn("m1", "2026-09-10T10:00:00Z", 10, 100, 0, 5),
            {"type": "user", "timestamp": "2026-09-10T10:01:00Z",
             "message": {"content": "<task-notification> done"}},
            _turn("m2", "2026-09-10T10:02:00Z", 0, 0, 110, 5),
            _turn("m3", "2026-08-01T10:00:00Z", 0, 0, 999999, 5),
        ])
        wf = os.path.join(root, sess, "subagents", "workflows", "wf_1")
        _write(os.path.join(wf, "agent-a.jsonl"), [
            _turn("b1", "2026-09-10T11:00:00Z", 0, 1000, 0, 10),
            _turn("b2", "2026-09-10T11:01:00Z", 0, 100, 1000, 10),
            _turn("b3", "2026-09-10T11:02:00Z", 0, 100, 1100, 10)])
        json.dump({"agentType": "workflow-subagent", "description": "build:feat-x:1"},
                  open(os.path.join(wf, "agent-a.meta.json"), "w"))
        _write(os.path.join(wf, "agent-b.jsonl"), [_turn("c1", "2026-09-10T12:00:00Z", 0, 500, 0, 10)])
        json.dump({"agentType": "workflow-subagent", "description": "build:feat-x:2"},
                  open(os.path.join(wf, "agent-b.meta.json"), "w"))
        sub = os.path.join(root, sess, "subagents")
        _write(os.path.join(sub, "agent-c.jsonl"), [_turn("d1", "2026-09-10T13:00:00Z", 0, 200, 0, 1)])
        json.dump({"agentType": "Explore", "description": "find things"},
                  open(os.path.join(sub, "agent-c.meta.json"), "w"))

        w = DEFAULT_WEIGHTS
        s = summarise(measure([root], "2026-09-01", None, w), w)
        main = s["roles"].get("main-session", {})
        expect("a response split over two lines counts once", main.get("turns") == 2)
        expect("a turn outside --since is excluded", main.get("avg_ctx") == 110)
        expect("task notifications are counted", s["notifications"] == 1)
        expect("workflow labels give the role", "build" in s["roles"] and s["roles"]["build"]["agents"] == 2)
        expect("Agent-tool subagents are labelled by type", "agent:Explore" in s["roles"])
        b = s["roles"]["build"]
        expect("context at turn 1 is the median first turn", b["first_ctx"] == 750)
        expect("growth is measured beyond each agent's first turn",
               abs(b["growth_share"] - (100 + 200) / (1000 + 1100 + 1200 + 500)) < 1e-9)
        c_att2 = cost_of({"cw": 500, "out": 10}, w)
        expect("retry share is attempt 2+ over total", abs(s["retry_share"] - c_att2 / s["total_units"]) < 1e-9)
        expect("a feature's highest attempt is recorded", s.get("features_by_max_attempt") == {"2": 1})
        expect("class shares sum to 1", abs(sum(s["class_share"].values()) - 1) < 1e-9)
        empty = summarise(measure([root], "2030-01-01", None, w), w)
        expect("an empty window measures nothing", empty["files"] == 0 and not empty["total_units"])
        expect("the project path is encoded the way Claude Code stores it",
               encode_project("/root/.claude/x_y") == "-root--claude-x-y")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


# --------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=".", help="the repository whose sessions to read (default: cwd)")
    ap.add_argument("--transcripts", action="append", default=[],
                    help="an extra transcripts directory, e.g. one for a worktree; repeatable")
    ap.add_argument("--since", help="YYYY-MM-DD, inclusive")
    ap.add_argument("--until", help="YYYY-MM-DD, inclusive")
    ap.add_argument("--weights", help="input,cache_write,cache_read,output (default 1,1.25,0.1,5)")
    ap.add_argument("--top", type=int, default=12, help="roles to list (default 12)")
    ap.add_argument("--baseline", help="a JSON written by --save-baseline, to compare against")
    ap.add_argument("--save-baseline", help="write this measurement as a baseline JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    weights = DEFAULT_WEIGHTS
    if args.weights:
        try:
            weights = tuple(float(x) for x in args.weights.split(","))
            assert len(weights) == 4
        except (ValueError, AssertionError):
            print("--weights needs four numbers: input,cache_write,cache_read,output", file=sys.stderr)
            return 2
    dirs, auto = transcript_dirs(args.project, args.transcripts)
    if not dirs:
        print("no transcripts found. Looked in %s (the project's Claude Code sessions). Pass "
              "--project <repo> or --transcripts <dir>." % auto, file=sys.stderr)
        return 2
    s = summarise(measure(dirs, args.since, args.until, weights), weights)
    if not s["files"]:
        print("the transcripts hold no turn in that window - nothing was measured, which is "
              "not the same as nothing being spent.", file=sys.stderr)
        return 2
    base = None
    if args.baseline:
        try:
            with open(args.baseline, encoding="utf-8") as fh:
                base = json.load(fh)
        except (OSError, ValueError) as e:
            print("could not read the baseline: %s" % e, file=sys.stderr)
            return 2
        if base.get("weights") != list(weights):
            print("! the baseline used different weights; its shares are not comparable", file=sys.stderr)
    print("measured: %s  window: %s .. %s" % (", ".join(dirs), args.since or "start", args.until or "now"))
    report(s, args.top, base)
    if args.save_baseline:
        s["window"] = [args.since, args.until]
        os.makedirs(os.path.dirname(os.path.abspath(args.save_baseline)), exist_ok=True)
        with open(args.save_baseline, "w", encoding="utf-8") as fh:
            json.dump(s, fh, indent=1)
        print("\nbaseline written: %s" % args.save_baseline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
