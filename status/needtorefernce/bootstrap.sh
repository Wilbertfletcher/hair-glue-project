# bootstrap.ps1 — Initialize AI session planning documents in a target repository.
#
# Usage:
#   .\bootstrap.ps1 -ProjectName <name> -DestinationPath <path> [-SubProject] [-Force]
#
# Modes:
#   Default (repo root)  — destination IS or contains the repo root;
#                          copilot-instructions.md goes at the repo root and
#                          is also copied to .github\ if that folder exists.
#   -SubProject          — destination is a subdirectory inside a larger repo;
#                          copilot-instructions.md is scoped inside the subdir;
#                          no .github\ copy is attempted.
#
# -Force: overwrite any files that already exist (default is to skip them).
#
# Examples:
#   # Fresh repo
#   .\bootstrap.ps1 -ProjectName "MyWebApp" -DestinationPath "C:\repos\my-web-app"
#
#   # Sub-directory of an existing repo
#   .\bootstrap.ps1 -ProjectName "DataPipeline" -DestinationPath "C:\repos\monorepo\packages\data-pipeline" -SubProject
#
#   # Re-run to add missing files (existing files untouched)
#   .\bootstrap.ps1 -ProjectName "MyWebApp" -DestinationPath "C:\repos\my-web-app"
#
#   # Re-run and overwrite everything
#   .\bootstrap.ps1 -ProjectName "MyWebApp" -DestinationPath "C:\repos\my-web-app" -Force

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [string] $ProjectName,

    [Parameter(Mandatory = $true)]
    [string] $DestinationPath,

    # Treat destination as a sub-directory within a larger repo.
    # Scopes copilot-instructions.md inside the subdir; skips .github\ copy.
    [switch] $SubProject,

    # Overwrite files that already exist. Default is to skip them.
    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$TemplateDir = Join-Path $ScriptDir "templates"
$SkippedFiles = @()
$WrittenFiles = @()

# -- Validate -----------------------------------------------------------------
if (-not (Test-Path $DestinationPath -PathType Container)) {
    Write-Error "Destination directory does not exist: $DestinationPath`nCreate it first or pass an existing repo path."
    exit 1
}
$DestinationPath = (Resolve-Path $DestinationPath).Path

if (-not (Test-Path $TemplateDir -PathType Container)) {
    Write-Error "Template directory not found: $TemplateDir`nRun this script from inside the ai-session-planning\ folder."
    exit 1
}

# -- Auto-detect: git root vs subdirectory ------------------------------------
function Find-GitRoot {
    param ([string] $StartPath)
    $current = $StartPath
    while ($current) {
        if (Test-Path (Join-Path $current ".git") -PathType Container) {
            return $current
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current) { return $null }   # filesystem root
        $current = $parent
    }
    return $null
}

$gitRoot  = Find-GitRoot $DestinationPath
$isSubDir = ($null -ne $gitRoot) -and ($gitRoot -ne $DestinationPath)

if ($isSubDir -and -not $SubProject) {
    Write-Host ""
    Write-Host "  NOTICE  '$DestinationPath' is inside a git repo rooted at:"
    Write-Host "            $gitRoot"
    Write-Host "          Add -SubProject to scope docs to this subdirectory,"
    Write-Host "          or omit it to treat the destination as the planning root anyway."
    Write-Host ""
}
if (-not $gitRoot) {
    Write-Host ""
    Write-Host "  NOTICE  No git repository found at or above the destination."
    Write-Host "          Proceeding anyway — run 'git init' in the repo root when ready."
    Write-Host ""
}

# -- Helpers ------------------------------------------------------------------
function Copy-AndSub {
    param (
        [string] $Source,
        [string] $Destination
    )
    $leaf = Split-Path -Leaf $Destination
    if ((Test-Path $Destination) -and -not $Force) {
        Write-Host "  SKIP  $leaf  (already exists; use -Force to overwrite)"
        $script:SkippedFiles += $Destination
        return
    }
    $dir = Split-Path -Parent $Destination
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $content = Get-Content -Path $Source -Raw -Encoding UTF8
    $content = $content -replace '\{\{ProjectName\}\}', $ProjectName
    $content = $content -replace '\{\{FeatureName\}\}', "$ProjectName Feature"
    $content = $content -replace '\{\{N\}\}', '0'
    Set-Content -Path $Destination -Value $content -Encoding UTF8 -NoNewline
    Write-Host "  OK    $leaf"
    $script:WrittenFiles += $Destination
}

# -- Print header -------------------------------------------------------------
Write-Host ""
$modeLabel = if ($SubProject) { "sub-project" } else { "repo root" }
Write-Host "Bootstrapping AI session planning for: $ProjectName  (mode: $modeLabel)"
Write-Host "Destination: $DestinationPath"
Write-Host ""

# -- Copy TODO/ templates -----------------------------------------------------
Write-Host "Creating TODO\ documents..."
Copy-AndSub (Join-Path $TemplateDir "TODO\STATUS.md")           (Join-Path $DestinationPath "TODO\STATUS.md")
Copy-AndSub (Join-Path $TemplateDir "TODO\TODO.md")             (Join-Path $DestinationPath "TODO\TODO.md")
Copy-AndSub (Join-Path $TemplateDir "TODO\DECISIONS.md")        (Join-Path $DestinationPath "TODO\DECISIONS.md")
Copy-AndSub (Join-Path $TemplateDir "TODO\GOTCHAS.md")          (Join-Path $DestinationPath "TODO\GOTCHAS.md")
Copy-AndSub (Join-Path $TemplateDir "TODO\ROADMAP-TEMPLATE.md") (Join-Path $DestinationPath "TODO\ROADMAP-M0.md")

# -- copilot-instructions.md --------------------------------------------------
Write-Host ""
Write-Host "Creating copilot-instructions.md..."
Copy-AndSub (Join-Path $TemplateDir "copilot-instructions.md")  (Join-Path $DestinationPath "copilot-instructions.md")

# -- .github\ copy (repo-root mode only) --------------------------------------
if (-not $SubProject) {
    # In repo-root mode: also write to .github\ for GitHub Copilot auto-injection.
    # Resolve root: prefer detected git root, otherwise the destination itself.
    $repoRoot = if ($null -ne $gitRoot) { $gitRoot } else { $DestinationPath }
    $githubDir = Join-Path $repoRoot ".github"
    Write-Host ""
    Write-Host "Checking for .github\ (GitHub Copilot auto-injection)..."
    if (Test-Path $githubDir -PathType Container) {
        Copy-AndSub (Join-Path $TemplateDir "copilot-instructions.md") (Join-Path $githubDir "copilot-instructions.md")
    } else {
        Write-Host "  --    No .github\ folder found at: $repoRoot"
        Write-Host "        To enable auto-injection, run:"
        Write-Host "          mkdir `"$githubDir`""
        Write-Host "          Copy-Item `"$DestinationPath\copilot-instructions.md`" `"$githubDir\copilot-instructions.md`""
    }
} else {
    Write-Host ""
    Write-Host "  --    Sub-project mode: skipping .github\ copy."
    Write-Host "        The repo-level .github\copilot-instructions.md (if any) is unchanged."
    Write-Host "        Attach '$DestinationPath\copilot-instructions.md' manually when opening a session."
}

# -- Summary ------------------------------------------------------------------
Write-Host ""
Write-Host "Bootstrap complete.  Written: $($WrittenFiles.Count)   Skipped: $($SkippedFiles.Count)"
if ($SkippedFiles.Count -gt 0) {
    Write-Host "  (Re-run with -Force to overwrite skipped files.)"
}
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit TODO\STATUS.md          -- fill in 'Where to Start Next Session'"
Write-Host "  2. Edit TODO\TODO.md            -- define your Milestone 0 tasks"
Write-Host "  3. Edit copilot-instructions.md -- fill in project architecture and key files"
Write-Host "  4. Edit TODO\ROADMAP-M0.md      -- fill in task details, phases, and acceptance criteria"
if (-not $SubProject) {
    Write-Host "  5. Commit: git add TODO copilot-instructions.md ; git commit -m 'chore: add AI session planning docs'"
} else {
    $rel = $DestinationPath.Replace($gitRoot + "\", "")
    Write-Host "  5. Commit: git add `"$rel/TODO`" `"$rel/copilot-instructions.md`" ; git commit -m 'chore: add AI session planning for $ProjectName'"
}
Write-Host ""
Write-Host "Framework guide: $ScriptDir\README.md"
