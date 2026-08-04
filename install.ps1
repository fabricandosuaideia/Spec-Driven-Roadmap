<#
.SYNOPSIS
    Installs the spec-driven-roadmap Claude Code skill on Windows.

.DESCRIPTION
    Downloads SKILL.md + references/ and installs them into
    .claude\skills\spec-driven-roadmap\ in the current directory, or into
    $HOME\.claude\skills\spec-driven-roadmap\ with -Global.

    Uses only built-in PowerShell cmdlets - no curl, tar, bash, WSL or Git Bash
    required. Requires PowerShell 5.1 or later (ships with Windows 10+).

.PARAMETER Global
    Install to $HOME\.claude\skills\ instead of the current project.

.PARAMETER Force
    Overwrite an existing install without prompting.

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
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$Repo      = 'fabricandosuaideia/Spec-Driven-Roadmap'
$Branch    = if ($env:SDR_BRANCH) { $env:SDR_BRANCH } else { 'main' }
$SkillName = 'spec-driven-roadmap'

# The skill is these files and nothing else. Used to validate the download
# before anything on disk is touched.
$RequiredRefs = @(
    'scope-phase.md',
    'index-phase.md',
    'decompose-phase.md',
    'handoff-seed.md'
)

function Write-Status  { param($m) Write-Host "-> $m" }
function Write-Ok      { param($m) Write-Host "OK $m" -ForegroundColor Green }
function Write-Fail    { param($m) Write-Host "ERROR $m" -ForegroundColor Red }

if ($Global) {
    $Dest = Join-Path $HOME ".claude\skills\$SkillName"
} else {
    $Dest = Join-Path (Get-Location).Path ".claude\skills\$SkillName"
}

# --- Overwrite guard -------------------------------------------------------
# `irm ... | iex` cannot pass parameters, so an interactive prompt is the only
# way a piped user can confirm. When the host is non-interactive we refuse
# loudly rather than guessing.
if ((Test-Path $Dest) -and -not $Force) {
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

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("sdr-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Tmp -Force | Out-Null

try {
    Write-Status "Downloading $SkillName ($Branch)..."
    $zipUrl = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"
    $zip    = Join-Path $Tmp 'skill.zip'
    try {
        # TLS 1.2 for older Windows PowerShell defaults.
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $zipUrl -OutFile $zip -UseBasicParsing
    } catch {
        Write-Fail "Failed to download $zipUrl"
        Write-Host 'If the repository is private, GitHub returns 404 to unauthenticated requests.' -ForegroundColor Yellow
        Write-Host 'Clone it and run .\install.ps1 from the checkout instead.' -ForegroundColor Yellow
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

    # Stage into a sibling, then swap. The destination is never left half-written.
    Write-Status "Installing to $Dest..."
    $stage = "$Dest.tmp"
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    Copy-Item (Join-Path $src.FullName 'SKILL.md') $stage
    Copy-Item $refDir $stage -Recurse

    $parent = Split-Path $Dest -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
    Move-Item $stage $Dest

    Write-Ok "$SkillName installed at $Dest"
    Write-Host ''
    Write-Host 'Installed:'
    Write-Host '  SKILL.md'
    Get-ChildItem (Join-Path $Dest 'references') -Filter *.md |
        Sort-Object Name | ForEach-Object { Write-Host "  references/$($_.Name)" }
    Write-Host @'

Next steps:
  1. Restart Claude Code (or run /skills) to pick it up.
  2. Install a downstream spec-driven skill if you have not yet - the roadmap
     hands off to it. Default assumption is tlc-spec-driven:
       npx @tech-leads-club/agent-skills install --skill tlc-spec-driven -a claude-code
  3. Start it with any of:
       "generate a roadmap from docs/PRD.md"
       "plan product"            (interview - when you have no document yet)
       "I don't know what to build yet"
'@
}
finally {
    if (Test-Path $Tmp) { Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
