param(
    [switch]$NoPush,
    [switch]$SkipSync,
    [string]$CommitMessage = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $projectRoot "venv\Scripts\python.exe"
$syncScript = Join-Path $projectRoot "scripts\sync_sources.py"
$validationScript = Join-Path $projectRoot "scripts\validate_synced_sources.py"

$dataFiles = @(
    "data/raw/github/profile.json",
    "data/raw/github/repositories.json",
    "data/raw/github/events.json",
    "data/raw/leetcode/profile.json",
    "data/raw/leetcode/submit_stats.json",
    "data/raw/google/data.json",
    "data/raw/cloudinary/documents.json",
    "data/raw/sync_report.json"
)

$meaningfulDataFiles = $dataFiles | Where-Object { $_ -ne "data/raw/sync_report.json" }
$automationFiles = @(
    "scripts/sync_latest_and_push.ps1",
    "scripts/validate_synced_sources.py",
    "sync_latest.cmd"
)

function Write-Step([string]$message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Assert-LastCommand([string]$message) {
    if ($LASTEXITCODE -ne 0) {
        throw $message
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Virtual environment Python was not found: $pythonPath"
}

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".env"))) {
    throw "The backend .env file is missing from: $projectRoot"
}

Push-Location $projectRoot

try {
    $env:PYTHONUTF8 = "1"

    Write-Step "Checking repository safety"
    $preexistingStagedFiles = @(& git diff --cached --name-only)
    Assert-LastCommand "Git could not inspect the staging area."

    if ($preexistingStagedFiles.Count -gt 0) {
        throw "The staging area already contains changes. Commit or unstage them before running this script: $($preexistingStagedFiles -join ', ')"
    }

    if (-not $SkipSync) {
        $preexistingDataChanges = @(& git status --porcelain -- @dataFiles)
        Assert-LastCommand "Git could not inspect source-data files."

        if ($preexistingDataChanges.Count -gt 0) {
            throw "Source-data files already contain local changes. Review them before syncing, or use -SkipSync only when continuing a previously interrupted run: $($preexistingDataChanges -join ', ')"
        }
    }

    if ($SkipSync) {
        Write-Step "Continuing with already-refreshed source data"
    } else {
        Write-Step "Synchronizing GitHub, LeetCode, Google, and Cloudinary"
        & $pythonPath $syncScript
        Assert-LastCommand "Source synchronization failed. Nothing was committed or pushed."
    }

    Write-Step "Validating synchronized data and backend health"
    & $pythonPath $validationScript
    Assert-LastCommand "Synchronized data or backend health validation failed."

    Write-Step "Checking for meaningful source-data changes"
    & git diff --quiet -- @meaningfulDataFiles
    $hasDataChanges = $LASTEXITCODE -ne 0

    $automationStatus = (& git status --porcelain -- @automationFiles) -join ""
    $hasAutomationChanges = -not [string]::IsNullOrWhiteSpace($automationStatus)

    if (-not $hasDataChanges -and -not $hasAutomationChanges) {
        & git restore -- "data/raw/sync_report.json"
        Write-Host "No new source data was found. Repository is already current." -ForegroundColor Green
        return
    }

    Write-Step "Staging approved synchronization files"
    & git add -- @dataFiles @automationFiles
    Assert-LastCommand "Git could not stage the synchronization files."

    $stagedFiles = @(& git diff --cached --name-only)
    $approvedFiles = @($dataFiles + $automationFiles)
    $unexpectedFiles = @($stagedFiles | Where-Object { $_ -notin $approvedFiles })

    if ($unexpectedFiles.Count -gt 0) {
        & git restore --staged -- @unexpectedFiles
        throw "Unexpected staged files were removed: $($unexpectedFiles -join ', ')"
    }

    if (-not $CommitMessage) {
        $utcStamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HHmm 'UTC'")
        $CommitMessage = "Sync portfolio assistant data ($utcStamp)"
    }

    Write-Step "Creating Git commit"
    & git commit -m $CommitMessage
    Assert-LastCommand "Git commit failed."

    if ($NoPush) {
        Write-Host "Commit created locally. Push was skipped because -NoPush was supplied." -ForegroundColor Yellow
        return
    }

    $branch = (& git branch --show-current).Trim()
    if (-not $branch) {
        throw "Cannot push from a detached HEAD."
    }

    Write-Step "Pushing $branch to origin"
    & git push origin $branch
    Assert-LastCommand "Git push failed. The commit remains available locally."

    Write-Host ""
    Write-Host "Synchronization completed and pushed successfully." -ForegroundColor Green
}
finally {
    Pop-Location
}
