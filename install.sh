#!/usr/bin/env bash
# =============================================================================
# spec-driven-roadmap installer
#
#   curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
#
# With flags (note the `-s --`, required when piping into bash):
#   curl -fsSL .../install.sh | bash -s -- --global
#   curl -fsSL .../install.sh | bash -s -- --force
#
# Installs SKILL.md + references/ into .claude/skills/spec-driven-roadmap/ in
# the current project, or ~/.claude/skills/... with --global. Needs curl + tar.
# =============================================================================

set -euo pipefail

REPO="fabricandosuaideia/Spec-Driven-Roadmap"
BRANCH="${SDR_BRANCH:-main}"
SKILL_NAME="spec-driven-roadmap"
SCOPE="project"
FORCE="false"

# The skill is these files and nothing else. Used to validate the download
# before anything on disk is touched.
REQUIRED_REFS=(scope-phase.md index-phase.md decompose-phase.md handoff-seed.md)

print_status()  { echo "→ $1"; }
print_success() { echo "✓ $1"; }
print_error()   { echo "✗ $1" >&2; }

show_help() {
    cat << EOF
Usage: install.sh [OPTIONS]

Install the spec-driven-roadmap Claude Code skill.

Options:
    --global      Install to ~/.claude/skills/${SKILL_NAME}/
                   (default: ./.claude/skills/${SKILL_NAME}/)
    --force       Overwrite an existing install without prompting
    -h, --help    Show this help message

Examples:
    curl -fsSL <url>/install.sh | bash
    curl -fsSL <url>/install.sh | bash -s -- --global
    curl -fsSL <url>/install.sh | bash -s -- --force
    ./install.sh --global --force

When piping into bash, flags MUST come after \`-s --\`; \`| bash --global\`
is parsed by bash itself and fails.
EOF
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --global) SCOPE="global"; shift ;;
        --force)  FORCE="true"; shift ;;
        -h|--help) show_help 0 ;;
        *) print_error "Unknown option: $1"; show_help 2 ;;
    esac
done

if [[ "$SCOPE" == "global" ]]; then
    DEST="$HOME/.claude/skills/$SKILL_NAME"
else
    DEST="$(pwd)/.claude/skills/$SKILL_NAME"
fi

for bin in curl tar; do
    command -v "$bin" >/dev/null 2>&1 || { print_error "'$bin' is required but not on PATH."; exit 1; }
done

# ---------------------------------------------------------------------------
# Overwrite guard.
#
# Read from the terminal, never stdin: under `curl | bash` the script body IS
# stdin, so a bare `read` swallows the next line of the script instead of user
# input. With no tty (CI, nested pipe) we refuse rather than guess, so the
# failure is visible instead of masquerading as a user cancellation.
# ---------------------------------------------------------------------------
if [[ -d "$DEST" && "$FORCE" != "true" ]]; then
    echo "An existing install was found at: $DEST"
    # Test by OPENING /dev/tty, not by `[[ -r /dev/tty ]]`: in containers the
    # path can exist and still fail to open, and a failed redirect would fall
    # through to an empty answer — i.e. a silent cancel, the very bug this
    # guard exists to avoid.
    if { exec 3< /dev/tty; } 2>/dev/null; then
        read -r -p "Overwrite it? (y/N) " REPLY <&3 || REPLY=""
        exec 3<&-
        if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 0
        fi
    else
        print_error "Non-interactive shell and $DEST already exists."
        echo "Re-run with --force to overwrite:" >&2
        echo "  curl -fsSL <url>/install.sh | bash -s -- --force" >&2
        exit 1
    fi
fi

TMP_DIR="$(mktemp -d)"
STAGE="${DEST}.tmp.$$"
trap 'rm -rf "$TMP_DIR" "$STAGE"' EXIT

print_status "Downloading $SKILL_NAME ($BRANCH)..."
TARBALL_URL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz"
if ! curl -fsSL "$TARBALL_URL" -o "$TMP_DIR/skill.tar.gz"; then
    print_error "Failed to download $TARBALL_URL"
    echo "If the repository is private, GitHub returns 404 to unauthenticated" >&2
    echo "requests. Clone it and run ./install.sh from the checkout instead." >&2
    exit 1
fi

tar -xzf "$TMP_DIR/skill.tar.gz" -C "$TMP_DIR"
# -print -quit rather than `| head -n1`: no pipeline, so no SIGPIPE interaction
# with `set -o pipefail`.
SRC_DIR="$(find "$TMP_DIR" -maxdepth 1 -mindepth 1 -type d -name 'Spec-Driven-Roadmap-*' -print -quit)"

# Validate the payload BEFORE touching the destination. A partial archive that
# yielded SKILL.md but no references/ would install a skill whose every
# procedure link is dead — silent capability loss.
[[ -n "$SRC_DIR" && -f "$SRC_DIR/SKILL.md" ]] || { print_error "Archive has no SKILL.md — aborting."; exit 1; }
[[ -d "$SRC_DIR/references" ]] || { print_error "Archive has no references/ — aborting."; exit 1; }
for ref in "${REQUIRED_REFS[@]}"; do
    [[ -f "$SRC_DIR/references/$ref" ]] || { print_error "Archive is missing references/$ref — aborting."; exit 1; }
done

# Stage into a sibling, then swap. The destination is never left half-written.
print_status "Installing to $DEST..."
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$SRC_DIR/SKILL.md" "$STAGE/"
cp -r "$SRC_DIR/references" "$STAGE/"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
mv "$STAGE" "$DEST"

print_success "$SKILL_NAME installed at $DEST"
echo ""
echo "Installed:"
echo "  SKILL.md"
find "$DEST/references" -name '*.md' -type f | sed "s|$DEST/|  |" | sort
cat << EOF

Next steps:
  1. Restart Claude Code (or run /skills) to pick it up.
  2. Install a downstream spec-driven skill if you have not yet — the roadmap
     hands off to it. Default assumption is tlc-spec-driven:
       npx @tech-leads-club/agent-skills install --skill tlc-spec-driven -a claude-code
  3. Start it with any of:
       "generate a roadmap from docs/PRD.md"
       "plan product"            (interview - when you have no document yet)
       "I don't know what to build yet"
EOF
