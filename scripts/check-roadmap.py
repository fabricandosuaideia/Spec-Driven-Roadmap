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



# tlc-spec-driven v3.x's rubric, from its references/specify.md. A different
# downstream skill has its own; the count is reported, never enforced blindly.
RUBRIC_THEMES = 9
MAX_TASKS = 8
WARN_TOKENS, ACT_TOKENS = 2000, 3000
DISCHARGE = "discharge: no code — answered open question or context.md"

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


# Both separators. decompose-phase.md Step 6 specifies the fields as
# `- **objective** — one sentence.` while the guide's worked example renders them
# as `- Objective: ...`. Accepting only the colon made an entry written in the
# documented form parse to zero fields, and every field check then skipped —
# a roadmap with a forward dependency and a 40-task feature came out green.
FIELD_RE = re.compile(
    r"^\s*[-*]\s*\*{0,2}([A-Za-z][A-Za-z .\-/]*?)\*{0,2}\s*(?::|—|–|\s-\s)\s*(.*)$")


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
            # A label Step 6 does not name is not a field — it is a sub-bullet of
            # the field above. Accepting any letters made a question written as
            # `- Qual regra de senha...? status: open` under `- **open questions**`
            # parse as a NEW field, leaving `open questions` empty and the
            # open-question check green on a roadmap full of them. The one real
            # run that escaped did so only because its author happened to prefix
            # every sub-bullet with `(A1)` — a convention no reference prescribes.
            if fm and not any(fm.group(1).strip().lower().startswith(n)
                              for n in KNOWN_FIELDS):
                fm = None
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


# Step 6's field labels, in the spellings `field()` looks up. `name` is
# deliberately not here: the `### ` heading already carries it and no check below
# reads a `- name` line, so an entry whose one English label was that would still
# leave every per-feature check with nothing to read.
KNOWN_FIELDS = ("objective", "scope-unit", "depends", "external contract", "size",
                "task estimate", "tasks", "implicit dimension", "open question",
                "needs pre-written context", "needs context", "discharge")


def has_known_field(fields):
    """True when an entry produced at least one label Step 6 names.

    Accepting only the colon used to make the documented `field — value` form
    parse to zero fields. Accepting both separators fixed that half and left the
    other: an entry whose labels are translated parses to a full dict of keys no
    check knows, every `field()` lookup returns None, and the per-feature checks
    then skip or pass on nothing at all. Both halves are the same parse failure,
    and the gate in main() treats them as one."""
    return any(k.startswith(n) for k in fields for n in KNOWN_FIELDS)


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


def reads_as_none(v):
    """Whether an `open questions` value means "nothing pending here".

    Exact equality with "none" made `none — <reason>` a failure, and that is a
    shape Step 6 itself prints one field above ("none — originated from `<X>`"),
    so the linter was failing a roadmap for obeying the reference. A `status:`
    marker anywhere on the line means a real question is on it whatever the line
    opens with — which is how check_context_flag already reads this same field,
    and the disagreement between two checks of one field was the bug's shape.
    `\\bnone` and not `startswith`: "None of the roles are named" is a question."""
    v = (v or "").strip()
    if v in ("", "—", "-"):
        return True
    if re.search(r"status\s*:", v, re.I):
        return False
    return re.match(r"none\b", v, re.I) is not None


def check_open_questions(rm, feats, text):
    rollup = block(text, "## Open Questions")
    if rollup is None:
        infield = [n for n, f, _ in feats
                   if not reads_as_none(field(f, "open question"))]
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
        if reads_as_none(v):
            continue
        if name not in rollup:
            missing.append(name)
    # Group by bullet, not by physical line. An entry is free to wrap -- markdown
    # does not care and the reference never asked for one line each -- but reading
    # line by line split a wrapped entry into a fragment holding `status: open`
    # and a fragment holding the feature name, and then failed on the half that
    # named nothing. A line starting with `-`/`*` opens an entry; anything after
    # it that is not a bullet belongs to it.
    entries, cur = [], None
    for line in rollup.splitlines():
        if line.strip().startswith(("-", "*")):
            if cur is not None:
                entries.append(cur)
            cur = line.strip()
        elif cur is not None and line.strip():
            cur += " " + line.strip()
    if cur is not None:
        entries.append(cur)
    orphan_status = []
    for entry in entries:
        if re.search(r"status\s*:\s*(open|answered)", entry, re.I):
            if not re.search(r"cross-cutting", entry, re.I):
                named = [n for n, _, _ in feats if n in entry]
                if not named:
                    orphan_status.append(entry[:90])
    detail = []
    if missing:
        detail.append("carried by a feature but absent from the roll-up: " + ", ".join(missing))
    if orphan_status:
        detail.append("roll-up entries naming no feature and not tagged `cross-cutting`:\n  "
                      + "\n  ".join(orphan_status))
    (ok if not detail else fail)(rm, "open questions agree in both directions", "\n".join(detail))


def check_ledger(rm, text, root=None, path=None):
    led = block(text, "## Cross-Cutting Decisions")
    source = rm
    looked_in = None
    if led is None and path:
        # Multi-section keeps the ledger in the index — exactly one per project.
        # Skipping here meant the ledger was never checked at all in that mode,
        # which is the mode where it matters most: every section roadmap defers
        # to it, so an unanswered theme reaches every one of them.
        idx = os.path.join(os.path.dirname(path), "ROADMAP-INDEX.md")
        if os.path.isfile(idx):
            looked_in = os.path.relpath(idx, root or os.path.dirname(path))
            with open(idx, encoding="utf-8") as fh:
                led = block(fh.read(), "## Cross-Cutting Decisions")
            source = looked_in
    if led is None:
        if looked_in:
            # The index is right there and was read. Saying "no index beside it"
            # was simply false, and this is not a file that could not be parsed:
            # it is a mandatory block that exists nowhere, which is what
            # check_coverage warns about in the same situation.
            warn(rm, "cross-cutting ledger",
                 "no `## Cross-Cutting Decisions` here, and none in %s either — "
                 "multi-section keeps exactly one per project, in the index, and "
                 "every section roadmap defers to it" % looked_in)
        else:
            skip(rm, "cross-cutting ledger", "no block here and no index beside it")
        return
    if source != rm:
        record("ok", rm, "cross-cutting ledger read from %s" % source)
    rows = [l for l in led.splitlines()
            if l.strip().startswith("|") and not re.match(r"^\s*\|[\s|:-]+\|\s*$", l)]
    rows = [r for r in rows if not re.search(r"\bTheme\b", r, re.I)]
    # decompose-phase Step 7a: a decision that passes the three tests but matches
    # no rubric theme gets a `project-specific` row. It obeys every other rule but
    # is not one of the nine, so counting it against them reports a false surplus.
    extra = [r for r in rows if re.search(r"project-specific", r, re.I)]
    rows = [r for r in rows if r not in extra]
    # `extra` leaves the theme count but NOT the pairing guard below: a
    # project-specific row left `not decided` still needs its `cross-cutting`
    # entry, or the decision the sweep surfaced has no question anywhere.
    paired = rows + extra
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
    summary = "%d rubric rows: %d decided, %d N/A, %d not decided, %d deferred%s" % (
        len(rows), states["decided"], states["n/a"], states["not decided"], states["deferred"],
        " (+%d project-specific)" % len(extra) if extra else "")
    if len(rows) != RUBRIC_THEMES:
        warn(rm, "cross-cutting ledger has one row per theme",
             summary + " — tlc-spec-driven v3.x's rubric has %d themes; a different downstream "
                       "skill has its own count, so check before treating this as wrong."
                       % RUBRIC_THEMES)
    else:
        ok(rm, "cross-cutting ledger has one row per theme (%s)" % summary)

    unresolved = []
    rollup = block(text, "## Open Questions") or ""
    for r in paired:
        if "not decided" in r.lower() and "deferred to feature" not in r.lower():
            theme = r.strip("| ").split("|")[0].strip()
            # Same bullet-grouping the roll-up check uses. Splitting on physical
            # lines here made a wrapped entry invisible to one check and visible
            # to the other, on the same file.
            entries, cur = [], ""
            for ln in rollup.splitlines():
                if ln.strip().startswith(("-", "*")):
                    if cur:
                        entries.append(cur)
                    cur = ln.strip()
                elif cur and ln.strip():
                    cur += " " + ln.strip()
            if cur:
                entries.append(cur)
            hit = [e for e in entries
                   if theme and theme.lower() in e.lower() and "cross-cutting" in e.lower()]
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


# The skill writes its output in the source document's language (scope-phase's
# carve-out keeps only names and headings in English), so these have to read
# more than English or the check silently passes every non-English roadmap.
MISFILED = re.compile(
    r"feature[- ]local|local (?:a|à|de) (?:uma )?feature|"
    r"cheap to reverse|barato (?:de|para) reverter|f[aá]cil de reverter|"
    r"barato de revertir|local a una feature|"
    r"test 2|test 3|teste 2|teste 3|prueba 2|prueba 3", re.I)
# Deliberately broad: a false accusation here costs more than a missed line,
# because the fix it suggests is to move a question into the loop's sweep.
LIVES_IN = re.compile(
    r"\bcode\b|\bconfig|convention|default|documented|"
    r"c[oó]digo|configura|conven[cç]|padr[aã]o|documenta|"
    r"biblioteca|library|librer[ií]a|schema|migration", re.I)


def check_gray_area_reasons(rm, text):
    """Step 7b: failing test 1 is the only route into this block.

    `feature-local` and `cheap to reverse` are the routing tests, not reasons to
    file something here — a decision only the user can make that happens to be
    small belongs in its feature's `open questions`, which the loop gate sweeps.
    This block is swept by nothing, so a user-only decision parked here gets a
    default with no one asked, which is rule 1's silent default relabelled."""
    gray = block(text, "## Expected Gray Areas")
    if gray is None:
        skip(rm, "gray-area lines say where the answer already lives", "no such block")
        return
    lines = [l.strip() for l in gray.splitlines() if l.strip().startswith(("-", "*"))]
    if not lines:
        skip(rm, "gray-area lines say where the answer already lives", "block present but empty")
        return
    misfiled = [l[:100] for l in lines if MISFILED.search(l)]
    silent = [l[:100] for l in lines if not MISFILED.search(l) and not LIVES_IN.search(l)]
    detail = []
    if misfiled:
        detail.append("reason is a routing test, not test 1 — these belong in the feature's "
                      "`open questions`:\n  " + "\n  ".join(misfiled))
    if silent:
        detail.append("no stated place where the answer already lives:\n  " + "\n  ".join(silent))
    (ok if not detail else fail)(rm, "gray-area lines say where the answer already lives",
                                 "\n".join(detail))


def check_coverage(rm, text):
    # Falling back to the whole file when there is no `## Coverage` heading used
    # to be silent, and silence here reads as a pass: any sentence of prose
    # saying "uncovered: none" satisfied the check, while the real table said
    # otherwise. Where this script cannot scope a read it says so instead --
    # decompose-phase.md promises exactly that.
    body = block(text, "## Coverage")
    scoped = body is not None
    m = re.search(r"uncovered:\s*(\w+)", body if scoped else text, re.I)
    if not m:
        warn(rm, "coverage closes with `uncovered: none`",
             "no `uncovered:` line found — decompose-phase Step 8 requires one")
    elif m.group(1).lower() != "none":
        fail(rm, "coverage closes with `uncovered: none`", "reads `uncovered: %s`" % m.group(1))
    elif scoped:
        ok(rm, "coverage closes with `uncovered: none`")
    else:
        warn(rm, "coverage closes with `uncovered: none`",
             "no `## Coverage` heading — the `uncovered:` line was matched anywhere in the file, so "
             "this pass is not scoped to the coverage table. decompose-phase Step 8's output shape "
             "names that heading.")


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


# decompose-phase.md's size bullet: the answer to a re-raised single-vs-multi
# question is recorded on a plain line between the H1 and `## Status`, the one
# spot no other reader rewrites. Without it "asked the user and they confirmed"
# and "never asked" produce the same warning forever.
SIZE_ACK = re.compile(r"^size re-raised\b", re.M | re.I)

# Roughly 230 tokens per feature over roughly 900 of fixed overhead, regressed
# against real roadmaps; decompose-phase.md's size bullet states the same two
# numbers and must move with this one.
TOKENS_PER_FEATURE = 230


def check_size(rm, text):
    # len/4, not words*1.3. Measured against tiktoken on four generated roadmaps,
    # words*1.3 ran ~31% low and put a 2,484-token file in the clear; len/4
    # classified all four correctly.
    tokens = len(text) // 4
    if tokens >= ACT_TOKENS and SIZE_ACK.search(text):
        ok(rm, "roadmap size (~%d tokens — oversize acknowledged)" % tokens)
    elif tokens >= ACT_TOKENS:
        warn(rm, "roadmap size", "~%d tokens — past the %d mark where decompose-phase re-raises "
             "the single-vs-multi question. The `/loop` prompt names this file as spec source for "
             "every feature it builds." % (tokens, ACT_TOKENS))
    elif tokens >= WARN_TOKENS:
        warn(rm, "roadmap size", "~%d tokens — approaching the %d mark (roughly %d more features)"
             % (tokens, ACT_TOKENS, max(1, (ACT_TOKENS - tokens) // TOKENS_PER_FEATURE)))
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
        fieldless = [n for n, f, _ in feats if not f]
        if fieldless:
            fail(rm, "every feature entry yields parseable fields",
                 "these `### ` entries produced no recognisable `- <field>` lines: "
                 + ", ".join(fieldless[:8])
                 + "\nEvery per-feature check below is vacuous for them, so a green "
                   "result here would mean nothing. Check the separator: the fields "
                   "are `- **objective** — value` or `- Objective: value`.")
        unlabelled = [n for n, f, _ in feats if f and not has_known_field(f)]
        if unlabelled:
            fail(rm, "feature fields carry their documented English labels",
                 "these entries parse into fields, but not one of them is a label "
                 "decompose-phase.md Step 6 names: " + ", ".join(unlabelled[:8])
                 + "\nThe per-feature checks below look those up by exact name, so "
                   "translated or renamed labels make them tick green or skip "
                   "without reading anything. Field labels stay English whatever "
                   "language the roadmap's prose is in (scope-phase.md's carve-out); "
                   "only the value after the label is translated.")
        base = os.path.basename(path)
        tp = os.path.join(os.path.dirname(path),
                          "roadmap.txt" if base == "ROADMAP.md"
                          else "roadmap-%s.txt" % base[len("ROADMAP-"):-3])
        txt = txt_names(tp)
        # Failing the two gates above is not enough on its own: the four checks
        # that look a field up by name would still run, read None everywhere, and
        # print `✓ no forward dependencies` and `✓ open questions agree in both
        # directions` under the failure that just said they mean nothing. A green
        # is a claim, so they are held back and one line says so instead.
        legible = any(has_known_field(f) for _, f, _ in feats)
        if not legible:
            skip(rm, "the checks that read Step 6's fields by name",
                 "held back — no entry yields a label they know, so each would report "
                 "green having read nothing. The failure above names the entries.")
        if legible:
            check_forward_deps(rm, feats)
        check_duplicate_names(rm, feats, txt)
        if legible:
            check_task_estimate(rm, feats)
        check_discharge(rm, feats, text)
        if legible:
            check_open_questions(rm, feats, text)
        check_ledger(rm, text, root, path)
        check_disjoint(rm, text, feats)
        check_gray_area_reasons(rm, text)
        check_coverage(rm, text)
        if legible:
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
