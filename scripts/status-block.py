#!/usr/bin/env python3
"""Rewrite the seed's two blocks, `## Status` and `## Handoff`, keeping both bounded; nothing is lost.

Why this exists: `## Status` is the block every handoff points agents at, so its
size is paid on every turn of every agent that opens it. On a real project it had
grown to 120 KB — 93% of it narrative that unattended `/loop` runs appended
("write the run's outcome into ## Status"), including `###` sub-headings. And the
seed could never shrink it: it replaced the body only up to the next heading of
ANY level, which stopped at the first `###` a run had added, so every run's
narrative survived every re-seed. A cut that has to tell a run's `###` apart from
a feature's `### <name>` entry, inside fenced code, is a rule a script does better
than prose.

`## Handoff` in .specs/STATE.md grew the same way by the opposite route. The seed
said "replace the body" and never said where the old one goes, so a run that would
not destroy 260 lines of someone's notes kept them — renamed `## Handoff
(superseded …)` — and so had every run before it: 72,899 of that file's 82,586
bytes, read by the downstream skill on every resume. Both downstream skills define
exactly two sections there, `## Decisions` and `## Handoff`; a section named after
the Handoff is a copy of it, and it leaves with the body it copied.

Three operations. Each writes one file and the history file:

  --body FILE|-      the seed (handoff-seed.md Step 5): replace the block's body.
                     The previous body is appended to docs/roadmap-history.md
                     first, verbatim, so nothing a run wrote is lost. The block's
                     `**Last run**:` line is carried over unless the body sets one. The new body
                     may not contain a heading — a heading inside it is exactly how
                     the old block escaped every rewrite.
  --last-run LINE    a loop run's outcome: set the block's single `**Last run**:`
     [--note FILE|-] line to LINE (one line), and append LINE plus the note — the
                     run's full account — to the history file.
  --handoff FILE|-   the seed (handoff-seed.md Step 6), given .specs/STATE.md:
                     replace `## Handoff`'s body, and move every other `##`
                     section named after it (`## Handoff (superseded …)`, `## Handoff
                     addendum 2`) out of the file. All of it goes to the history
                     file first, verbatim, one entry per section. `## Decisions`
                     and every other section are never touched; the body may not
                     contain a heading; the file must already exist. The history
                     file defaults to docs/roadmap-history.md beside `.specs/`.

The block ends at the next `#`/`##` heading, or at a `###` heading whose first
token is a feature name — listed in a docs/roadmap*.txt, or shaped like one
(`<prefix>-<kebab>`), with or without text after it (single-section roadmaps carry
their feature entries as `###` sections). Any other `###` inside is the block's
own and moves with it. Fence-aware. If the file has no `## Status`, the block is
inserted after the H1, or at the top when there is none.

The history file is a log for people. No prompt, handoff or reference ever points
an agent at it, which is what keeps its size off everyone's bill.

    python3 status-block.py docs/ROADMAP-INDEX.md --body new-status.md
    python3 status-block.py docs/ROADMAP.md --last-run "2026-09-28 - notes-list - PASS" --note run.md
    python3 status-block.py .specs/STATE.md --handoff new-handoff.md
    python3 status-block.py --selftest

Exit codes: 0 written, 1 refused (nothing written) or --selftest failed, 2 usage.
"""

import argparse
import datetime
import glob
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

STATUS = "## Status"
HANDOFF = "## Handoff"
LAST_RUN = "**Last run**:"
HISTORY_NAME = "roadmap-history.md"
# Any `##` heading whose first word is Handoff. The exact `## Handoff` is the live
# one; every other match is a copy of it. `\b` keeps a `## Handoffs log` out.
HANDOFF_NAMED = re.compile(r"^##\s+Handoff\b")
# handoff-seed.md Step 7 prescribes this exact line for a delegated seed's report.
NEXT_STEP_8 = "Next: Step 8 — ask the user how to build (handover-prompt.md)"
# A `###` whose first token is a feature name, bare or followed by text (real
# roadmaps carry `### `name` — SUPERSEDED`). Feature names are `<prefix>-<kebab>`,
# so a hyphenated identifier counts even when no .txt lists it (a superseded entry
# is dropped from the .txt). The two errors are not symmetric: reading a run's
# heading as a feature leaves narrative in the block, which the next rewrite can
# still see; reading a feature as the block's own moves its entry out of the roadmap.
FEATURE_HEADING = re.compile(r"^###\s+`?([A-Za-z0-9][\w.-]*)`?(?:\s.*)?$")
KEBAB_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def feature_names(docs_dir):
    names = set()
    for path in glob.glob(os.path.join(docs_dir, "roadmap*.txt")):
        with open(path, encoding="utf-8-sig") as fh:
            names.update(l.strip() for l in fh if l.strip() and not l.lstrip().startswith("#"))
    return names


def locate(lines, names):
    """(start, end) line indexes of the block body: start is the heading line."""
    fence, start = False, None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if start is None:
            if line.rstrip() == STATUS:
                start = i
            continue
        if re.match(r"^#{1,2}\s", line):
            return start, i
        m = FEATURE_HEADING.match(line)
        if m and (m.group(1) in names or KEBAB_NAME.match(m.group(1))):
            return start, i
    return (start, len(lines)) if start is not None else (None, None)


def has_heading(text):
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence and re.match(r"^#{1,6}\s", line):
            return True
    return False


def write_atomic(path, text):
    tmp = path + ".tmp-status-block"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def append_history(history, title, body):
    body = body.strip("\n")
    if not body.strip():
        return
    new = not os.path.isfile(history)
    with open(history, "a", encoding="utf-8", newline="\n") as fh:
        if new:
            fh.write("# Roadmap history\n\n_Written by status-block.py. Old `## Status` and `## Handoff` bodies and "
                     "each run's account, newest last. A log for people: no prompt points an agent here._\n")
        fh.write("\n## %s\n\n%s\n" % (title, body))


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def split_file(path, names):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.split("\n")
    start, end = locate(lines, names)
    if start is None:
        h1 = next((i for i, l in enumerate(lines) if re.match(r"^#\s", l)), None)
        at = h1 + 1 if h1 is not None else 0
        lines[at:at] = ([""] if h1 is not None else []) + [STATUS, ""]
        start, end = at + (1 if h1 is not None else 0), at + (3 if h1 is not None else 2)
    return lines, start, end


def replace_body(path, body, history):
    if has_heading(body):
        return "refused: the new body contains a heading, which is how a block escapes every rewrite"
    names = feature_names(os.path.dirname(path))
    lines, start, end = split_file(path, names)
    old = "\n".join(lines[start + 1:end])
    append_history(history, "%s - `## Status` as it stood before this rewrite" % now(), old)
    new = [""] + body.strip("\n").split("\n") + [""]
    # The last run's one line is the loop's, not the seed's: carry it over unless
    # the new body sets its own.
    carried = next((l for l in lines[start + 1:end] if l.startswith(LAST_RUN)), None)
    if carried and not any(l.startswith(LAST_RUN) for l in new):
        new[-1:-1] = ["", carried]
    lines[start + 1:end] = new
    write_atomic(path, "\n".join(lines))
    return None


def set_last_run(path, line, note, history):
    if "\n" in line.strip():
        return "refused: --last-run takes one line; put the account in --note"
    names = feature_names(os.path.dirname(path))
    lines, start, end = split_file(path, names)
    body = lines[start + 1:end]
    entry = "%s %s" % (LAST_RUN, line.strip())
    idx = next((i for i, l in enumerate(body) if l.startswith(LAST_RUN)), None)
    if idx is None:
        while body and not body[-1].strip():
            body.pop()
        body += ["", entry, ""]
    else:
        body[idx] = entry
    lines[start + 1:end] = body
    append_history(history, "%s - run: %s" % (now(), line.strip()), note or "(no account given)")
    write_atomic(path, "\n".join(lines))
    return None


def top_sections(lines):
    """(start, end) of every `#`/`##` section outside fences; end is the next one's start."""
    fence, heads = False, []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence and re.match(r"^#{1,2}\s", line):
            heads.append(i)
    return [(h, heads[k + 1] if k + 1 < len(heads) else len(lines)) for k, h in enumerate(heads)]


def replace_handoff(path, body, history):
    """Replace `## Handoff`'s body; move it, and every copy named after it, to the history.

    Returns (error, moved headings). Nothing is written when there is an error."""
    if has_heading(body):
        return "refused: the new body contains a heading, which ends the section for every reader", []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    live, copies = None, []
    for start, end in top_sections(lines):
        title = lines[start].rstrip()
        if title == HANDOFF and live is None:
            live = (start, end)
        elif HANDOFF_NAMED.match(title):
            copies.append((start, end))
    stamp = now()
    if live:
        append_history(history, "%s - `.specs/STATE.md` `## Handoff` as it stood before this seed" % stamp,
                       "\n".join(lines[live[0] + 1:live[1]]))
    for start, end in copies:
        append_history(history, "%s - moved out of `.specs/STATE.md`: %s"
                       % (stamp, lines[start].lstrip("#").strip()), "\n".join(lines[start + 1:end]))
    block = [HANDOFF, ""] + body.strip("\n").split("\n") + [""]
    skip = dict(copies)
    out, i = [], 0
    while i < len(lines):
        if live and i == live[0]:
            out += block
            i = live[1]
        elif i in skip:
            i = skip[i]
        else:
            out.append(lines[i])
            i += 1
    if not live:
        while out and not out[-1].strip():
            out.pop()
        out += [""] + block
    write_atomic(path, "\n".join(out))
    return None, [lines[s].lstrip("#").strip() for s, _ in copies]


# --------------------------------------------------------------------------- selftest

BLOATED = """# Notes Roadmap

## Status

_Backlog position. Regenerated by spec-driven-roadmap v3.20.0 on 2026-09-01._

- `docs/ROADMAP.md` - IN PROGRESS (1/2)

Execucao autonoma do /loop, um paragrafo inteiro que ninguem pediu.

### Encerramento - 2026-09-02

Mais narrativa de uma execucao.

```
### notes-list
```

## Cross-Cutting Decisions

| Theme | State |
|---|---|

## Execution Order

### notes-create

- **objective** - create.

### notes-list

- **objective** - list.
"""

SUPERSEDED_NEXT = """# Notes Roadmap

## Status

old status line

### `notes-old` — SUPERSEDED (2026-08-07)

- **objective** - replaced by notes-list.
"""

SINGLE_NO_CONTAINER = """# Notes Roadmap

## Status

old status line

### notes-create

- **objective** - create.
"""


STATE_PILED = """# STATE

## Decisions

- **AD-001**: votes are counted on read.

```
## Handoff (quoted inside a fence, not a section)
```

## Handoff

- **Feature**: notes-create
- **Next step**: specify feature `notes-list`

### a run's own sub-heading

Two hundred lines of what the last session did.

## Handoff (superseded detail, kept for history - 2026-09-22)

The session before that one.

## Handoff addendum 2 (2026-09-16, the owner's audit)

What the owner asked for, long since done.
"""

STATE_DECISIONS_LAST = """# STATE

## Handoff

- **Feature**: old

## Handoff

- **Feature**: a second live-looking copy

## Decisions

- **AD-001**: kept.
"""


def selftest():
    tmp = tempfile.mkdtemp(prefix="status-block-selftest-")
    failures = []

    def expect(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
    try:
        docs = os.path.join(tmp, "docs")
        os.makedirs(docs)
        with open(os.path.join(docs, "roadmap.txt"), "w") as fh:
            fh.write("notes-create\nnotes-list\n")
        rm = os.path.join(docs, "ROADMAP.md")
        hist = os.path.join(docs, HISTORY_NAME)
        with open(rm, "w") as fh:
            fh.write(BLOATED)
        err = replace_body(rm, "_Regenerated on 2026-09-28._\n\n**Next feature**: `notes-list`\n", hist)
        text = open(rm).read()
        h = open(hist).read()
        expect("the rewrite succeeds", err is None)
        expect("a run's ### sub-heading is part of the block and leaves it", "Encerramento" not in text)
        expect("a run's narrative leaves the block", "Execucao autonoma" not in text)
        expect("the new body is in place", "**Next feature**: `notes-list`" in text)
        expect("the next ## block is untouched", "## Cross-Cutting Decisions" in text and "| Theme |" in text)
        expect("feature entries survive", "- **objective** - create." in text and "- **objective** - list." in text)
        expect("the old body is kept verbatim in the history", "Encerramento" in h and "Execucao autonoma" in h)
        expect("a fenced ### inside the old block did not end it early", "```\n### notes-list\n```" in h)
        err = replace_body(rm, "fine\n### sneaky\n", hist)
        expect("a body carrying a heading is refused", err is not None)
        expect("a refused body writes nothing", "sneaky" not in open(rm).read())

        err = set_last_run(rm, "2026-09-28 - notes-list - PASS", "the whole account", hist)
        err2 = set_last_run(rm, "2026-09-29 - notes-list - FAIL twice, stopped", "second account", hist)
        text = open(rm).read()
        h = open(hist).read()
        expect("last-run succeeds", err is None and err2 is None)
        expect("there is exactly one Last run line, the newest",
               text.count(LAST_RUN) == 1 and "FAIL twice" in text and "2026-09-28 - notes-list - PASS" not in text)
        expect("each run's account goes to the history", "the whole account" in h and "second account" in h)
        expect("the account never enters the block", "whole account" not in text)
        expect("a multi-line last-run is refused", set_last_run(rm, "a\nb", "", hist) is not None)
        replace_body(rm, "_Regenerated again._\n", hist)
        text = open(rm).read()
        expect("a seed rewrite carries the Last run line over", text.count(LAST_RUN) == 1 and "FAIL twice" in text)

        with open(rm, "w") as fh:
            fh.write(SINGLE_NO_CONTAINER)
        replace_body(rm, "new status\n", hist)
        text = open(rm).read()
        expect("a feature's bare ### entry ends the block", "### notes-create" in text and "new status" in text
               and "old status line" not in text)

        with open(rm, "w") as fh:
            fh.write(SUPERSEDED_NEXT)
        replace_body(rm, "new status\n", hist)
        text = open(rm).read()
        expect("a superseded entry absent from the .txt still ends the block (it is never archived away)",
               "### `notes-old` — SUPERSEDED" in text and "replaced by notes-list" in text)

        with open(rm, "w") as fh:
            fh.write("# Title\n\nintro\n\n### notes-create\n\n- x\n")
        replace_body(rm, "inserted\n", hist)
        text = open(rm).read()
        expect("a missing block is inserted after the H1",
               text.index("## Status") < text.index("intro") and "inserted" in text)

        specs = os.path.join(tmp, ".specs")
        os.makedirs(specs)
        st = os.path.join(specs, "STATE.md")
        with open(st, "w") as fh:
            fh.write(STATE_PILED)
        before_hist = open(hist).read()
        seed = "- **Feature**: notes-list\n- **Next step**: specify feature `notes-list`\n"
        err, moved = replace_handoff(st, seed, hist)
        text = open(st).read()
        h = open(hist).read()[len(before_hist):]
        expect("the handoff rewrite succeeds", err is None)
        expect("exactly one ## Handoff is left, holding the new body",
               len(re.findall(r"^## Handoff$", text, re.M)) == 1 and "- **Feature**: notes-list" in text)
        expect("the copies named after it leave the file",
               "superseded detail" not in text and "addendum" not in text and "owner asked" not in text)
        expect("the old body, its ### included, leaves the file",
               "notes-create" not in text and "Two hundred lines" not in text)
        expect("## Decisions is untouched, fence and all",
               text.startswith(STATE_PILED[:STATE_PILED.index("\n## Handoff\n")]))
        expect("the old body and each copy are in the history, verbatim",
               "Two hundred lines" in h and "### a run's own sub-heading" in h
               and "The session before that one." in h and "What the owner asked for" in h)
        expect("each copy is named in the history and in what the call returns",
               "moved out of `.specs/STATE.md`: Handoff addendum 2" in h and len(moved) == 2)
        expect("a fenced `## Handoff` line is not a section and is not moved", len(moved) == 2
               and "quoted inside a fence" in text)

        with open(st, "w") as fh:
            fh.write(STATE_PILED)
        err, _ = replace_handoff(st, "- **Feature**: x\n## Status\n", hist)
        expect("a handoff body carrying a heading is refused, and nothing is written",
               err is not None and open(st).read() == STATE_PILED)

        with open(st, "w") as fh:
            fh.write(STATE_DECISIONS_LAST)
        err, moved = replace_handoff(st, "- **Feature**: new\n", hist)
        text = open(st).read()
        expect("a second exact ## Handoff is a copy: the first is rewritten, the second moved",
               err is None and text.count("## Handoff") == 1 and "second live-looking" not in text
               and moved == ["Handoff"])
        expect("a section after the Handoff survives", text.rstrip().endswith("- **AD-001**: kept."))

        with open(st, "w") as fh:
            fh.write("# STATE\n\n## Decisions\n\n- **AD-001**: kept.\n")
        err, _ = replace_handoff(st, "- **Feature**: new\n", hist)
        text = open(st).read()
        expect("a missing ## Handoff is appended, and Decisions stays",
               err is None and text.index("AD-001") < text.index("## Handoff") and text.endswith("- **Feature**: new\n"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


def read_arg(value):
    if value is None:
        return None
    if value == "-":
        return sys.stdin.read()
    with open(value, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("status_file", nargs="?",
                    help="docs/ROADMAP-INDEX.md or docs/ROADMAP.md; .specs/STATE.md with --handoff")
    ap.add_argument("--body", help="file holding the new body, or - for stdin")
    ap.add_argument("--last-run", help="one line: date - feature - state - reason")
    ap.add_argument("--note", help="file holding the run's full account, or - for stdin")
    ap.add_argument("--handoff", help="file holding the new ## Handoff body, or - for stdin")
    ap.add_argument("--history", help="default: roadmap-history.md beside the status file, "
                                      "or in docs/ beside .specs/ with --handoff")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.status_file or not os.path.isfile(args.status_file):
        print("give the file to rewrite (docs/ROADMAP-INDEX.md or docs/ROADMAP.md; .specs/STATE.md with "
              "--handoff, created first as handoff-seed.md Step 6 says); %r is not a file"
              % args.status_file, file=sys.stderr)
        return 2
    if sum(bool(x) for x in (args.body, args.last_run, args.handoff)) != 1:
        print("give exactly one of --body, --last-run or --handoff", file=sys.stderr)
        return 2
    before = os.path.getsize(args.status_file)
    if args.handoff:
        specs = os.path.dirname(os.path.abspath(args.status_file))
        if not args.history and os.path.basename(specs) != ".specs":
            print("%s is not inside .specs/, so the history file cannot be derived: give --history"
                  % args.status_file, file=sys.stderr)
            return 2
        history = args.history or os.path.join(os.path.dirname(specs), "docs", HISTORY_NAME)
        err, moved = replace_handoff(args.status_file, read_arg(args.handoff), history)
        if err:
            print(err, file=sys.stderr)
            return 1
        print("%s: %d -> %d bytes; the previous Handoff%s kept in %s"
              % (args.status_file, before, os.path.getsize(args.status_file),
                 " and %d section(s) named after it are" % len(moved) if moved else " is", history))
        for title in moved:
            print("  moved: %s" % title)
        # The one step a delegated seed has dropped: Steps 1-7 ran in a sub-agent,
        # its report came back, and nobody asked the user how to build.
        print(NEXT_STEP_8)
        print("  asked by the session the user is talking to, after Step 7's report; a sub-agent that "
              "ran this ends its report with the line above and never answers it")
        return 0
    history = args.history or os.path.join(os.path.dirname(os.path.abspath(args.status_file)), HISTORY_NAME)
    hist_before = os.path.getsize(history) if os.path.isfile(history) else 0
    if args.body:
        err = replace_body(args.status_file, read_arg(args.body), history)
    else:
        err = set_last_run(args.status_file, args.last_run, read_arg(args.note), history)
    if err:
        print(err, file=sys.stderr)
        return 1
    kept = os.path.isfile(history) and os.path.getsize(history) > hist_before
    print("%s: %d -> %d bytes; %s"
          % (args.status_file, before, os.path.getsize(args.status_file),
             "previous content kept in %s" % history if kept else "there was no previous content to keep"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
