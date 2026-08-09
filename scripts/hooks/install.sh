#!/usr/bin/env bash
# Point this clone's git at the tracked hooks directory.
#
# `core.hooksPath` rather than copying into `.git/hooks/`: the hook stays under
# version control, so a fix to it arrives with a pull instead of needing every
# clone to re-copy it. Nothing here is global — it configures this clone only.

set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"

git rev-parse --git-dir >/dev/null 2>&1 || {
    echo "✗ not a git repository: $repo" >&2
    exit 1
}

current="$(git config --get core.hooksPath || true)"
if [[ -n "$current" && "$current" != "scripts/hooks" ]]; then
    echo "! core.hooksPath is already set to '$current'." >&2
    echo "  Setting it to scripts/hooks would disable whatever lives there." >&2
    echo "  Resolve that by hand; nothing was changed." >&2
    exit 1
fi

chmod +x scripts/hooks/pre-commit
git config core.hooksPath scripts/hooks

echo "✓ core.hooksPath -> scripts/hooks"
echo ""
echo "  pre-commit now runs scripts/check-consistency.py when a commit touches"
echo "  SKILL.md, references/, scripts/, guide/, the READMEs, CLAUDE.md, the"
echo "  installers or the plugin manifests. Other commits are not delayed."
echo ""
echo "  Bypass with 'git commit --no-verify'. Undo with"
echo "  'git config --unset core.hooksPath'."
