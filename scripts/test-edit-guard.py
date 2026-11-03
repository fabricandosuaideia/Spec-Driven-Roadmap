#!/usr/bin/env python3
"""Find edits to tests that already existed on the main branch and carry no REVOKED-TEST commit (manager mode).

The rule it checks (roadmap-pipeline.js, REVOKED_RULE): in manager mode a test that already existed on the
main branch may change only in a commit of its own whose FIRST LINE is `REVOKED-TEST <file>:<test name>`.
A verifier refused whole rounds for the same slip, a fixture or a gate script edited inside an ordinary
feat, fix or docs commit: on the project that measured it, 5 of the 7 blockers across 11 features. This
script finds the slip in seconds, for the builder before it hands over and for the verifier before it reads.

It reports a file when ALL of these hold:
  - the file exists on <main> and its path looks like a test (the default patterns, or --pattern);
  - the NET diff <main>...<branch> removes or rewrites at least one of its lines, or deletes it, or it is binary
    and changed;
  - no commit on <main>..<branch> opens with `REVOKED-TEST <that exact path>` AND changes that file by removing
    or rewriting a line of it. A subject that names the file while the commit changes something else declares
    nothing: that is a header, not a declaration, and it is reported as such.

Pure additions (a new test in an old file, a new file) are the feature's own work and are never reported.
Lines the branch wrote and later edited do not show in the net diff, so they are not reported either.
Documentation (.md, .txt, .rst) is never a test, whatever directory it sits in.

It proves a declaration EXISTS and carries the edit, not that it is justified: whether the old assertion
contradicts a criterion decided before the branch is the verifier's judgement.

Usage:
    test-edit-guard.py --root <worktree> [--main main] [--branch HEAD] [--pattern REGEX ...]
    test-edit-guard.py --selftest
Exit 0: nothing to declare. Exit 1: lists the undeclared files, one per line. Exit 2: usage or git error.
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

DEFAULT_PATTERNS = [
    r"(^|/)tests?/",                       # test/ or tests/ anywhere: sources, fixtures, factories, smoke scripts
    r"(^|/)__tests__/",
    r"(^|/)__snapshots__/",
    r"(^|/)e2e/",
    r"(^|/)spec/",
    r"(^|/)test_[^/]*\.py$",
    r"[^/]*_test\.(py|go)$",
    r"(^|/)tests\.py$",
    r"[^/]*_spec\.rb$",
    r"\.(test|spec)\.[cm]?[jt]sx?$",
    r"\.snap$",
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
    so a name with an accent is the name, not a quoted escape that no pattern would match."""
    out = git(root, *(list(rev_args[:1]) + ["-z", "--numstat", "--no-renames"] + list(rev_args[1:])))
    stats = {}
    for rec in out.split("\0"):
        parts = rec.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        stats[path] = (None, None) if added == "-" or removed == "-" else (int(added), int(removed))
    return stats


def touched_tests(root, main, branch, patterns):
    """The existing test files whose net diff removes or rewrites something: [(path, why)]."""
    stat = numstat(root, "diff", "%s...%s" % (main, branch))
    on_main = set(p for p in git(root, "ls-tree", "-r", "-z", "--name-only", main).split("\0") if p)
    found = []
    for path, (added, removed) in sorted(stat.items()):
        if path.endswith(DOC_EXT) or path not in on_main or not any(p.search(path) for p in patterns):
            continue
        if added is None:
            found.append((path, "binary"))
        elif removed > 0:
            found.append((path, "%d lines removed or rewritten" % removed))
    return found


def declarations(root, main, branch):
    """[(sha, rest, changed)] for every commit on main..branch whose subject opens with REVOKED-TEST: `rest` is what follows
    the prefix and `changed` the set of files that commit removes or rewrites lines of (or deletes, or changes as binary)."""
    out = []
    log = git(root, "log", "--format=%H%x1f%s", "%s..%s" % (main, branch))
    for line in log.splitlines():
        sha, _, subject = line.partition("\x1f")
        if not subject.startswith(PREFIX):
            continue
        stat = numstat(root, "show", sha, "--format=")
        changed = set(p for p, (a, r) in stat.items() if a is None or r > 0)
        out.append((sha, subject[len(PREFIX):], changed))
    return out


def names(rest, path):
    """Does the text after `REVOKED-TEST ` name exactly this path (and not merely contain it)?"""
    return rest == path or rest.startswith(path + ":") or rest.startswith(path + " ")


def check(root, main, branch, patterns):
    """(lines, exit code)."""
    touched = touched_tests(root, main, branch, patterns)
    if not touched:
        return ["test-edit-guard: no existing test changed beyond additions"], 0
    decl = declarations(root, main, branch)
    lines, missing = [], 0
    for path, why in touched:
        carriers = [d for d in decl if names(d[1], path) and path in d[2]]
        if carriers:
            lines.append("declared    %s  (%s)" % (path, why))
            continue
        missing += 1
        lines.append("UNDECLARED  %s  (%s)" % (path, why))
        header_only = [d[0][:9] for d in decl if names(d[1], path)]
        if header_only:
            lines.append("            REVOKED-TEST commit %s names it but changes none of its lines: a header declares nothing" % ", ".join(header_only))
    if missing:
        lines.append(
            "test-edit-guard: %d existing test file(s) changed with no commit whose first line is `REVOKED-TEST <file>:<test name>` "
            "and which changes that file. For each: revert the edit, or put exactly that edit in a commit of its own with that "
            "first line and a body quoting the criterion or decision that revokes the old assertion. If the edit already sits in an "
            "earlier commit: restore the file from %s in a commit, then redo the edit in the REVOKED-TEST commit." % (missing, main))
        return lines, 1
    lines.append("test-edit-guard: every changed existing test file has its REVOKED-TEST commit")
    return lines, 0


def run(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root")
    ap.add_argument("--main", default="main")
    ap.add_argument("--branch", default="HEAD")
    ap.add_argument("--pattern", action="append", default=[], help="extra regex for test files (e.g. the gate script)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.root or not os.path.isdir(a.root):
        print("give --root <the feature's working tree>", file=sys.stderr)
        return 2
    try:
        patterns = [re.compile(p) for p in DEFAULT_PATTERNS + a.pattern]
        lines, code = check(a.root, a.main, a.branch, patterns)
    except (GitError, re.error) as e:
        print("test-edit-guard: %s" % e, file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return code


def main():
    # A file name with an accent must not crash a Windows console the one time the guard has something to say.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    return run(sys.argv[1:])


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
            self.git("init", "-q", "-b", "main")
            self.write(base_files)
            self.commit("base")
            self.git("checkout", "-q", "-b", "feat")

        def git(self, *a):
            return subprocess.run(["git", "-C", self.dir] + list(a), capture_output=True, text=True, encoding="utf-8", env=env, check=True).stdout

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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
