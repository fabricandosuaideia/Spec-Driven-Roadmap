#!/usr/bin/env bash
#
# bump-version.sh — set the release version in the three places that declare it.
#
# WHY THIS EXISTS
# ---------------
# This repository states its version three times, and nothing keeps the three in step:
#
#   SKILL.md                          metadata.version     what an installed skill reports
#   .claude-plugin/plugin.json        version              what `/plugin install` reports
#   .claude-plugin/marketplace.json   plugins[0].version   what the marketplace listing shows
#
# The drift is not hypothetical — it already happened here. Commit `d94aae5` ("Offer a loop
# prompt at handoff") bumped `SKILL.md` and `plugin.json` to 3.2.0 and never touched
# `marketplace.json`. Commit `7954214` repeated the omission for 3.3.0. So the marketplace
# advertised **3.1.0 across two whole releases** — including the release that first shipped
# the `/loop` prompt — and was corrected only in `80debaf`, when it jumped straight from
# 3.1.0 to 3.4.0. Anyone installing from that listing had no way to tell what they got.
#
# Hence the two things this script does that a `sed -i` one-liner would not:
#
#   1. It rewrites all three declarations or none of them.
#   2. It **refuses to run at all** when the three already disagree. Bumping over a
#      divergence would erase the only evidence of which release each file was left at,
#      so the divergence has to be reconciled and committed as its own fix first.
#
# Usage:  scripts/bump-version.sh <new-version>
#         scripts/bump-version.sh 3.5.0
#
# The new version must be bare `MAJOR.MINOR.PATCH` (no leading `v`, no pre-release suffix)
# and must be strictly greater than the current one.
#
# Dependencies: bash, sed, grep. No `jq` — the manifests are edited as text, one located
# line at a time, which is also what keeps `marketplace.json`'s *other* `version` key (the
# `metadata.version` of the marketplace itself, unrelated to the plugin) from being hit.
#
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

SKILL_FILE="$REPO_ROOT/SKILL.md"
PLUGIN_FILE="$REPO_ROOT/.claude-plugin/plugin.json"
MARKET_FILE="$REPO_ROOT/.claude-plugin/marketplace.json"

SEMVER_GREP='[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*'

# Parallel arrays, filled by locate_all: file path, human label of the field, line number,
# current version. Index order is fixed: 0 = SKILL.md, 1 = plugin.json, 2 = marketplace.json.
FILES=("$SKILL_FILE" "$PLUGIN_FILE" "$MARKET_FILE")
FIELDS=("metadata.version" "version" "plugins[0].version")
LINES=()
VERSIONS=()

die() {
    printf 'bump-version: %s\n' "$1" >&2
    exit "${2:-1}"
}

usage() {
    cat >&2 <<'EOF'
usage: scripts/bump-version.sh <new-version>

Sets the release version in all three declarations at once:

  SKILL.md                          metadata.version
  .claude-plugin/plugin.json        version
  .claude-plugin/marketplace.json   plugins[0].version

<new-version> must be bare MAJOR.MINOR.PATCH and strictly greater than the current version.
The script aborts without writing anything if the three declarations already disagree.
EOF
    exit 2
}

# Print the first bare semver found in the given text, or nothing.
extract_semver() {
    printf '%s\n' "$1" | grep -o "$SEMVER_GREP" | sed -n '1p' || true
}

# --------------------------------------------------------------------------------------
# Locating the declarations
#
# Each locator prints "<lineno>" for its file and nothing when the declaration cannot be
# found. Line numbers are resolved fresh on every run, so none of this depends on the
# current shape of the files beyond the anchors named here.
# --------------------------------------------------------------------------------------

# SKILL.md: the `version:` key inside the YAML frontmatter, i.e. above the closing `---`.
# Bounded that way so a version string mentioned in the prose below can never be picked up.
locate_skill() {
    local fm_end offset
    fm_end="$(grep -n -m 2 '^---[[:space:]]*$' "$SKILL_FILE" | sed -n '2s/:.*//p' || true)"
    [ -n "$fm_end" ] || return 0
    offset="$(sed -n "1,${fm_end}p" "$SKILL_FILE" \
        | grep -n -m 1 "^[[:space:]]*version:[[:space:]]*\"\{0,1\}${SEMVER_GREP}" \
        | sed -n '1s/:.*//p' || true)"
    [ -n "$offset" ] || return 0
    printf '%s\n' "$offset"
}

# plugin.json: the single top-level `"version"` key.
locate_plugin() {
    grep -n -m 1 "\"version\"[[:space:]]*:[[:space:]]*\"${SEMVER_GREP}\"" "$PLUGIN_FILE" \
        | sed -n '1s/:.*//p' || true
}

# marketplace.json: the first `"version"` key *after* `"plugins"`, which is plugins[0]'s.
# Anchoring on `"plugins"` is what steps over `metadata.version` — the marketplace's own
# version, which lives earlier in the file and must not move when the plugin is released.
locate_marketplace() {
    local pstart offset
    pstart="$(grep -n -m 1 '"plugins"[[:space:]]*:' "$MARKET_FILE" | sed -n '1s/:.*//p' || true)"
    [ -n "$pstart" ] || return 0
    offset="$(sed -n "${pstart},\$p" "$MARKET_FILE" \
        | grep -n -m 1 "\"version\"[[:space:]]*:[[:space:]]*\"${SEMVER_GREP}\"" \
        | sed -n '1s/:.*//p' || true)"
    [ -n "$offset" ] || return 0
    printf '%s\n' "$(( pstart + offset - 1 ))"
}

# Fill LINES and VERSIONS for all three files, failing loudly on anything unreadable.
locate_all() {
    local i file lineno raw version
    for i in 0 1 2; do
        file="${FILES[$i]}"
        [ -f "$file" ] || die "not found: $file"
        case "$i" in
            0) lineno="$(locate_skill)" ;;
            1) lineno="$(locate_plugin)" ;;
            2) lineno="$(locate_marketplace)" ;;
        esac
        [ -n "$lineno" ] || die "could not find ${FIELDS[$i]} in $file"
        raw="$(sed -n "${lineno}p" "$file")"
        version="$(extract_semver "$raw")"
        [ -n "$version" ] || die "no MAJOR.MINOR.PATCH version on line $lineno of $file"
        LINES[$i]="$lineno"
        VERSIONS[$i]="$version"
    done
}

# Replace the version on one known line. Writes through a sibling temp file and copies the
# bytes back, so the target keeps its own inode and mode even if it is a symlink or +x.
write_version() {
    local file="$1" lineno="$2" new="$3" tmp
    tmp="${file}.bump.$$"
    sed "${lineno}s/${SEMVER_GREP}/${new}/" "$file" > "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"
}

# True when $1 is strictly greater than $2, comparing numerically field by field.
version_gt() {
    local a1 a2 a3 b1 b2 b3
    IFS=. read -r a1 a2 a3 <<< "$1"
    IFS=. read -r b1 b2 b3 <<< "$2"
    if [ "$((10#$a1))" -ne "$((10#$b1))" ]; then [ "$((10#$a1))" -gt "$((10#$b1))" ]; return; fi
    if [ "$((10#$a2))" -ne "$((10#$b2))" ]; then [ "$((10#$a2))" -gt "$((10#$b2))" ]; return; fi
    [ "$((10#$a3))" -gt "$((10#$b3))" ]
}

main() {
    case "${1:-}" in
        -h|--help) usage ;;
    esac
    [ "$#" -eq 1 ] || usage

    local new="$1" current i
    printf '%s\n' "$new" | grep -q "^${SEMVER_GREP}$" \
        || die "'$new' is not a bare MAJOR.MINOR.PATCH version (no leading 'v', no suffix)"

    locate_all

    # The whole point of the script: never bump over an existing divergence.
    if [ "${VERSIONS[0]}" != "${VERSIONS[1]}" ] || [ "${VERSIONS[1]}" != "${VERSIONS[2]}" ]; then
        printf 'bump-version: the three version declarations already disagree.\n\n' >&2
        for i in 0 1 2; do
            printf '  %-8s %s  (%s, line %s)\n' \
                "${VERSIONS[$i]}" "${FILES[$i]}" "${FIELDS[$i]}" "${LINES[$i]}" >&2
        done
        printf '\n%s\n%s\n' \
            "Reconcile them by hand and commit that as its own fix, then bump." \
            "Bumping now would erase which release each file was left at." >&2
        exit 1
    fi

    current="${VERSIONS[0]}"
    version_gt "$new" "$current" \
        || die "$new is not greater than the current version $current"

    for i in 0 1 2; do
        write_version "${FILES[$i]}" "${LINES[$i]}" "$new"
    done

    printf '%s -> %s\n\n' "$current" "$new"
    for i in 0 1 2; do
        printf '  updated  %s  (%s, line %s)\n' "${FILES[$i]}" "${FIELDS[$i]}" "${LINES[$i]}"
    done
    printf '\n%s\n' "Review with 'git diff', then commit the bump with the release."
}

main "$@"
