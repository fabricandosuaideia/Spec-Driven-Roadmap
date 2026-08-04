#!/usr/bin/env bash
# =============================================================================
# spec-driven-roadmap installer
#
#   curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
#
# Installs the spec-driven-roadmap Claude Code skill (SKILL.md + references/)
# into the current project's .claude/skills/spec-driven-roadmap/, or into
# ~/.claude/skills/spec-driven-roadmap/ with --global. No git required — just
# curl and tar.
# =============================================================================

set -euo pipefail

REPO="fabricandosuaideia/Spec-Driven-Roadmap"
BRANCH="main"
SCOPE="project"
FORCE="false"

print_status()  { echo "→ $1"; }
print_success() { echo "✓ $1"; }
print_error()   { echo "✗ $1" >&2; }

show_help() {
    cat << EOF
Usage: install.sh [OPTIONS]

Install the spec-driven-roadmap skill.

Options:
    --global      Install to ~/.claude/skills/spec-driven-roadmap/ instead of
                   ./.claude/skills/spec-driven-roadmap/
    --force       Overwrite an existing install without prompting
    -h, --help    Show this help message
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --global) SCOPE="global"; shift ;;
        --force) FORCE="true"; shift ;;
        -h|--help) show_help ;;
        *) print_error "Unknown option: $1"; show_help ;;
    esac
done

if [[ "$SCOPE" == "global" ]]; then
    DEST="$HOME/.claude/skills/spec-driven-roadmap"
else
    DEST="$(pwd)/.claude/skills/spec-driven-roadmap"
fi

if [[ -d "$DEST" && "$FORCE" != "true" ]]; then
    echo "An existing install was found at: $DEST"
    read -r -p "Overwrite it? (y/N) " REPLY
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled. Re-run with --force to skip this prompt."
        exit 0
    fi
fi

for bin in curl tar; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        print_error "'$bin' is required but not found on PATH."
        exit 1
    fi
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

print_status "Downloading spec-driven-roadmap ($BRANCH)..."
TARBALL_URL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz"
if ! curl -fsSL "$TARBALL_URL" -o "$TMP_DIR/skill.tar.gz"; then
    print_error "Failed to download $TARBALL_URL"
    exit 1
fi

tar -xzf "$TMP_DIR/skill.tar.gz" -C "$TMP_DIR"
SRC_DIR="$(find "$TMP_DIR" -maxdepth 1 -mindepth 1 -type d -name "Spec-Driven-Roadmap-*" | head -n1)"

if [[ -z "$SRC_DIR" || ! -f "$SRC_DIR/SKILL.md" ]]; then
    print_error "Downloaded archive did not contain SKILL.md — aborting."
    exit 1
fi

print_status "Installing to $DEST..."
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$SRC_DIR/SKILL.md" "$DEST/"
cp -r "$SRC_DIR/references" "$DEST/"

print_success "spec-driven-roadmap installed at $DEST"
echo ""
echo "Installed:"
echo "  SKILL.md"
find "$DEST/references" -name "*.md" -type f | sed "s|$DEST/|  |" | sort
echo ""
echo "Restart Claude Code (or run /skills) to pick it up."
