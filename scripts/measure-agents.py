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
    agents' own, which is how many agents ran at once; how many verifications passed
    and how many were refused; and which stage the other refusals came from (a builder that
    did not finish, a prover that refused, a reviewer's blocker or major, a merge that
    failed), each as what the agent itself returned. On one project the prover and the merger, which run the gate, were about 60%
    of the agent time and about 13% of the relative cost, so a run can be cheap and still slow.

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
import contextlib
import io
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

# What a role's own reply says about its attempt, for the roles whose reply is not a verdict. A reply of another
# shape (a key missing, the wrong type) is not an outcome of that role and is left out of the count.
STAGE_REFUSALS = {
    "build": ("the builder did not finish", lambda o: o["ready"] is False if isinstance(o.get("ready"), bool) else None),
    "prove": ("the prover refused (a red gate or a rebase it could not do)", lambda o: o["ready"] is False if isinstance(o.get("ready"), bool) else None),
    "review": ("the reviewer found a blocker or a major", lambda o: any(isinstance(i, dict) and i.get("severity") in ("blocker", "major") for i in o["issues"]) if isinstance(o.get("issues"), list) else None),
    "merge": ("the merge failed", lambda o: o["ok"] is False if isinstance(o.get("ok"), bool) else None),
}


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
    final = None
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
                    reply = block.get("input")
                    if isinstance(reply, dict):
                        final = reply
                    passed = (reply or {}).get("pass") if isinstance(reply, dict) else None
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
    stamps.sort()
    span = (stamps[-1] - stamps[0]) if stamps else 0.0
    pause = max((b - a for a, b in zip(stamps, stamps[1:])), default=0.0)
    return ctx, totals, notifications, mix, (span, pause, stamps[0] if stamps else None, stamps[-1] if stamps else None), verdict, final


def epoch(ts):
    """Seconds since the epoch for an ISO timestamp, or None. Only differences are used. Before Python 3.11
    fromisoformat takes a fraction of exactly 3 or 6 digits, so any other length is padded to 6."""
    if not ts:
        return None
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(ts).timestamp()
    except ValueError:
        m = re.match(r"^(.*?T\d\d:\d\d:\d\d)\.(\d+)(.*)$", ts)
        if not m:
            return None
        try:
            return datetime.datetime.fromisoformat("%s.%s%s" % (m.group(1), (m.group(2) + "000000")[:6], m.group(3))).timestamp()
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
        "growth_sum": 0, "totals": collections.Counter(), "mix": collections.Counter(), "secs": [], "pause": 0.0})
    verdicts = collections.Counter()
    stages = collections.defaultdict(lambda: [0, 0])  # role -> [agents with an outcome, of them refused]
    by_run = collections.defaultdict(list)  # workflow run id -> [(first, last)] of its agents
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
                ctx, totals, notes, mix, (span, pause, t0, t1), verdict, final = scan(path, since, until)
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
                r["pause"] = max(r["pause"], pause)
                if kind == "workflow-agent" and role == "verify" and verdict is not None:
                    verdicts["said pass" if verdict else "said refuse"] += 1
                if kind == "workflow-agent" and role in STAGE_REFUSALS and final is not None:
                    refused = STAGE_REFUSALS[role][1](final)
                    if refused is not None:
                        stages[role][0] += 1
                        stages[role][1] += 1 if refused else 0
                if kind == "workflow-agent" and t0 is not None:
                    run_id = os.path.basename(os.path.dirname(path))
                    if run_id.startswith("wf_"):
                        by_run[run_id].append((t0, t1))
                classes.update(totals)
                c = cost_of(totals, weights)
                if attempt is not None:
                    attempts[attempt] += c
                if feature:
                    features[feature]["cost"] += c
                    features[feature]["max_attempt"] = max(features[feature]["max_attempt"], attempt or 0)
    return {"roles": roles, "attempts": attempts, "features": features,
            "classes": classes, "notifications": notifications, "files": files,
            "verdicts": verdicts, "stages": {k: tuple(v) for k, v in stages.items()},
            "workflows": workflow_runs(dirs, since, until), "by_run": by_run}


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
                    decided = collections.Counter()
                    for ln in (d.get("logs") or []):
                        m = re.search(r": attempt \d+ (passed verification, refused by the gate|passed|refused)\b", str(ln))
                        if m:
                            decided["passed" if m.group(1) == "passed" else "refused"] += 1
                    runs.append({"id": f[:-len(".json")], "name": d.get("workflowName") or "?", "hours": (d.get("durationMs") or 0) / 3.6e6,
                                 "start": (start or 0) / 1000.0, "secs": (d.get("durationMs") or 0) / 1000.0,
                                 "agents": d.get("agentCount") or 0, "status": d.get("status") or "?", "decided": decided})
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
    # Parallelism is paired per journal: only the agents whose transcripts sit in a run's own folder AND whose turns
    # fall inside the interval that journal covers. Agents of a run with no journal (one still going) and of a run
    # that was resumed (its folder holds the earlier segments too) would otherwise inflate the numerator against a
    # denominator that does not contain them: 1.38 where the paired figure was 1.01, on the project that motivated this.
    paired_agent_secs, paired_run_secs, paired_runs, paired_agents = 0.0, 0.0, 0, 0
    for run in (m.get("workflows") or []):
        slack = 120.0
        inside = [(a, b) for a, b in (m.get("by_run") or {}).get(run["id"], [])
                  if a >= run["start"] - slack and b <= run["start"] + run["secs"] + slack]
        if not inside or not run["secs"]:
            continue
        paired_runs += 1
        paired_agents += len(inside)
        paired_agent_secs += sum(b - a for a, b in inside)
        paired_run_secs += run["secs"]
    runs = m.get("workflows") or []
    out["workflow_runs"] = len(runs)
    out["workflow_hours"] = sum(x["hours"] for x in runs)
    out["parallelism"] = (paired_agent_secs / paired_run_secs) if paired_run_secs else None
    out["parallelism_runs"] = paired_runs
    out["agents_outside_journals"] = max(0, sum(len(v) for v in (m.get("by_run") or {}).values()) - paired_agents)
    out["verified"] = dict(m.get("verdicts") or {})
    out["stages"] = {r: {"agents": n, "refused": k} for r, (n, k) in (m.get("stages") or {}).items()}
    decided = collections.Counter()
    for run in runs:
        decided.update(run["decided"])
    out["pipeline_decisions"] = dict(decided)
    out["longest_pause_min"] = max((r["pause"] for r in m["roles"].values()), default=0.0) / 60.0
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
        line = "workflow agents: %.1f agent-hours; %d journalled run(s) of %.1f h on the clock" % (
            s["agent_hours"], s.get("workflow_runs", 0), s.get("workflow_hours", 0))
        if s.get("parallelism") is not None:
            line += " - %.2f agents at once over the %d run(s) whose agents could be paired with their journal (1.00 = one at a time)" % (
                s["parallelism"], s.get("parallelism_runs", 0))
            if s.get("agents_outside_journals"):
                line += "; %d agent(s) left out of that figure (a run still going, or the earlier part of a resumed one)" % s["agents_outside_journals"]
        else:
            line += " - no run could be paired with its journal, so no parallelism figure"
        if base and base.get("agent_hours"):
            line += "   was %.1f agent-hours" % base["agent_hours"]
        print(line)
    v = s.get("verified") or {}
    if v:
        n = sum(v.values())
        print("verifier verdicts (what each verifier itself returned): %d said pass, %d said refuse (%s)" % (
            v.get("said pass", 0), v.get("said refuse", 0), pct(v.get("said refuse", 0) / n).strip()))
    st = s.get("stages") or {}
    if st:
        print("other stages (what each agent itself returned): " + "; ".join(
            "%s %d of %d" % (STAGE_REFUSALS[r][0], st[r]["refused"], st[r]["agents"]) for r in STAGE_REFUSALS if r in st))
    d = s.get("pipeline_decisions") or {}
    if d:
        n = sum(d.values())
        print("pipeline decisions (attempts, from the journals' logs; they also count the reviewer and the gate): %d passed, %d refused (%s)" % (
            d.get("passed", 0), d.get("refused", 0), pct(d.get("refused", 0) / n).strip()))
    if s.get("longest_pause_min"):
        print("longest pause between two turns of one agent: %.1f min (a gate being waited for counts; so does a suspended host)" % s["longest_pause_min"])
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


def _turn(mid, ts, inp, cw, cr, out, model="claude-sonnet-5-5", effort="high", verdict=None, reply=None):
    d = {"type": "assistant", "timestamp": ts, "effort": effort, "message": {"id": mid, "model": model, "usage": {
        "input_tokens": inp, "cache_creation_input_tokens": cw,
        "cache_read_input_tokens": cr, "output_tokens": out}}}
    if verdict is not None:
        d["message"]["content"] = [{"type": "tool_use", "name": "StructuredOutput", "input": {"pass": verdict, "issues": []}}]
    if reply is not None:
        d["message"]["content"] = [{"type": "tool_use", "name": "StructuredOutput", "input": reply}]
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
        meta = lambda name, desc: json.dump({"agentType": "workflow-subagent", "description": desc}, open(os.path.join(wf, name + ".meta.json"), "w"))
        # The run's journal says it started at 14:00:00Z and lasted 8 minutes. Inside that interval: two builders
        # (120 s and 0 s; the first ends on a StructuredOutput that carries `pass`, which must NOT count: it is no
        # verifier), and three verifiers (360 s, said refuse; 60 s, said pass; 60 s, said pass). Outside it, in the
        # same folder: a `plan` agent from a resumed run's earlier segment (1800 s), which must stay out of the
        # parallelism but is still time the role spent.
        _write(os.path.join(wf, "agent-a.jsonl"), [
            _turn("b1", "2026-09-10T14:00:00Z", 0, 1000, 0, 10),
            _turn("b2", "2026-09-10T14:01:00Z", 0, 100, 1000, 10),
            _turn("b3", "2026-09-10T14:02:00Z", 0, 100, 1100, 10, verdict=True)])
        meta("agent-a", "build:feat-x:1")
        _write(os.path.join(wf, "agent-b.jsonl"), [_turn("c1", "2026-09-10T14:03:00Z", 0, 500, 0, 10)])
        meta("agent-b", "build:feat-x:2")
        _write(os.path.join(wf, "agent-v1.jsonl"), [_turn("v1a", "2026-09-10T14:00:00Z", 0, 100, 0, 1),
                                                   _turn("v1b", "2026-09-10T14:06:00Z", 0, 0, 100, 1, verdict=False)])
        meta("agent-v1", "verify:feat-x:1")
        _write(os.path.join(wf, "agent-v2.jsonl"), [_turn("v2a", "2026-09-10T14:06:00Z", 0, 100, 0, 1),
                                                   _turn("v2b", "2026-09-10T14:07:00Z", 0, 0, 100, 1, verdict=True)])
        meta("agent-v2", "verify:feat-x:1")
        _write(os.path.join(wf, "agent-v3.jsonl"), [_turn("v3a", "2026-09-10T14:07:00Z", 0, 100, 0, 1),
                                                   _turn("v3b", "2026-09-10T14:08:00Z", 0, 0, 100, 1, verdict=True)])
        meta("agent-v3", "verify:feat-x:1")
        _write(os.path.join(wf, "agent-old.jsonl"), [_turn("p1", "2026-09-10T09:00:00Z", 0, 100, 0, 1),
                                                    _turn("p2", "2026-09-10T09:30:00Z", 0, 0, 100, 1)])
        meta("agent-old", "plan:feat-x:1")
        os.makedirs(os.path.join(root, sess, "workflows"), exist_ok=True)
        json.dump({"workflowName": "roadmap-pipeline", "status": "completed", "agentCount": 5, "durationMs": 480000,
                   "startTime": 1789048800000,
                   "logs": ["[roadmap-pipeline] feat-x: attempt 1 refused", "[roadmap-pipeline] feat-x: attempt 2 passed",
                            "[roadmap-pipeline] feat-x: attempt 3 passed verification, refused by the gate", "feat-x: merged"]},
                  open(os.path.join(root, sess, "workflows", "wf_1.json"), "w"))
        # a decoy: a file shaped like a journal inside the transcripts' own folder, which is not one
        json.dump({"workflowName": "decoy", "agentCount": 99, "durationMs": 3600000, "startTime": 1789048800000},
                  open(os.path.join(root, sess, "subagents", "workflows", "wf_9.json"), "w"))
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
        expect("a role's share of time is over workflow agents only (2400 s: build 120, verify 480, plan 1800)",
               abs(s["roles"]["build"]["time_share"] - 120 / 2400) < 1e-9 and abs(s["roles"]["verify"]["time_share"] - 480 / 2400) < 1e-9
               and abs(s["roles"]["plan"]["time_share"] - 1800 / 2400) < 1e-9 and s["roles"]["main-session"]["time_share"] is None)
        expect("the run's clock comes from its journal", s["workflow_runs"] == 1 and abs(s["workflow_hours"] - 480 / 3600) < 1e-9)
        expect("parallelism pairs the agents inside the journal's interval with it: 600 s of agents over 480 s, not 2400 over 480",
               s["parallelism_runs"] == 1 and abs(s["parallelism"] - 600 / 480) < 1e-9)
        expect("the agents left out of the figure are counted", s["agents_outside_journals"] == 1)
        expect("verdicts are the verifiers' own, asymmetric so a swap shows, and a build agent's `pass` is no verdict",
               s["verified"] == {"said pass": 2, "said refuse": 1})
        expect("the pipeline's own decisions come from the journal's log, the gate's refusal counted as one",
               s["pipeline_decisions"] == {"passed": 1, "refused": 2})
        expect("a file shaped like a journal inside the transcripts folder is not one (a decoy says 99 agents)",
               [r["id"] for r in workflow_runs([root], None, None)] == ["wf_1"])
        expect("a journal after --until is left out", workflow_runs([root], None, "2026-09-09") == [])
        expect("a journal inside the window is kept", len(workflow_runs([root], "2026-09-10", "2026-09-10")) == 1)
        expect("a journal before --since is left out", workflow_runs([root], "2030-01-01", None) == [])
        expect("the longest pause between two turns of one agent is reported", abs(s["longest_pause_min"] - 30.0) < 1e-9)
        expect("a fraction of seconds of any length is read",
               abs(epoch("2026-09-10T14:00:00.5Z") - epoch("2026-09-10T14:00:00Z") - 0.5) < 1e-6
               and abs(epoch("2026-09-10T14:00:00.123456789Z") - epoch("2026-09-10T14:00:00Z") - 0.123456) < 1e-6
               and epoch("not a time") is None)
        expect("the project path is encoded the way Claude Code stores it",
               encode_project("/root/.claude/x_y") == "-root--claude-x-y")
        # What the other roles themselves returned: a builder and a prover with ready=false, a reviewer with a major
        # among minors (and one with only minors, and one with none), a merger with ok=false, a verifier (no stage),
        # a builder that never replied and a reviewer whose reply has another shape (neither is an outcome).
        root2 = os.path.join(tmp, "proj2")
        wf2 = os.path.join(root2, "s2", "subagents", "workflows", "wf_2")
        n = [0]

        def agent2(desc, reply):
            n[0] += 1
            name = "agent-%d" % n[0]
            _write(os.path.join(wf2, name + ".jsonl"), [_turn("x%d" % n[0], "2026-09-10T14:00:00Z", 0, 100, 0, 1, reply=reply)])
            json.dump({"agentType": "workflow-subagent", "description": desc}, open(os.path.join(wf2, name + ".meta.json"), "w"))
        agent2("build:f:1", {"ready": False, "summary": "", "blockers": ["x"]})
        agent2("build:f:2", {"ready": True, "summary": "", "blockers": []})
        agent2("build:f:3", None)
        agent2("prove:f:1", {"ready": False, "notes": "", "blockers": []})
        agent2("prove:f:2", {"ready": True, "notes": "", "blockers": []})
        agent2("review:f:1", {"issues": [{"severity": "minor"}, {"severity": "major"}]})
        agent2("review:f:2", {"issues": [{"severity": "minor"}]})
        agent2("review:f:3", {"issues": []})
        agent2("review:f:4", {"verdict": "other shape"})
        agent2("merge:f", {"ok": True, "before": "a", "commit": "b", "notes": ""})
        agent2("merge:g", {"ok": False, "before": "a", "commit": "", "notes": ""})
        agent2("verify:f:1", {"gateExit": 0, "pass": False, "notMet": [], "issues": []})
        s2 = summarise(measure([root2], None, None, w), w)
        expect("each role's own reply is counted as its outcome, a reply of another shape and no reply are not",
               s2["stages"] == {"build": {"agents": 2, "refused": 1}, "prove": {"agents": 2, "refused": 1},
                                "review": {"agents": 3, "refused": 1}, "merge": {"agents": 2, "refused": 1}})
        expect("the verifier keeps its own line and is no stage", s2["verified"] == {"said refuse": 1} and "verify" not in s2["stages"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            report(s2, 12)
        expect("the report names each stage with its own count",
               "the builder did not finish 1 of 2" in buf.getvalue() and "the prover refused" in buf.getvalue()
               and "the reviewer found a blocker or a major 1 of 3" in buf.getvalue() and "the merge failed 1 of 2" in buf.getvalue())
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
