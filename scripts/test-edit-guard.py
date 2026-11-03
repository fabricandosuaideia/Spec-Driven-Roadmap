#!/usr/bin/env python3
"""Find edits to tests that already existed on the main branch and carry no REVOKED-TEST commit (manager mode).

The rule it checks (roadmap-pipeline.js, the TESTS rule of manager mode): a test that already existed on the main
branch may change only in a commit of its own whose FIRST LINE is `REVOKED-TEST <file>:<test name>`. A verifier
refused whole rounds for the same slip, a fixture or a gate script edited inside an ordinary feat, fix or docs
commit: on the project that measured it, 5 of the 7 blockers across 11 features. This script finds the slip in
seconds, for the builder before it hands over and for the verifier before it reads.

It reports a file when ALL of these hold:
  - the file existed on <main> when the branch left it (the merge base) and its path looks like a test (the default
    patterns, or --pattern; --exclude removes a path from that);
  - the NET diff <main>...<branch> removes or rewrites at least one of its lines, or deletes it, or it is binary
    and changed;
  - no commit on <main>..<branch> opens with `REVOKED-TEST <that exact path>:<a test name>` AND changes that file by
    removing or rewriting a line of it. A subject that names the file while the commit changes something else declares
    nothing: that is a header, not a declaration, and it is reported as such.

Pure additions (a new test in an old file, a new file) are the feature's own work and are never reported.
Lines the branch wrote and later edited do not show in the net diff, so they are not reported either.
Documentation (.md, .txt, .rst) is never a test, whatever directory it sits in.

What it does NOT prove, said plainly because a green line invites stopping there:
  - The declaration is per FILE, not per edit. A declaring commit that changes a file covers every edit to that
    file on the branch, so a plain commit that also rewrites another test in it goes unseen (the verifier reads the
    whole diff of a declared file: that is its job). The test name after the colon is not checked.
  - It reads COMMITS: an edit that is staged or uncommitted is not seen (a note says so when the branch is checked out).
  - It does not say whether the correction is justified, nor whether the corrected test still bites.
  - Lines added to an existing test (an added skip mark, an early return) and the gate script are not seen.

Usage:
    test-edit-guard.py --root <worktree> [--main main] [--branch HEAD] [--pattern REGEX ...] [--exclude REGEX ...]
    test-edit-guard.py --selftest
Exit 0: nothing to declare. Exit 1: lists the undeclared files, one per line. Exit 2: usage, git or I/O error
(git missing from PATH is a 2, never a 1: a crash must not read as "undeclared files").
Standard library only.
"""
import argparse
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Documentation is never a test, even under tests/ (a README there was once reported as an edited test).
DOC_EXT = (".md", ".markdown", ".txt", ".rst")

# Matched case-insensitively: SwiftPM's Tests/ and .NET's Foo.Tests/ are tests too.
DEFAULT_PATTERNS = [
    r"(^|/)tests?/",                       # test/ or tests/ anywhere: sources, fixtures, factories, smoke scripts
    r"(^|/)[^/]*\.tests?/",                # Foo.Tests/ (.NET)
    r"(^|/)__tests__/",
    r"(^|/)__snapshots__/",
    r"(^|/)__mocks__/",
    r"(^|/)testdata/",
    r"(^|/)fixtures?/",
    r"(^|/)e2e/",
    r"(^|/)spec/",
    r"(^|/)test_[^/]*\.py$",
    r"[^/]*_test\.(py|go)$",
    r"[^/]*_tests\.py$",
    r"(^|/)tests\.py$",
    r"[^/]*_spec\.rb$",
    r"\.(test|spec)\.[cm]?[jt]sx?$",
    r"\.snap$",
    r"\.bats$",
    r"(^|/)conftest\.py$",
    r"(^|/)(vitest|jest|playwright)\.config\.[cm]?[jt]s$",
    r"(^|/)(pytest\.ini|tox\.ini)$",
]

PREFIX = "REVOKED-TEST "


class GitError(Exception):
    pass


def git(root, *args):
    p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise GitError("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout


def numstat(root, *rev_args):
    """{path: (added, removed)} from `git ... --numstat -z`; binary files are (None, None). Paths come NUL-separated,
    so a name with an accent is the name, not a quoted escape that no pattern would match, and a name with a tab is
    split only twice."""
    out = git(root, *(list(rev_args[:1]) + ["-z", "--numstat", "--no-renames"] + list(rev_args[1:])))
    stats = {}
    for rec in out.split("\0"):
        parts = rec.split("\t", 2)
        if len(parts) != 3:
            continue
        added, removed, path = parts
        stats[path] = (None, None) if added == "-" or removed == "-" else (int(added), int(removed))
    return stats


def statuses(root, main, branch):
    """{path: status letter} of <main>...<branch>. M, D and T mean the file existed at the merge base: that, and not the tip of
    the main branch, is what 'an existing test' is (main may have renamed or deleted it since the fork). Unlike `ls-tree`, the
    paths are relative to the repository root whichever directory --root names."""
    toks = git(root, "diff", "-z", "--name-status", "--no-renames", "%s...%s" % (main, branch)).split("\0")
    return {toks[i + 1]: toks[i] for i in range(0, len(toks) - 1, 2) if toks[i]}


def touched_tests(root, main, branch, patterns, excludes):
    """The existing test files whose net diff removes or rewrites something: [(path, why, deleted)]."""
    stat = numstat(root, "diff", "%s...%s" % (main, branch))
    status = statuses(root, main, branch)
    found = []
    for path, (added, removed) in sorted(stat.items()):
        if path.endswith(DOC_EXT) or status.get(path, "A")[:1] not in "MDT" or any(x.search(path) for x in excludes) or not any(q.search(path) for q in patterns):
            continue
        deleted = status.get(path, "")[:1] == "D"
        if added is None:
            found.append((path, "binary", deleted))
        elif removed > 0:
            found.append((path, "%d lines removed or rewritten" % removed, deleted))
    return found


def declarations(root, main, branch):
    """[(sha, rest, changed)] for every commit on main..branch whose subject opens with REVOKED-TEST: `rest` is what follows
    the prefix and `changed` the set of files that commit removes or rewrites lines of (or deletes, or changes as binary)."""
    out = []
    log = git(root, "log", "--encoding=UTF-8", "--format=%H%x1f%s", "%s..%s" % (main, branch))
    for line in log.splitlines():
        sha, _, subject = line.partition("\x1f")
        if not subject.startswith(PREFIX):
            continue
        stat = numstat(root, "show", sha, "--format=")
        changed = set(p for p, (a, r) in stat.items() if a is None or r > 0)
        out.append((sha, subject[len(PREFIX):], changed))
    return out


def names(rest, path):
    """Does the text after `REVOKED-TEST ` name exactly this path, followed by a colon and a test name? `tests/foo` is not named by
    `tests/foo bar.py:x`, and a bare path, or a colon with nothing after it, is a header and not a subject the rule describes."""
    return rest.startswith(path + ":") and rest[len(path) + 1:].strip() != ""


def check(root, main, branch, patterns, excludes=()):
    """(lines, exit code)."""
    touched = touched_tests(root, main, branch, patterns, excludes)
    notes = []
    try:
        here = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
        if branch in ("HEAD", here):
            dirty = [l for l in git(root, "status", "--porcelain", "--untracked-files=no").splitlines() if l.strip()]
            if dirty:
                notes.append("test-edit-guard: note: %d tracked file(s) have changes that are not committed; this check reads commits only, so commit first" % len(dirty))
    except GitError:
        pass
    if not touched:
        return ["test-edit-guard: no existing test changed beyond additions"] + notes, 0
    decl = declarations(root, main, branch)
    lines, missing = [], 0
    for path, why, deleted in touched:
        carriers = [d for d in decl if names(d[1], path) and path in d[2]]
        if carriers:
            lines.append("declared    %s  (%s%s)" % (path, why, "; deleted: the verifier refuses every deletion" if deleted else ""))
            continue
        missing += 1
        lines.append("UNDECLARED  %s  (%s)" % (path, why))
        header_only = [d[0][:9] for d in decl if names(d[1], path)]
        if header_only:
            lines.append("            REVOKED-TEST commit %s names it but changes none of its lines: a header declares nothing" % ", ".join(header_only))
        elsewhere = [d[0][:9] for d in decl if path in d[2] and not names(d[1], path)]
        if elsewhere:
            lines.append("            commit %s changes it too but declares another file: one REVOKED-TEST commit per file" % ", ".join(elsewhere))
        bare = [d[0][:9] for d in decl if d[1] == path or d[1].startswith(path + " ") or d[1] == path + ":"]
        if bare:
            lines.append("            commit %s names it without a test name: the subject is `REVOKED-TEST <file>:<test name>`" % ", ".join(bare))
    if missing:
        lines.append(
            "test-edit-guard: %d existing test file(s) changed with no commit whose first line is `REVOKED-TEST <file>:<test name>` "
            "and which changes that file. For each: revert the edit, or put exactly that edit in a commit of its own with that "
            "first line and a body quoting the criterion or decision that revokes the old assertion. If the edit already sits in an "
            "earlier commit: put the old lines back in a commit (git show %s:<file> shows them), then redo the edit in the REVOKED-TEST commit." % (missing, main))
        return lines + notes, 1
    lines.append("test-edit-guard: every changed existing test file has a commit that declares and changes it "
                 "(a declaration is per file, not per edit; whether it is justified and whether the corrected test still bites is not checked here)")
    return lines + notes, 0


def run(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root")
    ap.add_argument("--main", default="main")
    ap.add_argument("--branch", default="HEAD")
    ap.add_argument("--pattern", action="append", default=[], help="extra regex for test files (e.g. the gate script)")
    ap.add_argument("--exclude", action="append", default=[], help="regex for a path that looks like a test and is not (e.g. a Go package named spec)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.root or not os.path.isdir(a.root):
        print("give --root <the feature's working tree>", file=sys.stderr)
        return 2
    try:
        patterns = [re.compile(q, re.IGNORECASE) for q in DEFAULT_PATTERNS] + [re.compile(q) for q in a.pattern]
        lines, code = check(a.root, a.main, a.branch, patterns, [re.compile(q) for q in a.exclude])
    except (GitError, re.error, OSError) as e:
        print("test-edit-guard: %s" % e, file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return code


def main():
    # A file name with an accent must not crash a Windows console the one time the guard has something to say.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    try:
        return run(sys.argv[1:])
    except Exception as e:  # noqa: BLE001 - whatever else goes wrong is a 2: Python's own exit code for a crash is 1, the meaning of "undeclared files"
        print("test-edit-guard: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------------------------------------------------
# --selftest: every shape that mattered, in a repository of its own. A guard is exercised by what it must refuse.
# ---------------------------------------------------------------------------------------------------------------------
def selftest():
    failures = []
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    base_files = {
        "tests/a.py": "def test_a():\n    assert 1 == 1\n",
        "x/tests/a.py": "def test_a():\n    assert 2 == 2\n",
        "web/src/__tests__/f.test.ts": 'import { a } from "x";\nconst f = {\n  one: 1\n};\n',
        "tests/README.md": "# tests\nline\n",
        "tests/big.py": "".join("def test_%d():\n    assert %d == %d\n" % (i, i, i) for i in range(4)).replace("1 == 1", "2 == 2"),
        "tests/n\u00e3o.py": "a = 1\n",
        "spec/foo_spec.rb": "describe\n",
        "lib/bar_spec.rb": "describe_bar\n",
        "spec/support/helpers.rb": "module H\nend\n",
        "tests/big.py": "".join("def test_%d():\n    assert %d == %d\n" % (i, i, i) for i in range(12)),
        "api/tests.py": "class T:\n    pass\n",
        "web/__snap__/x.snap": "snap 1\n",
        "scripts/check_gate.py": "x = 1\n",
        "app.py": "prod = 1\n",
    }
    tmp = tempfile.mkdtemp(prefix="test-edit-guard-selftest-")
    counter = [0]

    class Repo(object):
        def __init__(self):
            counter[0] += 1
            self.dir = os.path.join(tmp, "r%d" % counter[0])
            os.makedirs(self.dir)
            self.git("init", "-q")
            self.git("symbolic-ref", "HEAD", "refs/heads/main")
            self.write(base_files)
            self.commit("base")
            self.git("checkout", "-q", "-b", "feat")

        def git(self, *a):
            quiet = ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.devnull, "-c", "core.autocrlf=false", "-c", "log.showSignature=false"]
            return subprocess.run(["git", "-C", self.dir] + quiet + list(a), capture_output=True, text=True, encoding="utf-8", env=env, check=True).stdout

        def write(self, files):
            for rel, body in files.items():
                full = os.path.join(self.dir, rel)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                mode = "wb" if isinstance(body, bytes) else "w"
                with open(full, mode, **({} if mode == "wb" else {"encoding": "utf-8", "newline": "\n"})) as fh:
                    fh.write(body)

        def commit(self, msg, files=None, remove=()):
            if files:
                self.write(files)
            for rel in remove:
                self.git("rm", "-q", rel)
            self.git("add", "-A")
            self.git("commit", "-q", "--allow-empty", "-m", msg)

        def guard(self, *extra, **kw):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                code = run(["--root", self.dir, "--main", kw.get("main", "main"), "--branch", kw.get("branch", "feat")] + list(extra))
            return code, buf.getvalue()

    def expect(name, cond, detail=""):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            failures.append(name)
            if detail:
                print("       " + detail.replace("\n", "\n       "))

    try:
        r = Repo(); r.commit("feat: a new test appended", {"tests/a.py": base_files["tests/a.py"] + "def test_b():\n    assert 3 == 3\n"})
        c, o = r.guard(); expect("a pure addition to an old test file is nothing to declare", c == 0, o)

        r = Repo(); r.commit("feat: new file", {"tests/new.py": "def test_n():\n    pass\n"})
        c, o = r.guard(); expect("a new test file is nothing to declare", c == 0, o)

        r = Repo(); r.commit("feat: strengthen", {"tests/a.py": base_files["tests/a.py"].replace("assert 1 == 1", "assert 1 == 1\n    assert 2 == 2")})
        c, o = r.guard(); expect("adding an assertion line to an old test is an addition", c == 0, o)

        r = Repo(); r.commit("feat: rewrite", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("a rewritten line is reported by its path", c == 1 and "UNDECLARED  tests/a.py" in o, o)

        r = Repo(); r.commit("feat: field at the end of a literal", {"web/src/__tests__/f.test.ts": 'import { a } from "x";\nconst f = {\n  one: 1,\n  two: 2\n};\n'})
        c, o = r.guard(); expect("a trailing comma rewrite counts as a rewrite", c == 1, o)

        r = Repo(); r.commit("style: whitespace", {"tests/a.py": base_files["tests/a.py"].replace("def test_a()", "def  test_a()")})
        c, o = r.guard(); expect("a whitespace-only change inside an old test is reported", c == 1, o)

        r = Repo(); r.commit("feat: delete", remove=["tests/a.py"])
        c, o = r.guard(); expect("deleting an old test file with no declaration is reported", c == 1 and "UNDECLARED  tests/a.py" in o, o)

        r = Repo(); r.commit("REVOKED-TEST tests/a.py:test_a", remove=["tests/a.py"])
        c, o = r.guard(); expect("deleting it in a REVOKED-TEST commit is declared", c == 0 and "declared    tests/a.py" in o, o)

        r = Repo(); r.git("mv", "tests/big.py", "tests/big2.py"); r.commit("feat: rename and edit", {"tests/big2.py": base_files["tests/big.py"].replace("3 == 3", "9 == 9")})
        c, o = r.guard(); expect("a renamed and edited test cannot hide behind the rename", c == 1 and "tests/big.py" in o, o)

        r = Repo()
        r.commit("fix: the edit, in a plain commit", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        r.commit("REVOKED-TEST tests/a.py:test_a (late)", {"app.py": "prod = 2\n"})
        c, o = r.guard(); expect("a header on a commit that does not touch the file declares nothing, and is said so",
                                 c == 1 and "UNDECLARED  tests/a.py" in o and "a header declares nothing" in o, o)

        r = Repo()
        r.commit("fix: the edit, in a plain commit", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        r.commit("REVOKED-TEST tests/a.py:test_a (late)", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9") + "# note\n"})
        c, o = r.guard(); expect("a header whose commit only ADDS to the file declares nothing either", c == 1, o)

        r = Repo()
        r.commit("fix: the edit, in a plain commit", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        r.commit("chore: restore the file from main", {"tests/a.py": base_files["tests/a.py"]})
        r.commit("REVOKED-TEST tests/a.py:test_a", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("the recipe the builder is given (restore, then redo in the declaring commit) passes", c == 0 and "declared    tests/a.py" in o, o)

        r = Repo()
        r.commit("REVOKED-TEST x/tests/a.py:test_a", {"x/tests/a.py": base_files["x/tests/a.py"].replace("2 == 2", "9 == 9")})
        r.commit("fix: sneaky", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("a declaration for x/tests/a.py does not cover tests/a.py", c == 1 and "UNDECLARED  tests/a.py" in o and "declared    x/tests/a.py" in o, o)

        r = Repo()
        r.commit("REVOKED-TEST x/tests/a.py:test_a", {"x/tests/a.py": base_files["x/tests/a.py"].replace("2 == 2", "9 == 9"),
                                                      "tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("a declaring commit covers the file it names, not a second file it also changes",
                                 c == 1 and "UNDECLARED  tests/a.py" in o and "declared    x/tests/a.py" in o, o)

        r = Repo(); r.commit("feat: edit an accented name", {"tests/n\u00e3o.py": "a = 2\n"})
        c, o = r.guard(); expect("a test file with an accent in its name is not skipped", c == 1 and "UNDECLARED" in o, o)

        r = Repo(); r.commit("docs: readme", {"tests/README.md": "# tests\nline 2\n"})
        c, o = r.guard(); expect("a README under tests/ is not a test", c == 0, o)

        r = Repo(); r.commit("feat: rspec", {"spec/foo_spec.rb": "describe2\n"})
        c, o = r.guard(); expect("a file under spec/ is a test", c == 1, o)

        r = Repo(); r.commit("feat: a helper under spec/", {"spec/support/helpers.rb": "module H2\nend\n"})
        c, o = r.guard(); expect("any file under spec/ is a test", c == 1, o)

        r = Repo(); r.commit("feat: rspec elsewhere", {"lib/bar_spec.rb": "describe_bar2\n"})
        c, o = r.guard(); expect("a _spec.rb file outside spec/ is a test", c == 1, o)

        r = Repo(); r.commit("feat: django", {"api/tests.py": "class T:\n    pass2\n"})
        c, o = r.guard(); expect("a Django tests.py is a test", c == 1, o)

        r = Repo(); r.commit("feat: snapshot", {"web/__snap__/x.snap": "snap 2\n"})
        c, o = r.guard(); expect("a .snap file is a test", c == 1, o)

        r = Repo(); r.commit("feat: gate script", {"scripts/check_gate.py": "x = 2\n"})
        c, o = r.guard(); expect("the gate script is not a test unless a pattern names it", c == 0, o)
        c, o = r.guard("--pattern", r"scripts/check_gate\.py$"); expect("--pattern makes the gate script one", c == 1 and "scripts/check_gate.py" in o, o)

        r = Repo(); r.commit("feat: binary", {"tests/blob.bin": b"\x00\x01"})
        r.git("checkout", "-q", "main"); r.git("merge", "-q", "--ff-only", "feat"); r.git("checkout", "-q", "-b", "feat2")
        r.commit("feat: change the binary", {"tests/blob.bin": b"\x00\x02"})
        c, o = r.guard(branch="feat2"); expect("a changed binary fixture is reported", c == 1 and "binary" in o, o)

        r = Repo()
        r.git("checkout", "-q", "main"); r.commit("main changes a test", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "5 == 5")})
        r.git("checkout", "-q", "feat"); r.commit("feat: prod only", {"app.py": "prod = 3\n"})
        c, o = r.guard(); expect("a test that main changed after the branch point is not the branch's edit", c == 0, o)
        r.git("merge", "-q", "main", "-m", "merge main")
        c, o = r.guard(); expect("nor after the branch took main in by a merge", c == 0, o)

        r = Repo(); r.commit("feat: ok", {"tests/new.py": "x = 1\n"})
        c, o = r.guard(main="nope"); expect("an unknown ref is a usage error, not a pass", c == 2)

        r = Repo(); r.commit("feat: rewrite", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        r.git("checkout", "-q", "main")
        c, o = r.guard(branch="HEAD"); expect("--branch HEAD with nothing ahead of main is nothing to declare", c == 0, o)

        # ---- the independent review of 3.51.0 (R1), each one reproduced first
        r = Repo()
        r.commit("fix: sneaky rewrite of another test in the same file", {"tests/big.py": base_files["tests/big.py"].replace("2 == 2", "9 == 9")})
        r.commit("REVOKED-TEST tests/big.py:test_0", {"tests/big.py": base_files["tests/big.py"].replace("2 == 2", "9 == 9").replace("0 == 0", "7 == 7")})
        c, o = r.guard(); expect("KNOWN LIMIT, said in the docstring: a declaration covers its file, not each edit in it (the verifier reads the whole diff of a declared file)", c == 0 and "per file, not per edit" in o, o)

        r2 = Repo(); r2.write({"pkg/tests/a.py": "x = 1\n"}); r2.git("add", "-A"); r2.git("commit", "-q", "-m", "pkg")
        r2.git("checkout", "-q", "main"); r2.git("merge", "-q", "--ff-only", "feat"); r2.git("checkout", "-q", "-b", "feat2")
        r2.commit("feat: edit in a subdirectory", {"pkg/tests/a.py": "x = 2\n"})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run(["--root", os.path.join(r2.dir, "pkg"), "--main", "main", "--branch", "feat2"])
        expect("--root a subdirectory of the repository still finds the edit (the paths are the repository's)", code == 1 and "UNDECLARED  pkg/tests/a.py" in buf.getvalue(), buf.getvalue())

        r = Repo(); r.commit("feat: a tab in the name", {"tests/with\ttab.py": "x = 1\n"})
        r.git("checkout", "-q", "main"); r.git("merge", "-q", "--ff-only", "feat"); r.git("checkout", "-q", "-b", "feat2")
        r.commit("feat: edit it", {"tests/with\ttab.py": "x = 2\n"})
        c, o = r.guard(branch="feat2"); expect("a test file with a tab in its name is not dropped", c == 1 and "with\ttab.py" in o, o)

        r = Repo()
        r.git("checkout", "-q", "main"); r.git("mv", "tests/a.py", "tests/c.py"); r.git("commit", "-q", "-m", "main renames the test after the fork")
        r.git("checkout", "-q", "feat"); r.commit("feat: edit the old path", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("a test that main renamed after the fork is still an existing test (it existed at the merge base)", c == 1 and "UNDECLARED  tests/a.py" in o, o)

        for label, subject in (("a bare path", "REVOKED-TEST tests/a.py"), ("a colon with no test name", "REVOKED-TEST tests/a.py:"), ("a space instead of a colon", "REVOKED-TEST tests/a.py test_a")):
            r = Repo(); r.commit(subject, {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
            c, o = r.guard(); expect("%s is not a declaration" % label, c == 1, o)
        r = Repo(); r.commit("REVOKED-TEST tests/big.py bar.py:x", {"tests/big.py": base_files["tests/big.py"].replace("2 == 2", "9 == 9")})
        c, o = r.guard(); expect("a subject naming `tests/big.py bar.py` does not declare `tests/big.py`", c == 1, o)

        r = Repo(); r.commit("feat: a new binary fixture", {"tests/fresh.bin": b"\x00\x01"})
        c, o = r.guard(); expect("a new binary fixture is not an edit of an existing test", c == 0, o)

        r = Repo()
        r.git("checkout", "-q", "main"); r.commit("REVOKED-TEST tests/a.py:t", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "5 == 5")})
        r.git("checkout", "-q", "-B", "feat", "main"); r.commit("fix: a plain edit of the same file", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "5 == 5").replace("def test_a", "def test_aa")})
        c, o = r.guard(); expect("a declaration that is already on the main branch does not cover this branch's edit", c == 1, o)

        r = Repo()
        r.commit("REVOKED-TEST tests/a.py:test_a", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        r.commit("REVOKED-TEST x/tests/a.py:test_a", {"x/tests/a.py": base_files["x/tests/a.py"].replace("2 == 2", "9 == 9")})
        c, o = r.guard(); expect("two files, two declaring commits: both are declared", c == 0 and "declared    tests/a.py" in o and "declared    x/tests/a.py" in o, o)

        r = Repo(); r.commit("feat: not tests", {"latest/x.py": "a = 1\n", "inspec/y.py": "a = 1\n"})
        r.git("checkout", "-q", "main"); r.git("merge", "-q", "--ff-only", "feat"); r.git("checkout", "-q", "-b", "feat2")
        r.commit("feat: edit them", {"latest/x.py": "a = 2\n", "inspec/y.py": "a = 2\n"})
        c, o = r.guard(branch="feat2"); expect("`latest/` and `inspec/` are not test directories (the patterns are anchored)", c == 0, o)

        shapes = ["tests/p.py", "Tests/p.swift", "Foo.Tests/p.cs", "web/__tests__/p.ts", "web/__snapshots__/p.json", "web/__mocks__/p.js", "pkg/testdata/p.json", "pkg/fixtures/p.json", "e2e/p.ts",
                  "spec/p.rb", "pkg/test_p.py", "pkg/p_test.go", "pkg/p_tests.py", "app/tests.py", "lib/p_spec.rb", "web/p.test.tsx", "web/p.spec.js", "web/p.snap", "ci/p.bats",
                  "conftest.py", "vitest.config.ts", "pytest.ini", "tox.ini"]
        r = Repo(); r.commit("feat: the shapes exist", {sh: "a = 1\n" for sh in shapes})
        r.git("checkout", "-q", "main"); r.git("merge", "-q", "--ff-only", "feat"); r.git("checkout", "-q", "-b", "feat2")
        r.commit("feat: rewrite them all", {sh: "a = 2\n" for sh in shapes})
        c, o = r.guard(branch="feat2"); missing_shapes = [sh for sh in shapes if "UNDECLARED  " + sh not in o]
        expect("every default test pattern is exercised: all %d shapes are reported" % len(shapes), c == 1 and not missing_shapes, "not reported: %s" % missing_shapes)

        r = Repo(); r.commit("REVOKED-TEST tests/a.py:test_a", remove=["tests/a.py"])
        c, o = r.guard(); expect("a declared deletion is declared, and the output says the verifier refuses every deletion", c == 0 and "refuses every deletion" in o, o)

        r = Repo(); r.write({"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("an edit that is not committed is not seen, and a note says so", c == 0 and "not committed" in o, o)

        r = Repo(); r.commit("feat: production code under a directory named like a test dir", {"internal/spec/spec.go": "package spec\n"})
        r.git("checkout", "-q", "main"); r.git("merge", "-q", "--ff-only", "feat"); r.git("checkout", "-q", "-b", "feat2")
        r.commit("feat: edit it", {"internal/spec/spec.go": "package spec // v2\n"})
        c, o = r.guard(branch="feat2"); expect("a production file under spec/ is reported by default", c == 1, o)
        c, o = r.guard("--exclude", r"internal/spec/", branch="feat2"); expect("--exclude lets a production path that looks like a test through", c == 0, o)

        r = Repo(); r.commit("REVOKED-TEST tests/a.py:test_a", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9"), "x/tests/a.py": base_files["x/tests/a.py"].replace("2 == 2", "9 == 9")})
        c, o = r.guard(); expect("a file changed inside the commit that declares ANOTHER file is told to be split", c == 1 and "UNDECLARED  x/tests/a.py" in o and "one REVOKED-TEST commit per file" in o, o)

        r = Repo(); r.commit("REVOKED-TEST tests/a.py", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("a subject with no test name is told what the subject is", c == 1 and "without a test name" in o, o)

        r = Repo(); r.commit("docs: a note tests/a.py:x REVOKED-TEST y", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        c, o = r.guard(); expect("a subject that merely CONTAINS `REVOKED-TEST ` is no declaration: it has to open the subject", c == 1, o)

        # an unexpected crash is a 2: Python's own exit code for one is 1, which is the meaning of "undeclared files"
        r = Repo(); saved = globals()["check"]; saved_argv = sys.argv
        def boom(*a, **k): raise RuntimeError("boom")
        globals()["check"] = boom; sys.argv = ["x", "--root", r.dir]
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                code = main()
        finally:
            globals()["check"] = saved; sys.argv = saved_argv
        expect("an unexpected crash inside the check is exit 2, never the 1 of 'undeclared files'", code == 2)

        # the script as a program: its defaults, a missing --root, and git missing from PATH (a crash must not read as "undeclared files")
        r = Repo(); r.commit("feat: rewrite", {"tests/a.py": base_files["tests/a.py"].replace("1 == 1", "9 == 9")})
        me = os.path.abspath(__file__)
        p = subprocess.run([sys.executable, "-I", me, "--root", r.dir], capture_output=True, text=True, encoding="utf-8")
        expect("run as a program with the defaults (--main main, --branch HEAD): exit 1 and the file named", p.returncode == 1 and "UNDECLARED  tests/a.py" in p.stdout, p.stdout + p.stderr)
        p = subprocess.run([sys.executable, "-I", me], capture_output=True, text=True, encoding="utf-8")
        expect("no --root is a usage error", p.returncode == 2)
        p = subprocess.run([sys.executable, "-I", me, "--root", r.dir], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PATH=os.devnull))
        expect("git missing from PATH is exit 2, not the 1 of 'undeclared files'", p.returncode == 2, p.stdout + p.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
