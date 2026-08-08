#!/usr/bin/env python3
"""Validate a generated roadmap against the rules that produced it.

decompose-phase.md closes with eleven sanity checks, and until now every one of
them was applied by reading. A full review of 3.6.0 found that the checks the
skill states cover what is countable and skip what is derived -- and that the
derived ones are where the cheapest mistakes live, because nothing catches them.
This turns them into a command.

It is a linter, not a gate: it never edits, and a finding is a question for the
person who owns the roadmap. Where a file cannot be parsed with confidence the
check reports SKIP rather than failing -- a false failure on somebody's real
backlog costs more than a missed one.

    python3 check-roadmap.py                     # every roadmap under docs/
    python3 check-roadmap.py --root DIR
    python3 check-roadmap.py docs/ROADMAP-pay.md # just one

Exit codes: 0 clean (warnings allowed), 1 at least one check failed, 2 usage.
"""

import argparse
import glob
import os
import re
import sys

# tlc-spec-driven v3.x's rubric, from its references/specify.md. A different
# downstream skill has its own; the count is reported, never enforced blindly.
RUBRIC_THEMES = 9
MAX_TASKS = 8
WARN_TOKENS, ACT_TOKENS = 2000, 3000
DISCHARGE = "discharge: no code — answered open question or context.md"
DIMENSIONS = ["persistence", "state", "external call", "auth", "payment",
              "concurrency", "state transition"]

RESULTS = []


def record(kind, roadmap, check, detail=""):
    RESULTS.append((kind, roadmap, check, detail))


def ok(rm, c, d=""):
    record("ok", rm, c)


def fail(rm, c, d):
    record("fail", rm, c, d)


def warn(rm, c, d):
    record("warn", rm, c, d)


def skip(rm, c, d):
    record("skip", rm, c, d)


# --------------------------------------------------------------------------
# parsing -- tolerant on purpose
# --------------------------------------------------------------------------

def strip_fences(text):
    out, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append("")
            continue
        out.append("" if fence else line)
    return "\n".join(out)


def block(text, heading):
    """Body of a '## Heading', to the next heading of any level. Fence-aware."""
    lines = strip_fences(text).splitlines()
    start = None
    for i, line in enumerate(lines):
        if start is None:
            if line.rstrip().lower() == heading.lower():
                start = i
        elif re.match(r"^#{1,6}\s", line):
            return "\n".join(lines[start + 1:i])
    return "\n".join(lines[start + 1:]) if start is not None else None


FIELD_RE = re.compile(r"^\s*[-*]\s*\*{0,2}([A-Za-z][A-Za-z .\-/]*?)\*{0,2}\s*:\s*(.*)$")


def parse_features(text):
    """[(name, {field: value}, raw_body)] from '### <name>' sections, in order."""
    lines = strip_fences(text).splitlines()
    feats, cur, body = [], None, []
    for line in lines:
        m = re.match(r"^###\s+`?([A-Za-z0-9][\w.-]*)`?\s*$", line)
        if m:
            if cur:
                feats.append((cur, body))
            cur, body = m.group(1), []
        elif re.match(r"^#{1,3}\s", line) and cur:
            feats.append((cur, body))
            cur, body = None, []
        elif cur is not None:
            body.append(line)
    if cur:
        feats.append((cur, body))

    out = []
    for name, body in feats:
        fields, last = {}, None
        for line in body:
            fm = FIELD_RE.match(line)
            if fm:
                last = fm.group(1).strip().lower()
                fields[last] = fm.group(2).strip()
            elif last and line.strip().startswith("-"):
                fields[last] = (fields[last] + " | " + line.strip().lstrip("- ")).strip(" |")
        out.append((name, fields, "\n".join(body)))
    return out


def field(fields, *names):
    for n in names:
        for k, v in fields.items():
            if k.startswith(n):
                return v
    return None


def txt_names(path):
    if not os.path.isfile(path):
        return None
    names = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                names.append(line)
    return names


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def check_forward_deps(rm, feats):
    seen, bad = [], []
    for name, fields, _ in feats:
        dep = field(fields, "depends on", "depends")
        if dep and dep not in ("—", "-", "none", "None"):
            for d in re.findall(r"`?([a-z0-9]+(?:-[a-z0-9]+)+)`?", dep):
                if d not in seen and any(d == n for n, _, _ in feats):
                    bad.append("%s depends on %s, which is listed after it" % (name, d))
        seen.append(name)
    (ok if not bad else fail)(rm, "no forward dependencies", "\n".join(bad))


def check_duplicate_names(rm, feats, txt):
    names = [n for n, _, _ in feats]
    dups = sorted({n for n in names if names.count(n) > 1})
    if txt:
        dups += sorted({n for n in txt if txt.count(n) > 1 and n not in dups})
    (ok if not dups else fail)(rm, "no name used twice", ", ".join(dups))


def check_task_estimate(rm, feats):
    over, missing = [], []
    for name, fields, _ in feats:
        v = field(fields, "task estimate", "tasks")
        if v is None:
            missing.append(name)
            continue
        m = re.search(r"\d+", v)
        if m and int(m.group(0)) > MAX_TASKS:
            over.append("%s: %s" % (name, m.group(0)))
    if over:
        fail(rm, "task estimate within budget (<=%d)" % MAX_TASKS, "\n".join(over))
    elif missing and len(missing) == len(feats):
        skip(rm, "task estimate within budget", "no feature carries the field")
    else:
        ok(rm, "task estimate within budget (<=%d)" % MAX_TASKS)


def check_discharge(rm, feats, text):
    carriers = [n for n, _, b in feats if DISCHARGE in b]
    loose = [n for n, _, b in feats
             if n not in carriers and re.search(r"discharge\s*:", b, re.I)]
    if loose:
        fail(rm, "discharge line is verbatim",
             "these carry a discharge: line that is not the exact wording: " + ", ".join(loose)
             + "\nthe seed matches it literally — a paraphrase strands the feature")
    else:
        ok(rm, "discharge line is verbatim%s"
           % (" (%d question-only)" % len(carriers) if carriers else ""))


def check_open_questions(rm, feats, text):
    rollup = block(text, "## Open Questions")
    if rollup is None:
        infield = [n for n, f, _ in feats
                   if (field(f, "open question") or "none").lower() not in ("none", "—", "-", "")]
        if infield:
            fail(rm, "open questions roll-up exists",
                 "features carry open questions but there is no `## Open Questions` section: "
                 + ", ".join(infield))
        else:
            ok(rm, "open questions roll-up (none needed)")
        return

    missing = []
    for name, fields, _ in feats:
        v = field(fields, "open question")
        if not v or v.lower() in ("none", "—", "-"):
            continue
        if name not in rollup:
            missing.append(name)
    orphan_status = []
    for line in rollup.splitlines():
        if re.search(r"status\s*:\s*open", line, re.I) or re.search(r"status\s*:\s*answered", line, re.I):
            if not re.search(r"cross-cutting", line, re.I):
                named = [n for n, _, _ in feats if n in line]
                if not named:
                    orphan_status.append(line.strip()[:90])
    detail = []
    if missing:
        detail.append("carried by a feature but absent from the roll-up: " + ", ".join(missing))
    if orphan_status:
        detail.append("roll-up entries naming no feature and not tagged `cross-cutting`:\n  "
                      + "\n  ".join(orphan_status))
    (ok if not detail else fail)(rm, "open questions agree in both directions", "\n".join(detail))


def check_ledger(rm, text):
    led = block(text, "## Cross-Cutting Decisions")
    if led is None:
        skip(rm, "cross-cutting ledger", "no block here (multi-section keeps it in the index)")
        return
    rows = [l for l in led.splitlines()
            if l.strip().startswith("|") and not re.match(r"^\s*\|[\s|:-]+\|\s*$", l)]
    rows = [r for r in rows if not re.search(r"\bTheme\b", r, re.I)]
    states = {"decided": 0, "n/a": 0, "not decided": 0, "deferred": 0}
    for r in rows:
        low = r.lower()
        if "deferred to feature" in low:
            states["deferred"] += 1
        elif "not decided" in low:
            states["not decided"] += 1
        elif "n/a because" in low:
            states["n/a"] += 1
        else:
            states["decided"] += 1
    if not rows:
        warn(rm, "cross-cutting ledger has one row per theme",
             "the block is present but no table rows were found")
        return
    summary = "%d rows: %d decided, %d N/A, %d not decided, %d deferred" % (
        len(rows), states["decided"], states["n/a"], states["not decided"], states["deferred"])
    if len(rows) != RUBRIC_THEMES:
        warn(rm, "cross-cutting ledger has one row per theme",
             summary + " — tlc-spec-driven v3.x's rubric has %d themes; a different downstream "
                       "skill has its own count, so check before treating this as wrong."
                       % RUBRIC_THEMES)
    else:
        ok(rm, "cross-cutting ledger has one row per theme (%s)" % summary)

    unresolved = []
    rollup = block(text, "## Open Questions") or ""
    for r in rows:
        if "not decided" in r.lower() and "deferred to feature" not in r.lower():
            theme = r.strip("| ").split("|")[0].strip()
            hit = [l for l in rollup.splitlines()
                   if theme and theme.lower() in l.lower() and "cross-cutting" in l.lower()]
            if not hit:
                unresolved.append("%r has a `not decided` row with no `cross-cutting` entry "
                                  "naming it in `## Open Questions`" % theme)
            elif not any("affects:" in l.lower() for l in hit):
                unresolved.append("%r has a `cross-cutting` entry with no `affects:` line" % theme)
    (ok if not unresolved else fail)(rm, "every `not decided` row has its question",
                                     "\n".join(unresolved))


def check_disjoint(rm, text, feats):
    gray = block(text, "## Expected Gray Areas")
    rollup = block(text, "## Open Questions")
    if gray is None or rollup is None:
        skip(rm, "gray areas and open questions are disjoint", "one of the two blocks is absent")
        return
    gl = [l.strip(" -*") for l in gray.splitlines() if l.strip().startswith(("-", "*"))]
    overlap = []
    for line in gl:
        key = re.sub(r"[^a-z ]", " ", line.lower())
        words = [w for w in key.split() if len(w) > 5]
        if len(words) >= 4 and sum(w in rollup.lower() for w in words) >= 4:
            overlap.append(line[:90])
    (ok if not overlap else warn)(rm, "gray areas and open questions are disjoint",
                                  "these look like they appear in both:\n  " + "\n  ".join(overlap)
                                  if overlap else "")


def check_coverage(rm, text):
    body = block(text, "## Coverage") or text
    m = re.search(r"uncovered:\s*(\w+)", body, re.I)
    if not m:
        warn(rm, "coverage closes with `uncovered: none`",
             "no `uncovered:` line found — decompose-phase Step 8 requires one")
        return
    (ok if m.group(1).lower() == "none" else fail)(
        rm, "coverage closes with `uncovered: none`",
        "" if m.group(1).lower() == "none" else "reads `uncovered: %s`" % m.group(1))


def check_context_flag(rm, feats):
    wrong = []
    for name, fields, _ in feats:
        flagv = field(fields, "needs pre-written context", "needs context")
        if flagv is None:
            continue
        dims = (field(fields, "implicit dimension") or "none").lower()
        oq = (field(fields, "open question") or "none").lower()
        expect = ("none" not in dims and dims.strip() not in ("", "—", "-")) \
            or re.search(r"status\s*:\s*open", oq) is not None
        got = flagv.strip().lower().startswith("y")
        if expect != got:
            wrong.append("%s: reads %r, but dimensions=%r and open question present=%s"
                         % (name, flagv.strip(), dims[:40],
                            bool(re.search(r"status\s*:\s*open", oq))))
    if not any(field(f, "needs pre-written context", "needs context") for _, f, _ in feats):
        skip(rm, "`needs pre-written context.md` is derived correctly", "no feature carries it")
    else:
        (ok if not wrong else fail)(rm, "`needs pre-written context.md` is derived correctly",
                                    "\n".join(wrong))


def check_txt_agreement(rm, feats, txt, txt_path):
    if txt is None:
        fail(rm, "build-order .txt agrees with the roadmap",
             "%s is missing — the seed counts its lines to compute progress" % txt_path)
        return
    names = [n for n, _, _ in feats]
    only_txt = [n for n in txt if n not in names]
    only_md = [n for n in names if n not in txt]
    detail = []
    if only_txt:
        detail.append("in the .txt but not a `### ` entry: " + ", ".join(only_txt))
    if only_md:
        detail.append("a `### ` entry but not in the .txt: " + ", ".join(only_md))
    if not detail and txt != names:
        detail.append("same names, different order — the .txt is the build order the seed walks")
    (ok if not detail else fail)(rm, "build-order .txt agrees with the roadmap", "\n".join(detail))


def check_size(rm, text):
    tokens = int(len(text.split()) * 1.3)
    if tokens >= ACT_TOKENS:
        warn(rm, "roadmap size", "~%d tokens — past the %d mark where decompose-phase re-raises "
             "the single-vs-multi question. The `/loop` prompt names this file as spec source for "
             "every feature it builds." % (tokens, ACT_TOKENS))
    elif tokens >= WARN_TOKENS:
        warn(rm, "roadmap size", "~%d tokens — approaching the %d mark (roughly %d more features)"
             % (tokens, ACT_TOKENS, max(1, (ACT_TOKENS - tokens) // 220)))
    else:
        ok(rm, "roadmap size (~%d tokens)" % tokens)


def check_global_names(root, all_feats):
    seen, dups = {}, []
    for rm, feats in all_feats.items():
        for name, _, _ in feats:
            if name in seen and seen[name] != rm:
                dups.append("%s appears in both %s and %s" % (name, seen[name], rm))
            seen[name] = rm
    spec = os.path.join(root, ".specs", "features")
    orphan = []
    if os.path.isdir(spec):
        for d in sorted(os.listdir(spec)):
            if os.path.isdir(os.path.join(spec, d)) and d not in seen:
                orphan.append(d)
    rm = "(project)"
    (ok if not dups else fail)(rm, "feature names are globally unique", "\n".join(dups))
    if orphan:
        warn(rm, "every built feature is still named by a roadmap",
             "these have a `.specs/features/` directory but appear in no roadmap: "
             + ", ".join(orphan)
             + "\nrule 6 freezes names at directory existence — a rename makes verified work "
               "look unbuilt")
    elif os.path.isdir(spec):
        ok(rm, "every built feature is still named by a roadmap")


# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roadmap", nargs="*", help="specific roadmap files (default: all under docs/)")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    paths = [os.path.abspath(p) for p in args.roadmap]
    if not paths:
        docs = os.path.join(root, "docs")
        if not os.path.isdir(docs):
            print("no docs/ at %s — nothing to check" % root, file=sys.stderr)
            return 2
        paths = sorted(glob.glob(os.path.join(docs, "ROADMAP.md"))
                       + [p for p in glob.glob(os.path.join(docs, "ROADMAP-*.md"))
                          if not p.endswith("ROADMAP-INDEX.md")])
    if not paths:
        print("no roadmap found under docs/ — nothing to check", file=sys.stderr)
        return 2

    all_feats = {}
    for path in paths:
        rm = os.path.relpath(path, root)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        feats = parse_features(text)
        all_feats[rm] = feats
        if not feats:
            skip(rm, "parse", "no `### <feature-name>` entries found — is this a roadmap?")
            continue
        base = os.path.basename(path)
        tp = os.path.join(os.path.dirname(path),
                          "roadmap.txt" if base == "ROADMAP.md"
                          else "roadmap-%s.txt" % base[len("ROADMAP-"):-3])
        txt = txt_names(tp)
        check_forward_deps(rm, feats)
        check_duplicate_names(rm, feats, txt)
        check_task_estimate(rm, feats)
        check_discharge(rm, feats, text)
        check_open_questions(rm, feats, text)
        check_ledger(rm, text)
        check_disjoint(rm, text, feats)
        check_coverage(rm, text)
        check_context_flag(rm, feats)
        check_txt_agreement(rm, feats, txt, os.path.relpath(tp, root))
        check_size(rm, text)
    check_global_names(root, all_feats)

    cur = None
    for kind, rm, check, detail in RESULTS:
        if rm != cur:
            print(("\n" if cur else "") + rm)
            cur = rm
        mark = {"ok": "✓", "fail": "✗", "warn": "!", "skip": "·"}[kind]
        print("  %s %s" % (mark, check))
        if detail:
            for line in detail.rstrip().splitlines():
                print("      " + line)

    n = {k: sum(1 for r in RESULTS if r[0] == k) for k in ("ok", "fail", "warn", "skip")}
    print("\n%d passed, %d failed, %d warnings, %d skipped"
          % (n["ok"], n["fail"], n["warn"], n["skip"]))
    if n["fail"]:
        print("\nA failure is a question for whoever owns this roadmap, not a verdict — "
              "read the detail before changing anything.")
    return 1 if n["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
