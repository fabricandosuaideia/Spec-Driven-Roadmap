#!/usr/bin/env python3
"""Run install.sh (and install.ps1, when PowerShell is there) against release archives built from this working tree.

Maintainer tooling, not shipped. Why it exists: the installer is the one place where a project's local change to its
copy of the skill is replaced for good, and nothing exercised it. The scenarios below plant the shapes that matter:
a copy that is the release it claims to be, a copy with a modified file and an added one, a version with no archive,
a copy with no version at all, a fresh install, and a non-interactive shell. No network: SDR_ARCHIVE_BASE points at a
folder of archives built here (a "current" one from the working tree, and an "old release" one with a different
version and a different plan-pipeline.py, so the installed copy and the new one are not the same).

    python3 scripts/check-installers.py

Exit 0: every scenario held. 1: one did not. A missing PowerShell is reported and skipped, never a pass for it.
"""

import filecmp
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OLD = "0.1.0"
failures = []


def expect(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond or not detail else "\n         " + detail.replace("\n", "\n         ")))
    if not cond:
        failures.append(name)


def required(kind):
    sh = open(os.path.join(ROOT, "install.sh"), encoding="utf-8").read()
    return re.search(r"REQUIRED_%s=\(([^)]*)\)" % kind, sh).group(1).split()


def current_version():
    m = re.search(r'^\s*version:\s*"([^"]+)"', open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read(), re.M)
    return m.group(1)


def build_tree(dest, version, old):
    """SKILL.md, references/ and scripts/ of the working tree under dest; the old release differs in version and in
    one script, so a copy installed from it is not the current one."""
    os.makedirs(dest)
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    skill = re.sub(r'(^\s*version:\s*")[^"]+(")', r"\g<1>%s\g<2>" % version, skill, count=1, flags=re.M)
    open(os.path.join(dest, "SKILL.md"), "w", encoding="utf-8").write(skill)
    shutil.copytree(os.path.join(ROOT, "references"), os.path.join(dest, "references"))
    shutil.copytree(os.path.join(ROOT, "scripts"), os.path.join(dest, "scripts"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if old:
        with open(os.path.join(dest, "scripts", "plan-pipeline.py"), "a", encoding="utf-8") as fh:
            fh.write("\n# release %s\n" % version)


def archive(tree, base, kind, ref, prefix):
    """tree -> <base>/<kind>/<ref>.tar.gz and .zip with the top folder GitHub gives (Spec-Driven-Roadmap-<...>)."""
    os.makedirs(os.path.join(base, kind), exist_ok=True)
    with tarfile.open(os.path.join(base, kind, ref + ".tar.gz"), "w:gz") as t:
        t.add(tree, arcname=prefix)
    with zipfile.ZipFile(os.path.join(base, kind, ref + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for dp, _d, fs in os.walk(tree):
            for f in fs:
                full = os.path.join(dp, f)
                z.write(full, os.path.join(prefix, os.path.relpath(full, tree)))


def digest(folder):
    h = hashlib.sha256()
    for dp, _d, fs in sorted(os.walk(folder)):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, folder).encode())
            h.update(open(p, "rb").read())
    return h.hexdigest()


def installed_copy(proj, old_tree, version=None, patch=False):
    dest = os.path.join(proj, ".claude", "skills", "spec-driven-roadmap")
    os.makedirs(os.path.join(dest, "scripts"))
    shutil.copy(os.path.join(old_tree, "SKILL.md"), dest)
    shutil.copytree(os.path.join(old_tree, "references"), os.path.join(dest, "references"))
    for scr in required("SCRIPTS"):
        shutil.copy(os.path.join(old_tree, "scripts", scr), os.path.join(dest, "scripts"))
    if version is not None:
        s = open(os.path.join(dest, "SKILL.md"), encoding="utf-8").read()
        s = re.sub(r'(^\s*version:\s*")[^"]+(")', r"\g<1>%s\g<2>" % version, s, count=1, flags=re.M) if version else re.sub(r"^\s*version:.*\n", "", s, count=1, flags=re.M)
        open(os.path.join(dest, "SKILL.md"), "w", encoding="utf-8").write(s)
    if patch:
        with open(os.path.join(dest, "scripts", "plan-pipeline.py"), "a", encoding="utf-8") as fh:
            fh.write("\n# a fix this project needed before a release had it\n")
        open(os.path.join(dest, "scripts", "extra-local.py"), "w", encoding="utf-8").write("print('mine')\n")
    return dest


def run(cmd, cwd, base, **kw):
    env = dict(os.environ, SDR_ARCHIVE_BASE="file://" + base)
    return subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          start_new_session=True, **kw)  # no controlling terminal: /dev/tty cannot be opened


def main():
    tmp = tempfile.mkdtemp(prefix="check-installers-")
    try:
        base = os.path.join(tmp, "archives")
        new_v = current_version()
        new_tree, old_tree = os.path.join(tmp, "new"), os.path.join(tmp, "old")
        build_tree(new_tree, new_v, old=False)
        build_tree(old_tree, OLD, old=True)
        archive(new_tree, base, "heads", "main", "Spec-Driven-Roadmap-main")
        archive(old_tree, base, "tags", "v" + OLD, "Spec-Driven-Roadmap-" + OLD)
        sh = ["bash", os.path.join(ROOT, "install.sh")]

        print("install.sh")
        proj = os.path.join(tmp, "p1"); os.makedirs(proj)
        dest = installed_copy(proj, old_tree)
        before = digest(dest)
        r = run(sh + ["--check"], proj, base)
        expect("--check on a copy that is the release it claims to be says nothing local is lost",
               r.returncode == 0 and "unchanged" in r.stdout and "nothing was changed" in r.stdout and "installed: %s" % OLD in r.stdout and "available: %s" % new_v in r.stdout, r.stdout + r.stderr)
        expect("--check writes nothing", digest(dest) == before)

        proj = os.path.join(tmp, "p2"); os.makedirs(proj)
        dest = installed_copy(proj, old_tree, patch=True)
        before = digest(dest)
        r = run(sh + ["--check"], proj, base)
        expect("--check lists the modified file and the added one",
               r.returncode == 0 and re.search(r"modified scripts/plan-pipeline\.py", r.stdout) and re.search(r"added\s+scripts/extra-local\.py", r.stdout)
               and "2 file(s)" in r.stdout and "nothing was changed" in r.stdout, r.stdout + r.stderr)
        r_d = run(sh + ["--check", "--diff"], proj, base)
        expect("--check --diff shows what the patch changed, not only that it exists",
               r_d.returncode == 0 and "--- scripts/plan-pipeline.py (release v%s -> installed copy)" % OLD in r_d.stdout and
               "+# a fix this project needed before a release had it" in r_d.stdout, r_d.stdout + r_d.stderr)
        expect("and says 'installed ..., available ...' instead of 'installing' when it installs nothing",
               "installed %s, available %s" % (OLD, new_v) in r.stdout and "installing" not in r.stdout, r.stdout)
        expect("and does not list the files the project left alone", "SKILL.md" not in r.stdout.replace("installed: ", "") or "modified SKILL.md" not in r.stdout)
        expect("--check writes nothing, even over local changes", digest(dest) == before)
        r = run(sh, proj, base)
        expect("without --force, in a shell with no terminal, an existing install is refused and nothing changes",
               r.returncode == 1 and digest(dest) == before, r.stdout + r.stderr)
        r = run(sh + ["--force"], proj, base)
        expect("--force lists what it replaces, then installs the current version",
               r.returncode == 0 and "REPLACES them" in r.stdout and "modified scripts/plan-pipeline.py" in r.stdout and "v%s installed" % new_v in r.stdout, r.stdout + r.stderr)
        expect("the project's patch and its extra file are gone, the current files are in",
               not os.path.exists(os.path.join(dest, "scripts", "extra-local.py")) and
               filecmp.cmp(os.path.join(dest, "scripts", "plan-pipeline.py"), os.path.join(new_tree, "scripts", "plan-pipeline.py"), shallow=False))
        expect("references/upgrade-notes.md is part of what is installed", os.path.isfile(os.path.join(dest, "references", "upgrade-notes.md")))

        proj = os.path.join(tmp, "p3"); os.makedirs(proj)
        dest = installed_copy(proj, old_tree, version="9.9.9", patch=True)
        r = run(sh + ["--check"], proj, base)
        expect("a version with no archive is 'could not check', not an error and not 'unchanged'",
               r.returncode == 0 and "could not check" in r.stdout and "unchanged" not in r.stdout, r.stdout + r.stderr)
        r = run(sh + ["--force"], proj, base)
        expect("and a forced install still goes ahead", r.returncode == 0 and "v%s installed" % new_v in r.stdout, r.stdout + r.stderr)

        proj = os.path.join(tmp, "p4"); os.makedirs(proj)
        dest = installed_copy(proj, old_tree, version="")
        r = run(sh + ["--check"], proj, base)
        expect("a copy with no version line is 'could not check' too", r.returncode == 0 and "could not check" in r.stdout and "unchanged" not in r.stdout, r.stdout + r.stderr)

        proj = os.path.join(tmp, "p5"); os.makedirs(proj)
        r = run(sh + ["--check"], proj, base)
        expect("--check with nothing installed says so and installs nothing",
               r.returncode == 0 and "installed: none" in r.stdout and not os.path.exists(os.path.join(proj, ".claude")), r.stdout + r.stderr)
        r = run(sh, proj, base)
        expect("a fresh install needs no check and no --force",
               r.returncode == 0 and "differ" not in r.stdout and "v%s installed" % new_v in r.stdout and os.path.isfile(os.path.join(proj, ".claude", "skills", "spec-driven-roadmap", "SKILL.md")), r.stdout + r.stderr)

        print("\ninstall.ps1")
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            print("  --   PowerShell not found: install.ps1 was NOT run. This is not a pass for it.")
        else:
            ps = [pwsh, "-NoProfile", "-NonInteractive", "-File", os.path.join(ROOT, "install.ps1")]
            proj = os.path.join(tmp, "q1"); os.makedirs(proj)
            dest = installed_copy(proj, old_tree, patch=True)
            before = digest(dest)
            r = run(ps + ["-Check"], proj, base)
            expect("-Check lists the modified file and the added one and changes nothing",
                   r.returncode == 0 and re.search(r"modified scripts/plan-pipeline\.py", r.stdout) and re.search(r"added\s+scripts/extra-local\.py", r.stdout)
                   and "nothing was changed" in r.stdout and digest(dest) == before, r.stdout + r.stderr)
            r = run(ps + ["-Check", "-Diff"], proj, base)
            expect("-Check -Diff shows the lines the patch added", "(release v%s -> installed copy)" % OLD in r.stdout and "+ # a fix this project needed before a release had it" in r.stdout, r.stdout + r.stderr)
            expect("-Check -Diff does not say 'installing'", "installing" not in r.stdout, r.stdout)
            r = run(ps, proj, base)
            expect("without -Force, non-interactive, an existing install is refused and nothing changes", r.returncode != 0 and digest(dest) == before, r.stdout + r.stderr)
            r = run(ps + ["-Force"], proj, base)
            expect("-Force lists what it replaces, then installs the current version",
                   r.returncode == 0 and "REPLACES them" in r.stdout and "v%s installed" % new_v in r.stdout, r.stdout + r.stderr)
            expect("the patch and its extra file are gone",
                   not os.path.exists(os.path.join(dest, "scripts", "extra-local.py")) and
                   filecmp.cmp(os.path.join(dest, "scripts", "plan-pipeline.py"), os.path.join(new_tree, "scripts", "plan-pipeline.py"), shallow=False))
            proj = os.path.join(tmp, "q2"); os.makedirs(proj)
            installed_copy(proj, old_tree)
            r = run(ps + ["-Check"], proj, base)
            expect("-Check on an unchanged copy says nothing local is lost", r.returncode == 0 and "unchanged" in r.stdout, r.stdout + r.stderr)
            proj = os.path.join(tmp, "q3"); os.makedirs(proj)
            installed_copy(proj, old_tree, version="9.9.9", patch=True)
            r = run(ps + ["-Check"], proj, base)
            expect("a version with no archive is 'could not check'", r.returncode == 0 and "could not check" in r.stdout and "unchanged" not in r.stdout, r.stdout + r.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
