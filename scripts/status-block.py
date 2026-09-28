#!/usr/bin/env python3
"""Rewrite the roadmap's `## Status` block and keep it bounded; nothing is lost.

Why this exists: `## Status` is the block every handoff points agents at, so its
size is paid on every turn of every agent that opens it. On a real project it had
grown to 120 KB — 93% of it narrative that unattended `/loop` runs appended
("write the run's outcome into ## Status"), including `###` sub-headings. And the
seed could never shrink it: it replaced the body only up to the next heading of
ANY level, which stopped at the first `###` a run had added, so every run's
narrative survived every re-seed. A cut that has to tell a run's `###` apart from
a feature's `### <name>` entry, inside fenced code, is a rule a script does better
than prose.

Two operations, both writing only the Status file and its history file:

  --body FILE|-      the seed (handoff-seed.md Step 5): replace the block's body.
                     The previous body is appended to docs/roadmap-history.md
                     first, verbatim, so nothing a run wrote is lost. The block's
                     `**Last run**:` line is carried over unless the body sets one. The new body
                     may not contain a heading — a heading inside it is exactly how
                     the old block escaped every rewrite.
  --last-run LINE    a loop run's outcome: set the block's single `**Last run**:`
     [--note FILE|-] line to LINE (one line), and append LINE plus the note — the
                     run's full account — to the history file.

The block ends at the next `#`/`##` heading, or at a `### <name>` heading whose
name is a feature in any docs/roadmap*.txt (single-section roadmaps carry their
feature entries as bare `###` sections). Any other `###` inside is the block's
own and moves with it. Fence-aware. If the file has no `## Status`, the block is
inserted after the H1, or at the top when there is none.

The history file is a log for people. No prompt, handoff or reference ever points
an agent at it, which is what keeps its size off everyone's bill.

    python3 status-block.py docs/ROADMAP-INDEX.md --body new-status.md
    python3 status-block.py docs/ROADMAP.md --last-run "2026-09-28 - notes-list - PASS" --note run.md
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
LAST_RUN = "**Last run**:"
HISTORY_NAME = "roadmap-history.md"
FEATURE_HEADING = re.compile(r"^###\s+`?([A-Za-z0-9][\w.-]*)`?\s*$")


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
        if m and m.group(1) in names:
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
            fh.write("# Roadmap history\n\n_Written by status-block.py. Old `## Status` bodies and each run's "
                     "account, newest last. A log for people: no prompt points an agent here._\n")
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

SINGLE_NO_CONTAINER = """# Notes Roadmap

## Status

old status line

### notes-create

- **objective** - create.
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
            fh.write("# Title\n\nintro\n\n### notes-create\n\n- x\n")
        replace_body(rm, "inserted\n", hist)
        text = open(rm).read()
        expect("a missing block is inserted after the H1",
               text.index("## Status") < text.index("intro") and "inserted" in text)
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
    ap.add_argument("status_file", nargs="?", help="docs/ROADMAP-INDEX.md or docs/ROADMAP.md")
    ap.add_argument("--body", help="file holding the new body, or - for stdin")
    ap.add_argument("--last-run", help="one line: date - feature - state - reason")
    ap.add_argument("--note", help="file holding the run's full account, or - for stdin")
    ap.add_argument("--history", help="default: roadmap-history.md beside the status file")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.status_file or not os.path.isfile(args.status_file):
        print("give the Status file (docs/ROADMAP-INDEX.md or docs/ROADMAP.md); %r is not a file"
              % args.status_file, file=sys.stderr)
        return 2
    if bool(args.body) == bool(args.last_run):
        print("give exactly one of --body or --last-run", file=sys.stderr)
        return 2
    history = args.history or os.path.join(os.path.dirname(os.path.abspath(args.status_file)), HISTORY_NAME)
    before = os.path.getsize(args.status_file)
    if args.body:
        err = replace_body(args.status_file, read_arg(args.body), history)
    else:
        err = set_last_run(args.status_file, args.last_run, read_arg(args.note), history)
    if err:
        print(err, file=sys.stderr)
        return 1
    print("%s: %d -> %d bytes; previous content kept in %s"
          % (args.status_file, before, os.path.getsize(args.status_file), history))
    return 0


if __name__ == "__main__":
    sys.exit(main())
