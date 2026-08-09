#!/usr/bin/env python3
"""Convert a single-section spec-driven-roadmap project to multi-section.

Why this is a script and not a written procedure: the conversion renames files,
moves two blocks that exist exactly once per project, and rewrites paths inside
them. Three rounds of review of the prose version kept finding catastrophic
paths -- a rollback that silently restored nothing, a rollback that recreated
`docs/ROADMAP.md` and then overwrote it (losing `## Cross-Cutting Decisions`
entirely), and a prefix derivation that split on the first hyphen and so handed
`auth-core-*` features the slug `auth`. Those are the failures a deterministic,
testable step does not have.

What it does, in one atomic operation:

  1. docs/ROADMAP.md  ->  docs/ROADMAP-<slug>.md
     docs/roadmap.txt ->  docs/roadmap-<slug>.txt
  2. creates a minimal docs/ROADMAP-INDEX.md carrying the `## Status` and
     `## Cross-Cutting Decisions` blocks, with every path inside them rewritten
  3. removes both blocks (heading and body) from the renamed roadmap

`<slug>` is never chosen. It is derived from the feature names already on disk,
because index-phase Step 2 makes the slug and the feature-name prefix the same
string, and those names freeze once `.specs/features/<name>/` exists.

The safety net is a backup directory, not git: git recovery needs the files
tracked AND clean, which is exactly what a project is not right after Phase 0c
wrote docs/CODEBASE-SUMMARY.md. `git mv` is still used when it is safe, so
history follows the rename -- but recovery never depends on it.

Usage:
    python3 convert-to-multi.py [--root DIR] [--dry-run] [--slug SLUG]
    python3 convert-to-multi.py [--root DIR] --rollback [--force]

Exit codes:
    0  converted (or dry run printed, or rollback completed)
    1  pre-condition failed, or a rollback refused -- nothing was touched
    2  usage error
    3  conversion failed mid-way and was rolled back automatically
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
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



BACKUP_DIR = ".sdr-conversion-backup"
JOURNAL = "journal.json"

MOVED_BLOCKS = ["## Status", "## Cross-Cutting Decisions"]

STALE_HANDOFF = (
    "**Handoff**: not rewritten this run — conversion in progress; re-seed after it. "
    "Any Handoff written before this run still names the pre-conversion `docs/ROADMAP.md`"
)

# What the index carries when a moved block simply is not there. One text per
# heading, because the two absences mean different things and are repaired by
# different steps: `## Cross-Cutting Decisions` is decompose-phase's, and
# `## Status` is written by nothing but handoff-seed.md's own Step 5. A single
# shared string said "the next Phase 2 run fills this block" about both, which
# is false — and unfalsifiable — for the Status one.
PLACEHOLDER = {
    "## Status": (
        "_No `Status` block existed in `docs/ROADMAP.md` at conversion time. This is "
        "handoff-seed.md Step 5's legacy case: the next run of this skill's Handoff "
        "seed writes it here. Never read it as \"nothing is in progress\"._"
    ),
    "## Cross-Cutting Decisions": (
        "_No `Cross-Cutting Decisions` existed in `docs/ROADMAP.md` at conversion "
        "time. This is handoff-seed.md's legacy case: read it as \"the roadmap "
        "predates decompose-phase Step 7a\" and report it — never as \"no open "
        "themes\". The next Phase 2 run fills this block._"
    ),
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def fail(msg, code=1):
    print("✗ " + msg, file=sys.stderr)
    sys.exit(code)


def info(msg):
    print("  " + msg)


def write_journal(backup, data):
    """Atomic: a half-written journal is a backup --rollback refuses to use."""
    tmp = os.path.join(backup, JOURNAL + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, os.path.join(backup, JOURNAL))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_git(root, *args):
    """Run a git command. Returns (exit_code, stdout). Never raises."""
    try:
        p = subprocess.run(
            ["git", "-C", str(root)] + list(args),
            capture_output=True, text=True, timeout=30,
        )
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def is_git_repo(root):
    code, out = run_git(root, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out == "true"


# --------------------------------------------------------------------------
# prefix derivation
# --------------------------------------------------------------------------

def read_feature_names(txt_path):
    """Feature names from a build-order .txt: one per line, '#' and blanks skipped."""
    names = []
    with open(txt_path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                names.append(line)
    return names


def derive_prefix(names):
    """Longest leading hyphen-token run common to every name, backed off until it
    is not the whole of any name.

    NOT a split on the first hyphen: a slug is kebab-case and may contain one, so
    `auth-core-login` + `auth-core-signup` yields `auth-core` here rather than
    `auth`. That is this helper's answer, not the command's -- `candidate_prefixes`
    then reports every leading run of it, and the command asks when more than one
    is viable. Returns (prefix, error); exactly one of the two is None.
    """
    if not names:
        return None, "no feature names found"

    token_lists = [n.split("-") for n in names]
    if any(len(t) < 2 for t in token_lists):
        bare = [n for n, t in zip(names, token_lists) if len(t) < 2]
        return None, (
            "these feature names carry no hyphen, so they have no prefix: "
            + ", ".join(sorted(bare)[:5])
        )

    common = []
    for i in range(min(len(t) for t in token_lists)):
        tok = token_lists[0][i]
        if all(t[i] == tok for t in token_lists):
            common.append(tok)
        else:
            break

    if not common:
        distinct = sorted({t[0] for t in token_lists})
        return None, (
            "feature names share no leading token — %d distinct prefixes: %s"
            % (len(distinct), ", ".join(distinct[:8]))
        )

    # The run must stop short of some feature's whole name, or the "prefix" is
    # itself a feature and every other name is nested under it. Back off a token
    # at a time rather than abort: `tt-list` + `tt-list-open-tasks` is an
    # ordinary shape (a parent feature and its children), and refusing it left
    # the conversion with no exit at all — the abort fired before the `--slug`
    # branch could override it.
    while common and any(len(t) == len(common) for t in token_lists):
        common = common[:-1]

    if not common:
        return None, (
            "every leading token run is the whole of some feature name, so no "
            "prefix is left to name the section after"
        )

    return "-".join(common), None


def candidate_prefixes(names):
    """Every leading token run common to all names, shortest first.

    `pay-invoice-create` + `pay-invoice-list` admit both `pay` and `pay-invoice`.
    Both are legal prefixes of every name, so the file CANNOT decide between
    them -- Step 2 assigned one and only the project knows which.
    """
    prefix, err = derive_prefix(names)
    if err:
        return None, err
    toks = prefix.split("-")
    return ["-".join(toks[:i]) for i in range(1, len(toks) + 1)], None


def validate_slug(slug):
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        return "'%s' is not usable as a filename component (lowercase kebab-case only)" % slug
    return None


# --------------------------------------------------------------------------
# block surgery
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r"^#{1,6}\s")

# Matches a moved-block heading loosely: leading spaces, trailing colon, any
# case, extra inner spacing. Used only to DETECT near-misses, never to move
# them -- a heading the extractor cannot match exactly is a heading that would
# be left behind while a placeholder is written in its place, which is how the
# ledger ends up existing twice.
LOOSE = {h: re.compile(r"^\s{0,3}#{2}\s*%s\s*:?\s*$" % re.escape(h[3:]), re.I)
         for h in MOVED_BLOCKS}


def scan_heading(text, heading):
    """Fence-aware. Returns (loose_line_numbers, exact_line_numbers), 1-indexed."""
    loose, exact, fence = [], [], False
    for i, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if LOOSE[heading].match(line):
            loose.append(i + 1)
            if line.rstrip() == heading:
                exact.append(i + 1)
    return loose, exact


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        fail("cannot read %s: %s" % (path, exc))


def split_block(text, heading):
    """Return (before, block, after) for a '## Heading' block.

    The block ends at the next heading of ANY level, not the next '## '. In a
    roadmap the feature entries sit between `## Cross-Cutting Decisions` and
    `## Open Questions` as bare `### <feature-name>` sections with no `##`
    container of their own -- stopping only at '## ' swallows every one of them
    into the block and migrates the features out of the roadmap. Neither block
    this script moves ever contains a heading in its own body, so the stricter
    rule loses nothing.

    Fenced code is respected so a '#' inside a fence never ends the block.
    Returns (text, None, '') when the heading is absent.
    """
    lines = text.splitlines(keepends=True)
    start = None
    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if start is None:
            if line.rstrip() == heading:
                start = i
        elif HEADING_RE.match(line):
            return "".join(lines[:start]), "".join(lines[start:i]), "".join(lines[i:])
    if start is None:
        return text, None, ""
    return "".join(lines[:start]), "".join(lines[start:]), ""


def rewrite_paths(block, slug):
    """Point every pre-conversion path at its post-conversion name.

    The lookahead bars a longer filename (`docs/ROADMAP.md.bak`, `.mdx`) but not
    a sentence-ending period: a trailing dot followed by anything other than a
    word character is punctuation, and `recorded in docs/ROADMAP.md.` has to
    migrate like every other mention.
    """
    block = re.sub(r"docs/ROADMAP\.md(?![\w-]|\.\w)", "docs/ROADMAP-%s.md" % slug, block)
    block = re.sub(r"docs/roadmap\.txt(?![\w-]|\.\w)", "docs/roadmap-%s.txt" % slug, block)
    return block


def mark_handoff_stale(status_block):
    """Replace the '**Handoff**:' line: the copied one asserts a seed that is
    now wrong, and Step 5's rewrite is several steps away.

    The line is matched with any list marker and re-emitted with that marker
    intact. Step 5's template writes it unbulleted, so a plain prefix test is
    enough for a generated roadmap -- the marker is tolerated for hand-edited
    ones, where an unmatched line would fall through to the append below and
    leave the block asserting two contradictory Handoff states.
    """
    out, replaced = [], False
    for line in status_block.splitlines(keepends=True):
        mm = re.match(r"(\s{0,3}(?:[-*]\s+)?)\*\*Handoff\*\*", line)
        if mm:
            nl = "\n" if line.endswith("\n") else ""
            out.append(mm.group(1) + STALE_HANDOFF + nl)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        body = "".join(out).rstrip("\n")
        return body + "\n\n" + STALE_HANDOFF + "\n"
    return "".join(out)


def build_index(project_title, slug, blocks):
    parts = ["# %s — Roadmap Index\n\n" % project_title]
    for heading in MOVED_BLOCKS:
        if blocks.get(heading):
            parts.append(blocks[heading].rstrip("\n") + "\n\n")
        else:
            parts.append("%s\n\n%s\n\n" % (heading, PLACEHOLDER[heading]))
    parts.append(
        "## Roadmaps\n\n"
        "| Section | Roadmap file | Build-order file | Slug / prefix | Depends on |\n"
        "|---|---|---|---|---|\n"
        "| %s | `docs/ROADMAP-%s.md` | `docs/roadmap-%s.txt` | `%s` | — |\n\n"
        % (slug, slug, slug, slug)
    )
    parts.append(
        "## Ordering\n\n"
        "```\n%s\n```\n\n"
        "One node. The new wave's row, its edge and the boundary contract are "
        "written when Phase 1 Steps 1-5 fill this index out.\n" % slug
    )
    return "".join(parts)


# --------------------------------------------------------------------------
# pre-conditions
# --------------------------------------------------------------------------

def preconditions(root, chosen_slug=None):
    docs = os.path.join(root, "docs")
    roadmap = os.path.join(docs, "ROADMAP.md")
    txt = os.path.join(docs, "roadmap.txt")
    index = os.path.join(docs, "ROADMAP-INDEX.md")
    backup = os.path.join(root, BACKUP_DIR)

    if not os.path.isdir(docs):
        fail("no docs/ directory at %s — nothing to convert." % root)

    # Order matters. After a finished OR interrupted conversion docs/ROADMAP.md is
    # gone, so a roadmap-first check reports "not single-section" for exactly the
    # half-converted state rule 9 wants surfaced. Test the interrupted states first.
    if os.path.exists(index):
        fail("docs/ROADMAP-INDEX.md already exists — this project is already "
             "multi-section, or a previous conversion did not finish. Resolve that "
             "first (see --rollback).")
    orphans = [f for f in sorted(os.listdir(docs))
               if f.startswith("ROADMAP-") and f.endswith(".md")]
    if orphans:
        hint = ("\n  A %s/ is present — `--rollback` reverses that conversion."
                % BACKUP_DIR) if os.path.isdir(backup) else ""
        fail("section roadmaps present with no index: %s. That is an interrupted "
             "conversion (SKILL.md rule 9) — stop and resolve it before converting.%s"
             % (", ".join(orphans), hint))
    if os.path.isdir(backup):
        fail("%s/ already exists — a previous conversion left state behind. Run "
             "--rollback, or remove it deliberately." % BACKUP_DIR)
    if not os.path.isfile(roadmap):
        fail("docs/ROADMAP.md not found. This project is not single-section.")
    if not os.path.isfile(txt):
        fail(
            "docs/roadmap.txt not found. The mandatory re-seed would classify the "
            "section NOT YET DECOMPOSED and strand the backlog. Regenerate it from "
            "the roadmap's execution-order block first (feature names only, one per "
            "line), then re-run.")
    if os.path.islink(roadmap) or os.path.islink(txt):
        fail("docs/ROADMAP.md or docs/roadmap.txt is a symlink — the backup would "
             "follow it and the rollback would replace it with a regular file. "
             "Resolve the link first.")

    body = read_text(roadmap)

    # --- D1: the extractor must be trustworthy before anything is written. ---
    if len([l for l in body.splitlines() if l.lstrip().startswith("```")]) % 2:
        fail("docs/ROADMAP.md has an odd number of ``` fence lines. While that is "
             "true the block extractor cannot tell code from headings, and it would "
             "silently declare both moved blocks absent — leaving the real ledger in "
             "the roadmap and a placeholder in the index, so it exists twice. Close "
             "the fence first.")
    for h in MOVED_BLOCKS:
        loose, exact = scan_heading(body, h)
        if len(loose) > 1:
            fail("'%s' appears %d times in docs/ROADMAP.md (lines %s). Exactly one "
                 "may exist per project — only the first would move, and the rest "
                 "would be orphaned." % (h, len(loose), ", ".join(map(str, loose))))
        # The fence check above only counts fences; it cannot see a ledger that
        # lives INSIDE a balanced one. `scan_heading` is fence-aware and returns
        # nothing for it, which is precisely the path that writes a placeholder
        # denying the block ever existed while the real one rides along in the
        # renamed roadmap. Only reached when the fence-aware scan found nothing —
        # a fenced EXAMPLE beside a real block is legal and must keep converting.
        if not loose:
            blind = [i + 1 for i, l in enumerate(body.splitlines())
                     if LOOSE[h].match(l)]
            if blind:
                fail("'%s' appears in docs/ROADMAP.md only inside a fenced block "
                     "(line %d). The extractor cannot tell the real ledger from an "
                     "example, and would write a placeholder saying it never existed. "
                     "Resolve it by hand before converting." % (h, blind[0]))
        if loose and not exact:
            fail("'%s' exists at line %d but not in that exact form (trailing "
                 "punctuation, or different spacing or case). It would be left "
                 "behind while a placeholder took its place, so the block would "
                 "exist twice. Normalise the heading first." % (h, loose[0]))

    names = read_feature_names(txt)
    if not names:
        fail("docs/roadmap.txt carries no feature names, so the section slug cannot "
             "be derived and the re-seed would have nothing to order. Regenerate it "
             "from the roadmap's execution-order block first (feature names only, one "
             "per line), then re-run.")

    # `--slug` is validated against the NAMES, not against the derived candidates.
    # Derivation is the thing this flag exists to override, so gating it on a
    # SUCCESSFUL derivation left every derivation failure with no exit at all.
    # Strict prefix: a slug equal to some whole feature name would name the
    # section after one of the features inside it.
    if chosen_slug:
        toks = chosen_slug.split("-")
        bad = [n for n in names
               if n.split("-")[:len(toks)] != toks or n.split("-") == toks]
        if bad:
            fail("--slug '%s' is not a strict prefix of these feature names: %s"
                 % (chosen_slug, ", ".join(sorted(bad)[:5])))
        slug = chosen_slug
    else:
        cands, err = candidate_prefixes(names)
        if err:
            fail(
                "cannot derive the section slug: %s.\nThe slug must be the prefix the "
                "existing features already carry — it is not free to choose, because "
                "those names are frozen. Put this to the user; if you know which prefix "
                "Step 2 assigned, re-run with --slug <choice>." % err)
        if len(cands) > 1:
            fail("the feature names admit %d possible section slugs: %s.\nEvery one is "
                 "a legal prefix of every name, so this CANNOT be derived from the file "
                 "— Step 2 assigned it and only the project knows which. Check "
                 "`.specs/features/*` and docs/ROADMAP.md, put it to the user (the "
                 "longest, '%s', is the usual answer), then re-run with --slug <choice>."
                 % (len(cands), ", ".join(cands), cands[-1]))
        slug = cands[0]
    err = validate_slug(slug)
    if err:
        fail("section slug %s" % err)

    # --- D3: a stale .txt would rename the roadmap after a section it does not hold.
    entries = re.findall(r"^###\s+`?([A-Za-z0-9][\w.-]*)`?\s*$", body, re.M)
    if entries:
        stray = [n for n in names if n not in entries]
        if stray:
            fail("docs/roadmap.txt names features docs/ROADMAP.md does not carry as "
                 "`### ` entries: %s. The slug is derived from that file, so a stale "
                 ".txt renames the roadmap after a section it does not contain. "
                 "Reconcile them first." % ", ".join(sorted(stray)[:5]))
    else:
        # Not a failure: a legacy or hand-made roadmap that never carried `### `
        # feature entries is exactly what the placeholder path exists to serve.
        # But index-phase.md lists this reconciliation among the guaranteed
        # aborts, so skipping it in silence is what has to stop.
        info("build-order reconciliation: skipped — docs/ROADMAP.md carries no "
             "`### ` feature entries (legacy or hand-made); the slug came from "
             "docs/roadmap.txt alone")

    # --- D5: never overwrite a rename target.
    for target in ("ROADMAP-%s.md" % slug, "roadmap-%s.txt" % slug):
        if os.path.lexists(os.path.join(docs, target)):
            fail("docs/%s already exists — the rename would overwrite it, and the "
                 "rollback would then delete it. Resolve that first." % target)

    git = {"repo": False, "tracked": False, "clean": False}
    if is_git_repo(root):
        git["repo"] = True
        code, _ = run_git(root, "ls-files", "--error-unmatch",
                          "docs/ROADMAP.md", "docs/roadmap.txt")
        git["tracked"] = code == 0
        if git["tracked"]:
            # Scoped to the two files that actually move. A dirty docs/ is the
            # normal state right after Phase 0c wrote CODEBASE-SUMMARY.md, and
            # must not disable the rename-with-history path.
            code, out = run_git(root, "status", "--porcelain", "--",
                                "docs/ROADMAP.md", "docs/roadmap.txt")
            git["clean"] = code == 0 and out == ""

    return {
        "root": root, "docs": docs, "roadmap": roadmap, "txt": txt,
        "index": index, "slug": slug, "names": names, "git": git, "body": body,
    }


def report_work_in_flight(root):
    """Informational only. The decision belongs to the procedure, not the script."""
    state = os.path.join(root, ".specs", "STATE.md")
    if not os.path.isfile(state):
        return "no .specs/STATE.md — nothing seeded yet"
    with open(state, encoding="utf-8") as fh:
        text = fh.read()
    _, handoff, _ = split_block(text, "## Handoff")
    if not handoff:
        return ".specs/STATE.md has no ## Handoff block"
    findings = []
    for field in ("Completed", "In-progress"):
        # The canonical field is `**In-progress** (file:line): none` — the
        # parenthetical carries its own colon, so a lazy [^:]* stops inside it and
        # captures "line): none", which never equals "none". Anchor on the field
        # name and skip any parenthetical before the real separator.
        m = re.search(r"\*\*%s\*\*\s*(?:\([^)]*\))?\s*:\s*(.+)" % re.escape(field),
                      handoff)
        if m and m.group(1).strip().lower() not in ("none", "none.", "—", "-"):
            findings.append("%s = %s" % (field, m.group(1).strip()))
    if findings:
        return "WORK MAY BE IN FLIGHT — " + "; ".join(findings)
    return "Handoff present, Completed/In-progress read none"


# --------------------------------------------------------------------------
# execute / rollback
# --------------------------------------------------------------------------

def do_convert(ctx, dry_run):
    root, slug = ctx["root"], ctx["slug"]
    new_md = os.path.join(ctx["docs"], "ROADMAP-%s.md" % slug)
    new_txt = os.path.join(ctx["docs"], "roadmap-%s.txt" % slug)

    original = ctx["body"]

    m = re.match(r"#\s+(.+)", original)
    title = m.group(1).strip() if m else "Project"
    title = re.sub(r"\s*[—-]\s*Roadmap\s*$", "", title).strip() or "Project"

    remaining, blocks = original, {}
    for heading in MOVED_BLOCKS:
        before, block, after = split_block(remaining, heading)
        if block is None:
            blocks[heading] = None
            continue
        block = rewrite_paths(block, slug)
        if heading == "## Status":
            block = mark_handoff_stale(block)
        blocks[heading] = block
        remaining = before.rstrip("\n") + "\n\n" + after.lstrip("\n") if after else before

    index_text = build_index(title, slug, blocks)

    print("\nPlan")
    info("slug (derived from %d feature names): %s" % (len(ctx["names"]), slug))
    info("docs/ROADMAP.md   -> docs/ROADMAP-%s.md" % slug)
    info("docs/roadmap.txt  -> docs/roadmap-%s.txt" % slug)
    for heading in MOVED_BLOCKS:
        info("%-28s %s" % (
            heading, "moved into the index" if blocks[heading] else "ABSENT — placeholder written"))
    info("rename method: %s" % (
        "git mv (history preserved)"
        if ctx["git"]["repo"] and ctx["git"]["tracked"] and ctx["git"]["clean"]
        else "plain rename"))
    info("work in flight: %s" % report_work_in_flight(root))

    if dry_run:
        print("\n--dry-run: nothing was written.")
        return 0

    backup = os.path.join(root, BACKUP_DIR)
    use_git = ctx["git"]["repo"] and ctx["git"]["tracked"] and ctx["git"]["clean"]
    # Relative to root, never absolute: a journal carrying absolute paths is
    # unreadable once the project is reached by a different absolute path (a
    # move, a different container mount, a copied worktree), and every isfile()
    # in the rollback then quietly returns False — restoring the originals
    # BESIDE the index it failed to remove, deleting the backup, and reporting
    # success. Relative paths plus the existence check below close that.
    rel = lambda p: os.path.relpath(p, root)
    journal = {"slug": slug, "new_md": rel(new_md), "new_txt": rel(new_txt),
               "index": rel(ctx["index"]), "used_git": use_git}
    # Bound before the try: `os.makedirs` itself can raise (read-only or full
    # filesystem), and the handler below reads `created` to decide whether the
    # backup is this run's to remove. Unbound, that handler died with an
    # UnboundLocalError traceback instead of the oriented message.
    created = False
    try:
        # No exist_ok: if another run created it between the pre-condition check
        # and here, this raises FileExistsError and the handler below must NOT
        # delete it — that directory is the other run's only safety net.
        os.makedirs(backup)
        created = True
        # copyfile, not copy2: copystat fails whenever the caller does not own
        # the file, and a backup that half-exists is worse than none.
        shutil.copyfile(ctx["roadmap"], os.path.join(backup, "ROADMAP.md"))
        shutil.copyfile(ctx["txt"], os.path.join(backup, "roadmap.txt"))
        write_journal(backup, journal)
    except FileExistsError:
        fail("%s/ appeared while this run was preparing — another conversion is "
             "in progress in this project. Nothing was touched." % BACKUP_DIR)
    except Exception as exc:  # noqa: BLE001
        # Never leave a backup without its journal: --rollback would refuse and
        # the project would be stuck between the two commands. Only remove what
        # this run created.
        if created:
            shutil.rmtree(backup, ignore_errors=True)
        fail("could not create the backup at %s/ (%s) — nothing was touched."
             % (BACKUP_DIR, exc))

    try:
        for src, dst in ((ctx["roadmap"], new_md), (ctx["txt"], new_txt)):
            if use_git:
                code, out = run_git(root, "mv", os.path.relpath(src, root),
                                    os.path.relpath(dst, root))
                if code != 0:
                    raise RuntimeError(
                        "git mv %s -> %s failed (%s). Refusing the plain-rename "
                        "fallback: git refuses for reasons a blind rename ignores, "
                        "and os.rename would overwrite the destination."
                        % (src, dst, out or code))
            else:
                os.rename(src, dst)
        with open(ctx["index"], "w", encoding="utf-8") as fh:
            fh.write(index_text)
        with open(new_md, "w", encoding="utf-8") as fh:
            fh.write(remaining)

        # Post-conditions. The extractor is trusted only after the result is
        # checked: "it did not raise" is not evidence that a block moved.
        after_text = read_text(new_md)
        index_check = read_text(ctx["index"])
        for heading in MOVED_BLOCKS:
            if scan_heading(after_text, heading)[0]:
                raise RuntimeError(
                    "post-condition failed: '%s' is still in %s — it would exist "
                    "twice" % (heading, os.path.basename(new_md)))
            if len(scan_heading(index_check, heading)[0]) != 1:
                raise RuntimeError(
                    "post-condition failed: '%s' does not appear exactly once in "
                    "docs/ROADMAP-INDEX.md" % heading)

        journal["hashes"] = {rel(p): sha256(p)
                             for p in (new_md, new_txt, ctx["index"])}
        write_journal(backup, journal)
    except Exception as exc:  # noqa: BLE001 - any failure must restore
        print("\n✗ conversion failed: %s\n  rolling back..." % exc, file=sys.stderr)
        try:
            rollback(root, quiet=False, force=True, auto=True)
        except SystemExit:
            raise
        except Exception as rexc:  # noqa: BLE001
            fail("ROLLBACK ALSO FAILED (%s). The project is half-converted. Your "
                 "originals are intact at %s/ — restore docs/ROADMAP.md and "
                 "docs/roadmap.txt from there by hand, and delete any "
                 "docs/ROADMAP-*.md this run created." % (rexc, BACKUP_DIR), code=3)
        return 3

    print("\n✓ converted to multi-section")
    info("docs/ROADMAP-INDEX.md written (minimal — Steps 1-5 fill it out)")
    info("backup kept at %s/ — `--rollback` reverses this exactly" % BACKUP_DIR)
    print("\nNext, in order:")
    info("1. fill the index out through Phase 1 Steps 1-5 (add the new wave's row and edge)")
    info("2. re-run the Handoff seed — all three path placeholders moved")
    info("3. delete %s/ once you are satisfied" % BACKUP_DIR)
    return 0


def rollback(root, quiet=True, force=False, auto=False):
    """auto=True is the in-run recovery path, and it knows things the manual one
    cannot assume: this run created the backup seconds ago, so it is not foreign;
    hashes are absent because the run never reached the point that writes them,
    not because anything is suspect; and no product has existed long enough for
    anyone to edit it. The guards below exist for a human running --rollback
    later, and firing them here is what left a backup behind after every failed
    conversion -- blocking re-conversion, since a surviving backup aborts the
    pre-conditions."""
    backup = os.path.join(root, BACKUP_DIR)
    jpath = os.path.join(backup, JOURNAL)
    if not os.path.isfile(jpath):
        fail("no %s/%s — nothing to roll back." % (BACKUP_DIR, JOURNAL))
    try:
        with open(jpath, encoding="utf-8") as fh:
            j = json.load(fh)
    except (OSError, ValueError) as exc:
        fail("%s/%s is unreadable (%s). Restore docs/ROADMAP.md and docs/roadmap.txt "
             "from %s/ by hand." % (BACKUP_DIR, JOURNAL, exc, BACKUP_DIR))

    docs = os.path.join(root, "docs")
    # Journals from 3.6.0 carry absolute paths; anything relative is joined to
    # root. os.path.join returns an absolute path unchanged, so both load.
    products = {k: os.path.join(root, j[k]) for k in ("index", "new_md", "new_txt")}

    # The journal describes what this run produced. If none of it is on disk, this
    # backup does not belong to this directory -- restoring on top of that would
    # put docs/ROADMAP.md beside a surviving index (rule 9's first contradiction)
    # and then delete the only backup, reporting success.
    missing = [p for p in products.values() if not os.path.exists(p)]
    if not auto and len(missing) == len(products):
        fail("this backup describes files that are not here:\n  %s\nIt does not "
             "belong to %s — most likely the project was reached by a different "
             "path than the one it was converted under. Nothing was touched."
             % ("\n  ".join(sorted(missing)), root))
    if not auto and os.path.exists(os.path.join(docs, "ROADMAP.md")):
        fail("docs/ROADMAP.md already exists — restoring on top of it would leave "
             "two roadmaps for the same scope. Resolve that first; nothing was "
             "touched.")

    # The procedure sends the user straight into this window: fill the index out
    # through Steps 1-5, then re-seed. That work is uncommitted and lives in the
    # exact files a rollback removes, so removing it silently is not an option.
    hashes = {os.path.join(root, k): v for k, v in (j.get("hashes") or {}).items()}
    if not hashes and not force and not auto:
        fail("this backup has no recorded hashes, so changes made since the "
             "conversion cannot be detected — the run was interrupted before it "
             "finished. Re-run with `--rollback --force` to proceed anyway; any "
             "changed file is kept under %s/discarded/." % BACKUP_DIR)
    changed = [p for p, want in hashes.items()
               if os.path.isfile(p) and sha256(p) != want]
    if changed and not force:
        fail("these files changed since the conversion:\n  %s\n"
             "Rolling back removes that work. Re-run with `--rollback --force` to "
             "discard it deliberately — the changed versions are kept under %s/"
             "discarded/ either way." % ("\n  ".join(sorted(changed)), BACKUP_DIR))

    # Order matters: the index goes FIRST. Restoring docs/ROADMAP.md while an
    # index survives recreates rule 9's first contradiction, and a rollback that
    # halts the next run is not a rollback.
    quarantine = os.path.join(backup, "discarded")
    for key in ("index", "new_md", "new_txt"):
        path = products[key]
        if os.path.isfile(path):
            if path in changed or (not hashes and not auto):
                os.makedirs(quarantine, exist_ok=True)
                shutil.move(path, os.path.join(quarantine, os.path.basename(path)))
            else:
                os.remove(path)
    shutil.copyfile(os.path.join(backup, "ROADMAP.md"), os.path.join(docs, "ROADMAP.md"))
    shutil.copyfile(os.path.join(backup, "roadmap.txt"), os.path.join(docs, "roadmap.txt"))

    # Restoring the working tree is not enough after `git mv`: the rename is
    # already staged, so the index still records it and `git status` reports a
    # rename whose target no longer exists. Unstage the four paths.
    if j.get("used_git"):
        rel = [os.path.relpath(p, root) for p in
               ([os.path.join(docs, "ROADMAP.md"), os.path.join(docs, "roadmap.txt")]
                + [products["new_md"], products["new_txt"]])]
        run_git(root, "reset", "-q", "--", *rel)

    kept = os.path.isdir(quarantine)
    if not kept:
        shutil.rmtree(backup, ignore_errors=True)
    if not quiet:
        print("✓ rolled back — docs/ROADMAP.md and docs/roadmap.txt restored")
        if j.get("used_git"):
            print("  git index unstaged back to HEAD")
        if kept:
            print("  changed versions kept at %s/discarded/ — not deleted" % BACKUP_DIR)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Convert a single-section roadmap project to multi-section.")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and write nothing")
    ap.add_argument("--rollback", action="store_true",
                    help="reverse a conversion using its backup")
    ap.add_argument("--force", action="store_true",
                    help="with --rollback: discard changes made since the conversion")
    ap.add_argument("--slug",
                    help="the section slug, instead of deriving one: pick among the "
                         "viable prefixes when the feature names admit more than one, "
                         "or supply the prefix Step 2 assigned when derivation fails "
                         "outright. Must be a strict prefix of every feature name.")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        fail("no such directory: %s" % root, code=2)

    if args.rollback:
        if args.dry_run:
            fail("--rollback and --dry-run are mutually exclusive", code=2)
        return rollback(root, quiet=False, force=args.force)

    print("spec-driven-roadmap: single-section -> multi-section")
    ctx = preconditions(root, args.slug)
    return do_convert(ctx, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
