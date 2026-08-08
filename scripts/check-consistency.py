#!/usr/bin/env python3
"""Check the invariants that keep this skill's duplicated facts in sync.

Why this exists: the skill duplicates facts on purpose, so each reference file is
self-sufficient for the agent reading it. Nothing keeps the copies in step, and a
full review of 3.6.0 traced fifteen of its thirty-seven findings to exactly that
-- a release added a fact in one place and left the places that write, audit and
document it on the previous version. Every check below is one of those failures,
turned into something a command can catch.

Maintainer tool. Not copied by the installers.

    python3 scripts/check-consistency.py            # from the repo root
    python3 scripts/check-consistency.py --root DIR

Exit codes: 0 all checks passed, 1 at least one failed, 2 usage error.
"""

import argparse
import json
import os
import re
import sys

REFERENCES = ["scope-phase.md", "index-phase.md", "decompose-phase.md", "handoff-seed.md"]
GUIDES = ["HOW-IT-WORKS.md", "HOW-IT-WORKS.pt-BR.md", "HOW-IT-WORKS.es.md"]
READMES = ["README.md", "README.pt-BR.md", "README.es.md"]

# Block names the skill writes into GENERATED files. In this repo's own prose they
# are always cited inline; a line that starts with one is a real heading, which is
# how a wrapped quotation silently becomes a section -- and handoff-seed.md is the
# file that tells an agent to find `## Handoff` and overwrite everything after it.
GENERATED_BLOCKS = [
    "## Status", "## Handoff", "## Decisions", "## Cross-Cutting Decisions",
    "## Open Questions", "## Expected Gray Areas", "## Coverage",
]

# Counts asserted in prose that must match reality. Each one drifted at least once.
COUNTED_FACTS = [
    ("non-negotiable rules", 13),
    ("ledger states", 4),          # decision / N/A because / not decided / deferred to feature
    ("coverage dispositions", 4),  # feature / covered by reference / deferred / pre-existing
    ("handoff fields", 8),         # tlc-spec-driven v3.x's schema
]
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
}

failures = []
checks_run = 0


def check(name, ok, detail=""):
    global checks_run
    checks_run += 1
    if ok:
        print("  ✓ %s" % name)
    else:
        print("  ✗ %s" % name)
        if detail:
            for line in detail.rstrip().splitlines():
                print("      " + line)
        failures.append(name)


def read(root, *parts):
    path = os.path.join(root, *parts)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def strip_fences(text):
    """Blank out fenced code so templates do not read as prose."""
    out, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append("")
            continue
        out.append("" if fence else line)
    return "\n".join(out)


def headings(text):
    return [m.group(0).rstrip() for m in
            re.finditer(r"^#{1,6} .+$", strip_fences(text), re.M)]


def code_spans(text):
    """Normalised: lines joined first, so a span wrapped across two lines counts once."""
    joined = re.sub(r"\s*\n\s*", " ", strip_fences(text))
    return sorted(re.findall(r"`([^`\n]+)`", joined))


# --------------------------------------------------------------------------


def check_versions(root):
    skill = read(root, "SKILL.md") or ""
    m = re.search(r"^\s*version:\s*\"?([^\"\s]+)", skill, re.M)
    sv = m.group(1) if m else None
    try:
        pv = json.loads(read(root, ".claude-plugin", "plugin.json"))["version"]
        mv = json.loads(read(root, ".claude-plugin", "marketplace.json"))["plugins"][0]["version"]
    except Exception as exc:  # noqa: BLE001
        check("three version declarations agree", False, "could not parse manifests: %s" % exc)
        return
    check("three version declarations agree",
          sv == pv == mv,
          "SKILL.md=%s plugin.json=%s marketplace.json=%s" % (sv, pv, mv))


def check_section_pointers(root):
    """Every quoted section name cited in prose must resolve to a real heading."""
    canonical, texts = set(), {}
    for name in ["SKILL.md"] + [os.path.join("references", r) for r in REFERENCES]:
        text = read(root, name)
        if text is None:
            continue
        texts[name] = text
        for h in headings(text):
            canonical.add(h.lstrip("# ").strip())

    unresolved, split = [], []
    for name, text in texts.items():
        stripped = strip_fences(text)
        for m in re.finditer(r'"([A-Z][^"\n]{6,80})"', stripped):
            cited = m.group(1).strip()
            if cited in canonical:
                continue
            # A citation broken across a newline: the head is a strict prefix of a
            # real heading. That is the shape a name-based lookup cannot find.
            if any(c.startswith(cited) for c in canonical):
                split.append("%s: %r is a prefix of a real section — wrapped citation?"
                             % (name, cited))
            elif re.match(r"^(Step \d|Phase \d|[A-Z][a-z]+ing |When |What |Output |Only )", cited):
                unresolved.append("%s: %r resolves to no heading" % (name, cited))

    check("cited section names resolve", not unresolved, "\n".join(unresolved))
    check("no section name split across lines", not split, "\n".join(split))


def check_generated_blocks_never_start_a_line(root):
    bad = []
    for r in REFERENCES:
        text = read(root, "references", r)
        if text is None:
            continue
        for i, line in enumerate(strip_fences(text).splitlines(), 1):
            for block in GENERATED_BLOCKS:
                if line.rstrip() == block:
                    bad.append("references/%s:%d starts with %r" % (r, i, block))
    check("generated-block names never start a line in references/", not bad, "\n".join(bad))


def check_rule_count(root):
    skill = read(root, "SKILL.md") or ""
    m = re.search(r"^## Non-negotiable rules$(.*?)^## ", skill, re.M | re.S)
    n = len(re.findall(r"^\d+\. ", m.group(1), re.M)) if m else 0
    check("SKILL.md carries exactly 13 non-negotiable rules", n == 13, "found %d" % n)

    wrong = []
    for name in ["SKILL.md"] + [os.path.join("references", r) for r in REFERENCES]:
        text = read(root, name) or ""
        for mm in re.finditer(r"\b(\w+)\s+(?:non-negotiable\s+)?rules\b", text, re.I):
            word = mm.group(1).lower()
            if word in NUMBER_WORDS and NUMBER_WORDS[word] != 13:
                wrong.append("%s: %r rules" % (name, mm.group(1)))
            elif word.isdigit() and int(word) != 13:
                wrong.append("%s: %r rules" % (name, mm.group(1)))
    check("no file claims a rule count other than 13", not wrong, "\n".join(wrong))


def check_counted_facts(root):
    """Catch 'three states' surviving in one file while another says four."""
    nouns = {
        "ledger states": (r"\b(\w+)\s+(?:legal\s+|possible\s+)?states\b", 4),
        # Anchored on "valid": scope-phase also says "Two dispositions" about the
        # extend-versus-new-section fork, which is a different noun entirely.
        "coverage dispositions": (r"\b(\w+)\s+dispositions\s+are\s+valid\b", 4),
    }
    wrong = []
    for label, (pattern, expected) in nouns.items():
        for r in REFERENCES:
            text = read(root, "references", r) or ""
            for mm in re.finditer(pattern, text, re.I):
                word = mm.group(1).lower()
                val = NUMBER_WORDS.get(word, int(word) if word.isdigit() else None)
                if val is not None and val != expected:
                    line = text[:mm.start()].count("\n") + 1
                    wrong.append("references/%s:%d says %r %s (expected %d)"
                                 % (r, line, mm.group(1), label.split()[-1], expected))
    check("enumerated facts agree across references", not wrong, "\n".join(wrong))


def check_installer_payload(root):
    """What the installers actually copy, versus what prose says they copy."""
    sh = read(root, "install.sh") or ""
    ps = read(root, "install.ps1") or ""

    sh_refs = set(re.findall(r"[\w-]+\.md", re.search(
        r"REQUIRED_REFS=\(([^)]*)\)", sh).group(1))) if "REQUIRED_REFS=(" in sh else set()
    ps_refs = set(re.findall(r"'([\w.-]+\.md)'", re.search(
        r"\$RequiredRefs = @\((.*?)\)", ps, re.S).group(1))) if "$RequiredRefs = @(" in ps else set()
    sh_scr = set(re.findall(r"[\w-]+\.py", re.search(
        r"REQUIRED_SCRIPTS=\(([^)]*)\)", sh).group(1))) if "REQUIRED_SCRIPTS=(" in sh else set()
    ps_scr = set(re.findall(r"'([\w.-]+\.py)'", re.search(
        r"\$RequiredScripts = @\((.*?)\)", ps, re.S).group(1))) if "$RequiredScripts = @(" in ps else set()

    check("both installers require the same references",
          sh_refs == ps_refs, "sh=%s ps1=%s" % (sorted(sh_refs), sorted(ps_refs)))
    check("both installers require the same runtime scripts",
          sh_scr == ps_scr, "sh=%s ps1=%s" % (sorted(sh_scr), sorted(ps_scr)))

    on_disk = set(os.listdir(os.path.join(root, "references")))
    check("every references/ file is required by the installers",
          on_disk == sh_refs,
          "on disk but not required: %s" % sorted(on_disk - sh_refs))

    # The prose that claims what reaches a user's disk. It said "SKILL.md and
    # references/" for a whole release after scripts/ started shipping.
    stale = []
    for name in ["SKILL.md"] + [os.path.join("references", r) for r in REFERENCES]:
        text = read(root, name) or ""
        for mm in re.finditer(r"copy only `?SKILL\.md`?[^.\n]*", text):
            if "scripts" not in mm.group(0):
                line = text[:mm.start()].count("\n") + 1
                stale.append("%s:%d %r" % (name, line, mm.group(0)[:70]))
    check("payload claims mention scripts/ now that it ships", not stale, "\n".join(stale))

    for scr in sorted(sh_scr):
        check("required runtime script exists: %s" % scr,
              os.path.isfile(os.path.join(root, "scripts", scr)))


def check_trilingual_parity(root, folder, names, label):
    texts = {n: read(root, folder, n) if folder else read(root, n) for n in names}
    if any(t is None for t in texts.values()):
        check("%s: all three files present" % label, False)
        return
    base = names[0]
    hs = {n: headings(t) for n, t in texts.items()}
    check("%s: heading counts match" % label,
          len({len(v) for v in hs.values()}) == 1,
          " ".join("%s=%d" % (n, len(v)) for n, v in hs.items()))
    cs = {n: code_spans(t) for n, t in texts.items()}
    for n in names[1:]:
        only_base = sorted(set(cs[base]) - set(cs[n]))
        only_n = sorted(set(cs[n]) - set(cs[base]))
        check("%s: code spans identical (%s vs %s)" % (label, base, n),
              not only_base and not only_n,
              ("only in %s: %s\nonly in %s: %s"
               % (base, only_base[:6], n, only_n[:6])) if (only_base or only_n) else "")


def check_changelog(root):
    text = read(root, "CHANGELOG.md") or ""
    skill = read(root, "SKILL.md") or ""
    m = re.search(r"^\s*version:\s*\"?([^\"\s]+)", skill, re.M)
    version = m.group(1) if m else "?"
    check("CHANGELOG has an entry for the current version",
          re.search(r"^## %s\b" % re.escape(version), text, re.M) is not None,
          "no '## %s' heading" % version)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isfile(os.path.join(root, "SKILL.md")):
        print("no SKILL.md at %s — run from the repo root or pass --root" % root,
              file=sys.stderr)
        return 2

    print("spec-driven-roadmap: consistency check\n")
    print("versions"); check_versions(root)
    print("cross-file pointers"); check_section_pointers(root)
    check_generated_blocks_never_start_a_line(root)
    print("counted facts"); check_rule_count(root); check_counted_facts(root)
    print("installers"); check_installer_payload(root)
    print("trilingual parity")
    check_trilingual_parity(root, "guide", GUIDES, "guide")
    check_trilingual_parity(root, "", READMES, "README")
    print("changelog"); check_changelog(root)

    print("\n%d checks, %d failed" % (checks_run, len(failures)))
    if failures:
        print("failed: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
