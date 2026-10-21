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
  - the orchestrator: how many task notifications its session processed;
  - TIME, because tokens are not the only price: per workflow role, the wall-clock its
    agents spent (first to last turn) and its share of all workflow-agent time; the
    wall-clock of the workflow runs themselves (from each run's journal) against the
    agents' own, which is how many agents ran at once; and how many verifications passed
    and how many were refused. On one project the gate was 61% of the time and about 2%
    of the tokens, so a run can be cheap and still slow.

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
import datetime
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
BASELINE_VERSION = 1  # the time fields are optional additions; an older baseline simply lacks them


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
    mix = collections.Counter()
    stamps = []
    verdict = None
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
            t = epoch(d.get("timestamp"))
            if t is not None:
                stamps.append(t)
            for block in (msg.get("content") or []) if isinstance(msg.get("content"), list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "StructuredOutput":
                    passed = (block.get("input") or {}).get("pass")
                    if isinstance(passed, bool):
                        verdict = passed
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
            mix["%s/%s" % (short_model(msg.get("model")), d.get("effort") or "?")] += 1
    span = (max(stamps) - min(stamps)) if stamps else 0.0
    return ctx, totals, notifications, mix, span, verdict


def epoch(ts):
    """Seconds since the epoch for an ISO timestamp, or None. Only differences are used."""
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def short_model(m):
    """`claude-sonnet-5-5` -> `sonnet-5-5`; the vendor prefix is noise in a column."""
    return (m or "?").replace("claude-", "")


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
        "growth_sum": 0, "totals": collections.Counter(), "mix": collections.Counter(), "secs": []})
    verdicts = collections.Counter()
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
                ctx, totals, notes, mix, span, verdict = scan(path, since, until)
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
                r["mix"].update(mix)
                r["secs"].append(span)
                if kind == "workflow-agent" and role == "verify" and verdict is not None:
                    verdicts["passed" if verdict else "refused"] += 1
                classes.update(totals)
                c = cost_of(totals, weights)
                if attempt is not None:
                    attempts[attempt] += c
                if feature:
                    features[feature]["cost"] += c
                    features[feature]["max_attempt"] = max(features[feature]["max_attempt"], attempt or 0)
    return {"roles": roles, "attempts": attempts, "features": features,
            "classes": classes, "notifications": notifications, "files": files,
            "verdicts": verdicts, "workflows": workflow_runs(dirs, since, until)}


def workflow_runs(dirs, since, until):
    """The workflow runs' own journals (<session>/workflows/wf_*.json): how long each run took on the
    clock and how many agents it started. A subagent folder of the same name holds transcripts, not these."""
    runs = []
    for root in dirs:
        for dp, _dirs, fs in os.walk(root):
            if os.path.basename(dp) != "workflows" or os.path.basename(os.path.dirname(dp)) == "subagents":
                continue
            for f in fs:
                if not (f.startswith("wf_") and f.endswith(".json")):
                    continue
                try:
                    with open(os.path.join(dp, f), encoding="utf-8") as fh:
                        d = json.load(fh)
                    start = d.get("startTime")
                    day = datetime.datetime.fromtimestamp(start / 1000, datetime.timezone.utc).strftime("%Y-%m-%d") if start else None
                    if (since or until) and not (day and (not since or day >= since) and (not until or day <= until)):
                        continue
                    runs.append({"name": d.get("workflowName") or "?", "hours": (d.get("durationMs") or 0) / 3.6e6,
                                 "agents": d.get("agentCount") or 0, "status": d.get("status") or "?"})
                except (OSError, ValueError, TypeError):
                    continue
    return runs


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
        hours = sum(r["secs"]) / 3600 if r["kind"] == "workflow-agent" else None
        out["roles"][name] = {
            "kind": r["kind"], "agents": r["agents"], "turns": turns,
            "hours": hours, "median_min": (statistics.median(r["secs"]) / 60) if hours is not None else None,
            "median_turns": statistics.median(r["turns"]),
            "first_ctx": statistics.median(r["first_ctx"]),
            "avg_ctx": r["ctx_sum"] / max(turns, 1),
            "growth_share": r["growth_sum"] / max(r["ctx_sum"], 1),
            "share": c / total,
            "model_effort": dict(r["mix"].most_common(3))}
    out["kind_share"] = {k: v / total for k, v in kinds.items()}
    wf_hours = sum(r["hours"] for r in out["roles"].values() if r["hours"] is not None)
    out["agent_hours"] = wf_hours
    for r in out["roles"].values():
        r["time_share"] = (r["hours"] / wf_hours) if (r["hours"] is not None and wf_hours) else None
    runs = m.get("workflows") or []
    out["workflow_runs"] = len(runs)
    out["workflow_hours"] = sum(x["hours"] for x in runs)
    out["parallelism"] = (wf_hours / out["workflow_hours"]) if out["workflow_hours"] else None
    out["verified"] = dict(m.get("verdicts") or {})
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
    print("%-24s %6s %8s %6s %7s %7s %7s %7s %7s %6s  %s" % (
        "role", "agents", "turns", "med.t", "ctx@1", "avg.ctx", "growth", "cost", "time", "med.m", "model/effort (share of turns)"))
    ranked = sorted(s["roles"].items(), key=lambda kv: -kv[1]["share"])
    for name, r in ranked[:top]:
        me = r.get("model_effort") or {}
        me_txt = ", ".join("%s %d%%" % (k, round(100 * v / max(r["turns"], 1))) for k, v in me.items())
        line = "%-24s %6d %8d %6d %7s %7s %7s %7s %7s %6s  %s" % (
            name[:24], r["agents"], r["turns"], r["median_turns"], kilo(r["first_ctx"]),
            kilo(r["avg_ctx"]), pct(r["growth_share"]).strip(), pct(r["share"]).strip(),
            pct(r.get("time_share")).strip() if r.get("time_share") is not None else "-",
            ("%.1f" % r["median_min"]) if r.get("median_min") is not None else "-", me_txt)
        if base and name in base.get("roles", {}):
            line += "   was %s" % pct(base["roles"][name]["share"]).strip()
            if base["roles"][name].get("time_share") is not None and r.get("time_share") is not None:
                line += " of cost, %s of time" % pct(base["roles"][name]["time_share"]).strip()
        print(line)
    if len(ranked) > top:
        rest = sum(r["share"] for _, r in ranked[top:])
        print("%-24s %s" % ("(%d more roles)" % (len(ranked) - top), pct(rest).strip()))
    print("")
    main = s["roles"].get("main-session")
    if main:
        print("orchestrator/main sessions: %d, %d turns, avg context %s, %d task notifications processed"
              % (main["agents"], main["turns"], kilo(main["avg_ctx"]), s["notifications"]))
    if s.get("agent_hours"):
        line = "workflow agents: %.1f agent-hours" % s["agent_hours"]
        if s.get("workflow_runs"):
            line += " in %d run(s) of %.1f h on the clock - %.2f agents at once (1.00 = one at a time)" % (
                s["workflow_runs"], s["workflow_hours"], s["parallelism"] or 0)
        else:
            line += " (no workflow journal found, so no wall-clock for the runs)"
        if base and base.get("agent_hours"):
            line += "   was %.1f agent-hours" % base["agent_hours"]
        print(line)
    v = s.get("verified") or {}
    if v:
        n = sum(v.values())
        print("verifications: %d passed, %d refused (%s refused)" % (v.get("passed", 0), v.get("refused", 0),
                                                                      pct(v.get("refused", 0) / n).strip()))
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
    print("time = a role's share of all workflow-agent wall-clock (first to last turn of each agent); a")
    print("run still going has no journal yet, so its agents count in the agent-hours but not on the clock.")
    print("growth = share of a role's context tokens beyond each agent's first turn. High growth")
    print("with many turns is what a fresh agent per phase attacks; a high main-session share is")
    print("what a leaner orchestrator attacks; a high retry share is what the attempt policy attacks.")


# --------------------------------------------------------------------------- selftest

def _write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for d in lines:
            fh.write(json.dumps(d) + "\n")


def _turn(mid, ts, inp, cw, cr, out, model="claude-sonnet-5-5", effort="high", verdict=None):
    d = {"type": "assistant", "timestamp": ts, "effort": effort, "message": {"id": mid, "model": model, "usage": {
        "input_tokens": inp, "cache_creation_input_tokens": cw,
        "cache_read_input_tokens": cr, "output_tokens": out}}}
    if verdict is not None:
        d["message"]["content"] = [{"type": "tool_use", "name": "StructuredOutput", "input": {"pass": verdict, "issues": []}}]
    return d


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
        # Time: two verifiers (10 minutes then passed, 1 minute then refused) and the run's own journal, 4 minutes
        # on the clock. The agents spent 120 s + 0 s (builds) + 600 s + 60 s = 780 s, so 3.25 agents at once.
        _write(os.path.join(wf, "agent-v1.jsonl"), [_turn("v1a", "2026-09-10T14:00:00Z", 0, 100, 0, 1),
                                                   _turn("v1b", "2026-09-10T14:10:00Z", 0, 0, 100, 1, verdict=True)])
        json.dump({"agentType": "workflow-subagent", "description": "verify:feat-x:1"}, open(os.path.join(wf, "agent-v1.meta.json"), "w"))
        _write(os.path.join(wf, "agent-v2.jsonl"), [_turn("v2a", "2026-09-10T15:00:00Z", 0, 100, 0, 1),
                                                   _turn("v2b", "2026-09-10T15:01:00Z", 0, 0, 100, 1, verdict=False)])
        json.dump({"agentType": "workflow-subagent", "description": "verify:feat-x:1"}, open(os.path.join(wf, "agent-v2.meta.json"), "w"))
        os.makedirs(os.path.join(root, sess, "workflows"), exist_ok=True)
        json.dump({"workflowName": "roadmap-pipeline", "status": "completed", "agentCount": 4, "durationMs": 240000,
                   "startTime": 1789048800000}, open(os.path.join(root, sess, "workflows", "wf_1.json"), "w"))
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
        expect("the model and effort each role ran at are recorded",
               s["roles"]["build"]["model_effort"] == {"sonnet-5-5/high": 4})
        expect("a workflow role's wall-clock is first to last turn", abs(s["roles"]["build"]["hours"] - 120 / 3600) < 1e-9
               and s["roles"]["build"]["median_min"] == 1.0)
        expect("a role's share of time is over workflow agents only", abs(s["roles"]["build"]["time_share"] - 120 / 780) < 1e-9
               and abs(s["roles"]["verify"]["time_share"] - 660 / 780) < 1e-9 and s["roles"]["main-session"]["time_share"] is None)
        expect("the run's clock comes from its journal and gives the parallelism",
               s["workflow_runs"] == 1 and abs(s["workflow_hours"] - 240 / 3600) < 1e-9 and abs(s["parallelism"] - 3.25) < 1e-9)
        expect("verifications are counted as passed and refused", s["verified"] == {"passed": 1, "refused": 1})
        expect("a subagent folder named workflows is not mistaken for a journal",
               len(workflow_runs([root], None, None)) == 1)
        expect("a journal outside the window is left out", workflow_runs([root], "2030-01-01", None) == [])
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
