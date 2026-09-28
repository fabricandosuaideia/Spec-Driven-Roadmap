#!/usr/bin/env python3
"""Print what one feature's builder needs from the roadmap, and nothing else. Read-only.

Why this exists: an agent that builds a feature pays, on every later turn, for
everything it read on the way in — measured on a real multi-agent build, 75% of
the relative cost was context re-read, and every agent's context only grew. The
roadmap files this skill writes are shared by the whole backlog: on the two real
projects they reach 80-190 KB, and a builder told to "read the roadmap" loads
all of it to use one entry. This prints the one entry plus exactly the lines
that bind it:

  - the feature's own `### <feature>` entry, verbatim;
  - every `## Open Questions` item that names it, or is `cross-cutting` with an
    `affects:` line reaching it (answered ones included — the answer binds);
  - every `## Expected Gray Areas` line that names it;
  - the project's `## Cross-Cutting Decisions` block, whole — those are settled
    for every feature;
  - in multi-section mode, the `## Boundary Contracts` sub-blocks for the
    contracts its `external contract consumed` field names.

    python3 feature-brief.py <feature> [--root <project-root>]
    python3 feature-brief.py --selftest

Exit codes: 0 printed, 1 --selftest failed, 2 the feature is in no roadmap
(names close to it are listed — a drifted name is a finding, never a guess).
"""

import argparse
import difflib
import glob
import importlib.util
import os
import re
import shutil
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - pre-3.7 or a pipe
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
# Builders run this from the installed skill inside their project; importing the
# checker must not leave a __pycache__ there for `git status` to report.
sys.dont_write_bytecode = True
CONTRACT_RE = re.compile(r"`([\w-]+)`\s*(?:→|->)\s*`([\w-]+)`")

# What a risk tier sets downstream — the one place it is written; decompose-phase.md
# Step 6 points here. The attempt ceilings are the WordPress AI Agent Manager
# pipeline's (5/4/3), carried over as a starting point, not measured as optimal.
# B gets tlc-spec-lean's `standard` profile, not its `light` default: `light` injects
# no faults, and on the project behind GUIA-TESTES-RAPIDOS 8 of 9 verification
# failures were tests that could not tell a wrong implementation from a right one.
TIER_MEANING = {
    "A": ("tlc-spec-lean: `Profile: standard` in checks.md (`ui` when it changes a screen)",
          "tlc-spec-driven: spec, design.md and tasks, whatever its size",
          "an independent verifier AND an independent reviewer; at most 5 attempts in a pipeline; never batched"),
    "B": ("tlc-spec-lean: `Profile: standard` in checks.md (`ui` when it changes a screen)",
          "tlc-spec-driven: spec and tasks; design.md only above 6 tasks",
          "an independent verifier; at most 4 attempts in a pipeline; never batched"),
    "C": ("tlc-spec-lean: `Profile: light` in checks.md",
          "tlc-spec-driven: a short spec (EARS criteria only) and tasks; no design.md",
          "one independent verifier; at most 3 attempts in a pipeline; may share one gate with up to 2 other independent C features"),
}


def _load_checker():
    """The roadmap parsers live in check-roadmap.py; one parser, not two that drift."""
    spec = importlib.util.spec_from_file_location("check_roadmap", os.path.join(HERE, "check-roadmap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CR = _load_checker()


def roadmap_files(root):
    docs = os.path.join(root, "docs")
    single = os.path.join(docs, "ROADMAP.md")
    sections = sorted(p for p in glob.glob(os.path.join(docs, "ROADMAP-*.md"))
                      if os.path.basename(p) != "ROADMAP-INDEX.md")
    return ([single] if os.path.isfile(single) else []) + sections


def status_path(root):
    index = os.path.join(root, "docs", "ROADMAP-INDEX.md")
    return index if os.path.isfile(index) else os.path.join(root, "docs", "ROADMAP.md")


def raw_entry(text, name):
    """The `### <name>` section verbatim, fences kept, to the next heading of level 1-3."""
    lines = text.splitlines()
    out, inside, fence = [], False, False
    for line in lines:
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^###\s+`?([A-Za-z0-9][\w.-]*)`?\s*$", line)
        if m and m.group(1) == name:
            inside = True
            out.append(line)
            continue
        if inside and not fence and re.match(r"^#{1,3}\s", line):
            break
        if inside:
            out.append(line)
    return "\n".join(out).rstrip()


def raw_block(text, heading):
    """A `## Heading` body verbatim (fences kept), to the next `#`/`##` heading."""
    lines = text.splitlines()
    out, inside, fence = [], False, False
    for line in lines:
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and line.rstrip().lower() == heading.lower():
            inside = True
            continue
        if inside and not fence and re.match(r"^#{1,2}\s", line):
            break
        if inside:
            out.append(line)
    return "\n".join(out).strip() if inside else None


def names_feature(item, name):
    return re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(name), item) is not None


def reaches(item, name):
    """A cross-cutting item whose `affects:` line reaches this feature."""
    if "cross-cutting" not in item.lower():
        return False
    m = re.search(r"affects:\s*(.*)", item, re.I)
    if not m:
        return True  # a roll-up entry with no affects: line is treated as `all` (handoff-seed Step 6)
    val = m.group(1)
    return bool(re.match(r"\W*all\b", val, re.I)) or names_feature(val, name)


def contract_blocks(index_text, consumed):
    """Boundary-contract sub-blocks whose heading carries a producer→consumer pair named in `consumed`."""
    pairs = set(CONTRACT_RE.findall(consumed or ""))
    if not pairs:
        return []
    body = raw_block(index_text, "## Boundary Contracts") or ""
    out, cur = [], None
    for line in body.splitlines() + ["### end"]:
        if line.startswith("### "):
            if cur and any(p in cur[0] and c in cur[0] for p, c in pairs):
                out.append("\n".join(cur).rstrip())
            cur = [line]
        elif cur is not None:
            cur.append(line)
    return out


def brief(root, name):
    files = roadmap_files(root)
    home = None
    for path in files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if any(n == name for n, _f, _b in CR.parse_features(text)):
            home = (path, text)
            break
    if home is None:
        known = []
        for path in files:
            with open(path, encoding="utf-8") as fh:
                known += [n for n, _f, _b in CR.parse_features(fh.read())]
        return None, difflib.get_close_matches(name, known, n=5, cutoff=0.5)

    path, text = home
    rel = lambda p: os.path.relpath(p, root)
    fields = next(f for n, f, _b in CR.parse_features(text) if n == name)
    parts = ["# Brief: `%s`" % name,
             "_From `%s`, printed by feature-brief.py. It is the roadmap's own text, cut to this "
             "feature; the roadmap file stays the source of truth._" % rel(path),
             "", raw_entry(text, name)]
    floor, why = CR.derive_tier(fields)
    got, _raised = CR.stated_tier(fields)
    tier = got if got and CR.TIER_RANK[got] >= CR.TIER_RANK[floor] else floor
    if got is None:
        origin = "derived: %s (the entry states none)" % why
    elif tier == got:
        origin = "stated in the entry (floor %s: %s)" % (floor, why)
    else:
        origin = "the entry states %s, below its floor — the floor wins: %s" % (got, why)
    parts += ["", "## Risk tier: %s" % tier, "", "_%s._" % origin, ""]
    parts += ["- %s" % line for line in TIER_MEANING[tier]]

    oq = [i for i in CR.bullets(raw_block(text, "## Open Questions") or "")
          if names_feature(i, name) or reaches(i, name)]
    parts += ["", "## Open questions naming it", ""] + (oq or ["None."])

    ga = [i for i in CR.bullets(raw_block(text, "## Expected Gray Areas") or "") if names_feature(i, name)]
    parts += ["", "## Expected gray areas naming it", ""] + (ga or ["None."])

    sp = status_path(root)
    ledger = None
    if os.path.isfile(sp):
        with open(sp, encoding="utf-8") as fh:
            status_text = fh.read()
        ledger = raw_block(status_text, "## Cross-Cutting Decisions")
        consumed = CR.field(fields, "external contract")
        if sp.endswith("ROADMAP-INDEX.md") and consumed and not CR.reads_as_none(consumed):
            blocks = contract_blocks(status_text, consumed)
            parts += ["", "## Boundary contracts it consumes (from `%s`)" % rel(sp), ""]
            parts += blocks or ["None matched `%s` — open `## Boundary Contracts` in %s."
                                % (consumed, rel(sp))]
    parts += ["", "## Cross-Cutting Decisions (settled for every feature — obey, never re-decide)", ""]
    parts += [ledger if ledger else "None — this roadmap has no such block."]
    return "\n".join(parts).rstrip() + "\n", path


# --------------------------------------------------------------------------- selftest

FIXTURE_INDEX = """# Index

## Status

- x

## Boundary Contracts

### `core` → `app`

- **Producer exposes:** `saveNote`.

### `core` → `ops`

- **Producer exposes:** `exportAll`.

## Cross-Cutting Decisions

| Theme | State |
|---|---|
| Data lifecycle / expiry | decided: soft delete |
"""

FIXTURE_APP = """# App

## Open Questions

- **app-tag** — Max tags per note? status: answered. Answer: 20.
- **app-list** — Page size? status: open
- **app-tag-bulk** — Batch size? status: open
- Retention of drafts? `cross-cutting` status: open affects: all
- Audit trail format? `cross-cutting` status: open affects: app-list, app-export
- Timezone policy? `cross-cutting` status: open

## Expected Gray Areas

- `app-tag` — tag casing. Lives in: Discuss.
- `app-list` — empty state.
- `app-tag-bulk` — undo of a bulk tag.

## Execution Order

An entry looks like this:

```
### app-tag
- **objective** — EXAMPLE ONLY
```

### app-tag

- **objective** — attach tags.
- **external contract consumed** — `core` → `app` (saveNote)

```
### not-a-heading
```

### app-tag-bulk

- **objective** — tag many notes.
- **external contract consumed** — none

### app-list

- **objective** — list notes.
- **external contract consumed** — none

### app-lowered

- **objective** — rotate the signing keys.
- **size** — Medium
- **implicit dimensions present** — auth
- **external contract consumed** — none
- **risk tier** — C
"""


def selftest():
    tmp = tempfile.mkdtemp(prefix="feature-brief-selftest-")
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    try:
        os.makedirs(os.path.join(tmp, "docs"))
        with open(os.path.join(tmp, "docs", "ROADMAP-INDEX.md"), "w", encoding="utf-8") as fh:
            fh.write(FIXTURE_INDEX)
        with open(os.path.join(tmp, "docs", "ROADMAP-app.md"), "w", encoding="utf-8") as fh:
            fh.write(FIXTURE_APP)
        out, _ = brief(tmp, "app-tag")
        expect("the entry is printed", "attach tags" in (out or ""))
        expect("a fenced '### ' line stays inside the entry", "### not-a-heading" in (out or ""))
        expect("a neighbouring feature's entry is not printed", "tag many notes" not in (out or ""))
        expect("its own open question is included", "Max tags per note" in (out or ""))
        expect("another feature's open question is not", "Page size" not in (out or ""))
        expect("a cross-cutting question affecting all is included", "Retention of drafts" in (out or ""))
        expect("a cross-cutting question affecting others is not", "Audit trail" not in (out or ""))
        expect("a cross-cutting question with no affects: line reaches every feature",
               "Timezone policy" in (out or ""))
        expect("a feature whose name is a prefix of another does not steal its lines",
               "Batch size" not in (out or "") and "undo of a bulk" not in (out or ""))
        expect("a fenced example of the heading is not taken for the entry",
               "EXAMPLE ONLY" not in (out or ""))
        expect("its gray area is included", "tag casing" in (out or ""))
        expect("the consumed contract is included", "saveNote" in (out or ""))
        expect("an unconsumed contract is not", "exportAll" not in (out or ""))
        expect("the ledger is included whole", "soft delete" in (out or ""))
        out2, _ = brief(tmp, "app-list")
        expect("a cross-cutting question naming it in affects: is included", "Audit trail" in (out2 or ""))
        expect("the tier is derived when the entry states none (a consumed contract makes it B)",
               "## Risk tier: B" in (out or "") and "derived" in (out or ""))
        expect("the tier says what it sets for both downstream skills",
               "`Profile: standard`" in (out or "") and "design.md only above 6 tasks" in (out or ""))
        out_c, _ = brief(tmp, "app-list")
        expect("no dimension and no contract is C", "## Risk tier: C" in (out_c or "") and "`Profile: light`" in (out_c or ""))
        f_large = {"size": "Large", "implicit dimensions present": "none", "external contract consumed": "none"}
        f_auth = {"size": "Small", "implicit dimensions present": "auth", "external contract consumed": "none"}
        f_ext = {"size": "Medium", "implicit dimensions present": "external calls", "external contract consumed": "none"}
        f_contract = {"size": "Small", "implicit dimensions present": "none", "external contract consumed": "`a` -> `b`"}
        expect("Large is A", CR.derive_tier(f_large)[0] == "A")
        expect("auth is A", CR.derive_tier(f_auth)[0] == "A")
        expect("a dimension that is not an A trigger is B", CR.derive_tier(f_ext)[0] == "B")
        expect("consuming a contract keeps it out of C", CR.derive_tier(f_contract)[0] == "B")
        expect("a raised tier with a reason is read as raised",
               CR.stated_tier({"risk tier": "A — raised from B: touches billing"}) == ("A", True))
        expect("a bare higher tier is not read as raised", CR.stated_tier({"risk tier": "A"}) == ("A", False))
        out3, _ = brief(tmp, "app-lowered")
        expect("a stated tier below the floor is overruled by the floor",
               "## Risk tier: A" in (out3 or "") and "floor wins" in (out3 or ""))
        miss, close = brief(tmp, "app-tags")
        expect("an unknown name prints nothing and offers close names", miss is None and "app-tag" in close)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("feature", nargs="?")
    ap.add_argument("--root", default=".", help="project root holding docs/ (default: cwd)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.feature:
        ap.error("name a feature, or pass --selftest")
    root = os.path.abspath(args.root)
    if not roadmap_files(root):
        print("no docs/ROADMAP.md or docs/ROADMAP-*.md under %s" % root, file=sys.stderr)
        return 2
    out, where = brief(root, args.feature)
    if out is None:
        print("`%s` is in no roadmap under %s/docs." % (args.feature, root)
              + (" Close names: %s." % ", ".join(where) if where else ""), file=sys.stderr)
        return 2
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
