<#
.SYNOPSIS
    Installs the spec-driven-roadmap Claude Code skill on Windows.

.DESCRIPTION
    Downloads SKILL.md + references/ + scripts/ and installs them into
    .claude\skills\spec-driven-roadmap\ in the current directory, or into
    $HOME\.claude\skills\spec-driven-roadmap\ with -Global.

    Uses only built-in PowerShell cmdlets - no curl, tar, bash, WSL or Git Bash
    required. Requires PowerShell 5.1 or later (ships with Windows 10+).

.PARAMETER Global
    Install to $HOME\.claude\skills\ instead of the current project.

.PARAMETER Force
    Overwrite an existing install without prompting.

.PARAMETER Diff
    With the list of changed files, also print what each one changed (the lines that differ from the release, at
    most 80 per file) - the way to learn what a local patch was for.

.PARAMETER Check
    Change nothing: print the installed version, the available one, and which files of the installed copy differ
    from the release it claims to be.

.EXAMPLE
    irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 | iex

.EXAMPLE
    # With parameters, the piped form cannot take arguments - download first:
    irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 -OutFile install.ps1
    .\install.ps1 -Global -Force
#>
[CmdletBinding()]
param(
    [switch]$Global,
    [switch]$Force,
    [switch]$Check,
    [switch]$Diff
)

$ErrorActionPreference = 'Stop'

$Repo      = 'fabricandosuaideia/Spec-Driven-Roadmap'
$Branch    = if ($env:SDR_BRANCH) { $env:SDR_BRANCH } else { 'main' }
$SkillName = 'spec-driven-roadmap'
# Where the release archives live. Only tests change it (a file:// folder), so nothing here needs the network.
$ArchiveBase = if ($env:SDR_ARCHIVE_BASE) { $env:SDR_ARCHIVE_BASE } else { "https://github.com/$Repo/archive/refs" }

# The skill is these files and nothing else. Used to validate the download
# before anything on disk is touched.
$RequiredScripts = @('convert-to-multi.py', 'check-roadmap.py', 'measure-agents.py', 'feature-brief.py', 'status-block.py', 'write-agents.py', 'plan-pipeline.py', 'roadmap-pipeline.js', 'manager-pipeline.js', 'triage-probe.py', 'record-barrier.py', 'bench-gate.py')
$RequiredRefs = @(
    'scope-phase.md',
    'index-phase.md',
    'decompose-phase.md',
    'handoff-seed.md',
    'handover-prompt.md',
    'loop-tlc-spec-driven.md',
    'loop-tlc-spec-lean.md',
    'upgrade-project.md',
    'upgrade-notes.md',
    'manager-mode.md'
)

function Write-Status  { param($m) Write-Host "-> $m" }
function Write-Ok      { param($m) Write-Host "OK $m" -ForegroundColor Green }
function Write-Fail    { param($m) Write-Host "ERROR $m" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# Read the version out of a SKILL.md frontmatter, which carries it as an
# indented, QUOTED scalar:
#
#     metadata:
#       version: "3.5.0"
#
# so the quotes have to come off. Plain -match over the lines, nothing that
# needs PowerShell 7. A SKILL.md predating the field - or one that cannot be
# read - degrades to 'unknown' rather than throwing: $ErrorActionPreference is
# 'Stop', so an unguarded Get-Content would abort the whole install, and a
# missing version line is no reason to refuse to install.
# ---------------------------------------------------------------------------
function Get-SkillVersion {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return 'unknown' }
    try { $lines = Get-Content -LiteralPath $Path } catch { return 'unknown' }
    if (-not $lines) { return 'unknown' }
    $inFrontmatter = $false
    foreach ($line in $lines) {
        if ($null -eq $line) { continue }
        # TrimEnd() so a CRLF checkout does not smuggle a stray \r into the
        # version string and make every comparison differ.
        $line = $line.TrimEnd()
        if ($line -eq '---') {
            if ($inFrontmatter) { break }
            $inFrontmatter = $true
            continue
        }
        if ($inFrontmatter -and $line -match '^\s*version:\s*"?([^"\s]+)') { return $Matches[1] }
    }
    return 'unknown'
}

if ($Global) {
    $Dest = Join-Path $HOME ".claude\skills\$SkillName"
} else {
    $Dest = Join-Path (Get-Location).Path ".claude\skills\$SkillName"
}

# --- Overwrite guard -------------------------------------------------------
# `irm ... | iex` cannot pass parameters, so an interactive prompt is the only
# way a piped user can confirm. When the host is non-interactive we refuse
# loudly rather than guessing.
if ((Test-Path -LiteralPath $Dest) -and -not $Force -and -not $Check) {
    Write-Host "An existing install was found at: $Dest"
    $interactive = $Host.UI.RawUI -and -not [Console]::IsInputRedirected
    if ($interactive) {
        $reply = Read-Host 'Overwrite it? (y/N)'
        if ($reply -notmatch '^[Yy]') {
            Write-Host 'Installation cancelled.'
            exit 0
        }
    } else {
        Write-Fail "Non-interactive session and $Dest already exists."
        Write-Host 'Download the script and re-run it with -Force:' -ForegroundColor Yellow
        Write-Host '  irm <url>/install.ps1 -OutFile install.ps1; .\install.ps1 -Force' -ForegroundColor Yellow
        exit 1
    }
}

# --- What did the project change in its copy of the skill? ------------------
# Same idea as install.sh: an installed copy patched locally is replaced by a plain install without a word, and
# whatever setting depended on the patch stops working. The comparison is against the release the copy CLAIMS to be
# (its own version's archive), over the files of the installed copy. Any failure only means "could not check".
function Get-Archive {
    param([string]$Url, [string]$OutFile)
    if ($Url -like 'file://*') {
        $local = ([Uri]$Url).LocalPath
        Copy-Item -LiteralPath $local -Destination $OutFile -Force
    } else {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
    }
}
function Get-ReleaseTree {
    param([string]$Version, [string]$Work)
    if ($Version -eq 'unknown') { return $null }
    try {
        $zip = Join-Path $Work 'old.zip'
        Get-Archive "$ArchiveBase/tags/v$Version.zip" $zip
        $dir = Join-Path $Work 'old'
        Expand-Archive -Path $zip -DestinationPath $dir -Force
        $tree = Get-ChildItem -Path $dir -Directory | Where-Object { $_.Name -like 'Spec-Driven-Roadmap-*' } | Select-Object -First 1
        if ($tree) { return $tree.FullName }
    } catch { }
    return $null
}
function Get-LocalChanges {
    param([string]$Installed, [string]$Release)
    $base = (Resolve-Path -LiteralPath $Installed).Path
    foreach ($f in (Get-ChildItem -LiteralPath $base -Recurse -File -Force | Sort-Object FullName)) {  # -Force: a dotfile the project added is a local change too
        $rel = $f.FullName.Substring($base.Length).TrimStart('\', '/')
        if ($rel -match '\.pyc$' -or $rel -match '__pycache__' -or $rel -eq '.skill-meta.json') { continue }
        $orig = Join-Path $Release $rel
        if (-not (Test-Path -LiteralPath $orig)) { "added    $($rel -replace '\\', '/')" }
        elseif ((Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $orig -Algorithm SHA256).Hash) { "modified $($rel -replace '\\', '/')" }
    }
}

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("sdr-" + [Guid]::NewGuid().ToString('N'))
# Declared out here so `finally` can clean it too, and PID-suffixed to match
# install.sh and survive two concurrent runs. $Stage is a sibling of $Dest -
# i.e. INSIDE .claude\skills\ - so a leftover is not clutter: it is a second
# directory holding a SKILL.md with the same skill name, which registers twice.
$Stage = "$Dest.tmp.$PID"
New-Item -ItemType Directory -Path $Tmp -Force | Out-Null

try {
    Write-Status "Downloading $SkillName ($Branch)..."
    $zipUrl = "$ArchiveBase/heads/$Branch.zip"
    $zip    = Join-Path $Tmp 'skill.zip'
    try {
        Get-Archive $zipUrl $zip
    } catch {
        Write-Fail "Failed to download $zipUrl"
        Write-Host 'If the repository is private, GitHub returns 404 to unauthenticated requests.' -ForegroundColor Yellow
        Write-Host 'This installer only downloads - it has no local-source mode, so re-running it' -ForegroundColor Yellow
        Write-Host 'from a checkout fails the same way. From a clone, install by hand:' -ForegroundColor Yellow
        Write-Host "  New-Item -ItemType Directory -Path '$Dest\scripts' -Force" -ForegroundColor Yellow
        Write-Host "  Copy-Item SKILL.md,references '$Dest' -Recurse -Force" -ForegroundColor Yellow
        Write-Host ("  Copy-Item -Path " + (($RequiredScripts | ForEach-Object { "scripts\$_" }) -join ', ') + " -Destination '$Dest\scripts' -Force") -ForegroundColor Yellow
        exit 1
    }

    Expand-Archive -Path $zip -DestinationPath $Tmp -Force
    $src = Get-ChildItem -Path $Tmp -Directory | Where-Object { $_.Name -like 'Spec-Driven-Roadmap-*' } | Select-Object -First 1

    # Validate the payload BEFORE touching the destination. A partial archive
    # that yielded SKILL.md but no references/ would install a skill whose
    # every procedure link is dead - silent capability loss.
    if (-not $src)                                              { Write-Fail 'Archive layout unexpected - aborting.'; exit 1 }
    if (-not (Test-Path (Join-Path $src.FullName 'SKILL.md')))  { Write-Fail 'Archive has no SKILL.md - aborting.'; exit 1 }
    $refDir = Join-Path $src.FullName 'references'
    if (-not (Test-Path $refDir))                               { Write-Fail 'Archive has no references/ - aborting.'; exit 1 }
    foreach ($ref in $RequiredRefs) {
        if (-not (Test-Path (Join-Path $refDir $ref))) { Write-Fail "Archive is missing references/$ref - aborting."; exit 1 }
    }
    $scrDir = Join-Path $src.FullName 'scripts'
    foreach ($scr in $RequiredScripts) {
        if (-not (Test-Path (Join-Path $scrDir $scr))) { Write-Fail "Archive is missing scripts/$scr - aborting."; exit 1 }
    }

    # Announce which version is going in, and which one it displaces. This is
    # the only moment in the flow where the downloaded version and the one
    # already on disk are both available - say it out loud, or a user sitting
    # on an old install has no way to tell.
    $newVersion = Get-SkillVersion (Join-Path $src.FullName 'SKILL.md')
    $oldVersion = 'none'
    if (Test-Path -LiteralPath $Dest) {
        $oldVersion = Get-SkillVersion (Join-Path $Dest 'SKILL.md')
        if ($Check) {
            if ($oldVersion -eq $newVersion) { Write-Status "installed $oldVersion is the version available" }
            else { Write-Status "installed $oldVersion, available $newVersion" }
        } elseif ($oldVersion -eq $newVersion) {
            Write-Status "already at $newVersion - reinstalling"
        } else {
            Write-Status "installing $newVersion (replacing $oldVersion)"
        }
    } elseif ($Check) {
        Write-Status "nothing installed here; available $newVersion"
    } else {
        Write-Status "installing $newVersion"
    }

    $changes = @()
    if (Test-Path -LiteralPath $Dest) {
        $relTree = Get-ReleaseTree $oldVersion $Tmp
        if ($relTree) {
            $changes = @(Get-LocalChanges $Dest $relTree)
            if ($changes.Count -gt 0) {
                Write-Host "! $($changes.Count) file(s) of the installed copy differ from the released v$oldVersion, and an install REPLACES them:" -ForegroundColor Yellow
                $changes | ForEach-Object { Write-Host "    $_" }
                if ($Diff) {
                    foreach ($c in ($changes | Where-Object { $_ -like 'modified *' })) {
                        $rel = ($c -replace '^modified\s+', '')
                        Write-Host ''; Write-Host "--- $rel (release v$oldVersion -> installed copy)"
                        # @(...): an empty file is $null to Get-Content, and Compare-Object refuses $null. -CaseSensitive: a case-only edit is a change.
                        $a = @(Get-Content -LiteralPath (Join-Path $relTree $rel)); $b = @(Get-Content -LiteralPath (Join-Path $Dest $rel))
                        $d = @(Compare-Object $a $b -CaseSensitive)
                        if ($d.Count -eq 0) { Write-Host '  (no line differs: the file differs in line endings, line order, a final newline or an encoding mark)' }
                        else { $d | Select-Object -First 80 | ForEach-Object { ($(if ($_.SideIndicator -eq '=>') { '+ ' } else { '- ' }) + $_.InputObject) } | ForEach-Object { Write-Host $_ } }
                    }
                }
                Write-Host '  If a setting of the project depended on a local patch, it stops working after this install.'
            } else {
                Write-Status "the installed copy is the released v$oldVersion, unchanged - nothing local to lose"
            }
        } else {
            Write-Status "could not check the installed copy for local changes (no archive of v$oldVersion to compare with)"
        }
    }
    if ($Check) {
        Write-Host "--check: nothing was changed. installed: $oldVersion  available: $newVersion"
        return
    }
    # A local change is the one thing in an install that cannot be undone from the archive: ask again, with the list
    # in front of the person, unless they already said -Force.
    if ($changes.Count -gt 0 -and -not $Force) {
        $interactive2 = $Host.UI.RawUI -and -not [Console]::IsInputRedirected
        if ($interactive2) {
            $reply2 = Read-Host 'Replace them anyway? (y/N)'
            if ($reply2 -notmatch '^[Yy]') { Write-Host 'Installation cancelled.'; return }
        } else {
            Write-Fail 'Non-interactive session and the installed copy has local changes. Re-run with -Force to replace them.'
            exit 1
        }
    }

    # Stage into a sibling, then swap. The destination is never left half-written.
    Write-Status "Installing to $Dest..."
    if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
    New-Item -ItemType Directory -Path $Stage -Force | Out-Null
    Copy-Item (Join-Path $src.FullName 'SKILL.md') $Stage
    Copy-Item $refDir $Stage -Recurse
    $stageScripts = Join-Path $Stage 'scripts'
    New-Item -ItemType Directory -Path $stageScripts -Force | Out-Null
    foreach ($scr in $RequiredScripts) { Copy-Item (Join-Path $scrDir $scr) $stageScripts }

    $parent = Split-Path $Dest -Parent
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    if (Test-Path -LiteralPath $Dest) { Remove-Item -LiteralPath $Dest -Recurse -Force }
    Move-Item -LiteralPath $Stage -Destination $Dest

    if ($newVersion -eq 'unknown') {
        Write-Ok "$SkillName (version unknown) installed at $Dest"
    } else {
        Write-Ok "$SkillName v$newVersion installed at $Dest"
    }
    Write-Host ''
    Write-Host 'Installed:'
    Write-Host '  SKILL.md'
    Get-ChildItem -LiteralPath (Join-Path $Dest 'references') -Filter *.md |
        Sort-Object Name | ForEach-Object { Write-Host "  references/$($_.Name)" }
    Get-ChildItem -LiteralPath (Join-Path $Dest 'scripts') |
        Sort-Object Name | ForEach-Object { Write-Host "  scripts/$($_.Name)" }
    Write-Host @'

Next steps:
  1. Restart Claude Code (or run /skills) to pick it up.
  2. Install a downstream spec-driven skill if you have not yet - the roadmap
     hands off to it. Default assumption is tlc-spec-lean (tlc-spec-driven is also supported),
     with tlc-discover for the no-document interview and its companion:
       npx @tech-leads-club/agent-skills install --skill tlc-spec-lean -a claude-code
       npx @tech-leads-club/agent-skills install --skill tlc-discover -a claude-code
       npx @tech-leads-club/agent-skills install --skill not-your-babysitter -a claude-code
  3. Start it with any of:
       "generate a roadmap from docs/PRD.md"
       "plan product"            (interview - when you have no document yet)
       "I don't know what to build yet"
  4. Later, to see whether a newer version is out, compare the `version:` line
     in your installed SKILL.md with the one in the repo - the README's
     "Which version do I have?" section has the one-liner that does it.
'@
}
finally {
    if (Test-Path -LiteralPath $Tmp)   { Remove-Item -LiteralPath $Tmp   -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue }
}
