<#
.SYNOPSIS
    Replace a working copy's contents with the delivery archive's, so git
    records the DELETIONS as well as the additions.

.DESCRIPTION
    Unzipping the delivery archive over an existing folder adds and
    overwrites files. It never removes one. A repository that has been
    restructured - files moved to new folders, old modules deleted -
    therefore ends up holding BOTH layouts at once after an unzip, and
    `git add -A` sees nothing to delete because nothing was deleted.

    That is not hypothetical. It put 1,055 files on the remote where the
    project has 593: an entire pre-restructure copy of services/ and
    tests/ sitting beside the current one, 169 committed .pyc files, and
    - the one that actually broke the build - an artifacts/
    feature_columns.json from before the model was retrained, listing 52
    columns for a classifier fitted on 184.

    This script does the part unzipping cannot: it empties the working
    copy (keeping .git, so history and the remote survive), lays the
    archive's contents down in its place, and restores the large files
    the archive omits for transport. Afterwards `git status` shows the
    stale files as deletions, which is what makes the commit correct.

.PARAMETER ArchiveRoot
    The extracted archive's inner folder - the one directly containing
    run.py and requirements.txt.

.EXAMPLE
    cd C:\path\to\Digital-Wellness-AI
    .\scripts\replace-tree.ps1 -ArchiveRoot C:\Downloads\Digital-Wellness-AI

.NOTES
    Everything removed is copied to a timestamped backup folder beside
    the repository first. Nothing is pushed; you review and push.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- checks

if (-not (Test-Path '.git')) {
    throw "Run this from the root of the git repository (no .git here: $PWD)."
}
if (-not (Test-Path (Join-Path $ArchiveRoot 'run.py'))) {
    throw "ArchiveRoot does not look like the project: no run.py in $ArchiveRoot"
}

$repo = (Get-Location).Path
$archive = (Resolve-Path $ArchiveRoot).Path
if ($archive -eq $repo) {
    throw "ArchiveRoot is the repository itself. Extract the zip somewhere else first."
}

Write-Host ""
Write-Host "  repository : $repo"
Write-Host "  archive    : $archive"
Write-Host ""

# ------------------------------------------------------- keep a way back

$backup = Join-Path (Split-Path $repo -Parent) ("Digital-Wellness-AI-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
Write-Host "  Backing the current contents up to:"
Write-Host "    $backup"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Get-ChildItem -Force | Where-Object { $_.Name -ne '.git' } |
    Copy-Item -Destination $backup -Recurse -Force
Write-Host "  done."
Write-Host ""

# ---------------------------------------------- the part unzip cannot do

Write-Host "  Emptying the working copy (.git is kept)..."
Get-ChildItem -Force | Where-Object { $_.Name -ne '.git' } |
    Remove-Item -Recurse -Force

# Enumerated with -Force rather than copied with a `dir\*` wildcard: the
# wildcard form skips items carrying the hidden attribute, and .github/
# is where the CI workflows live. Losing it silently would mean the very
# checks this replacement exists to fix never run again.
Write-Host "  Laying down the archive..."
Get-ChildItem -Path $archive -Force |
    Copy-Item -Destination $repo -Recurse -Force
$workflow = Join-Path $repo '.github\workflows\ci.yml'
if (Test-Path $workflow) {
    Write-Host "    .github\workflows\ci.yml present"
} else {
    Write-Warning ".github\workflows\ci.yml did not arrive - CI would stop running. Stop and check the archive."
}
Write-Host ""

# ------------------------------------------------ restore what it omits
#
# These are tracked in git and left out of the archive only because they
# do not fit in one upload. Without them `git add -A` stages their
# deletion, which would drop the training data and the archived models
# from the repository.

Write-Host "  Restoring the files the archive omits for size..."
foreach ($relative in @(
    'data\train.csv',
    'data\test.csv',
    'data\archive_pre_user_split_fix',
    'artifacts\archive_pre_user_split_fix',
    'artifacts\archive_pre_feature_consistency_fix'
)) {
    $from = Join-Path $backup $relative
    if (-not (Test-Path $from)) {
        Write-Host "    MISSING   $relative  (was not in the old copy either)"
        continue
    }

    $to = Join-Path $repo $relative
    if ((Get-Item $from) -is [System.IO.DirectoryInfo]) {
        # Merge CONTENTS into $to - never `Copy-Item $from $to -Recurse`
        # for a directory. That form nests the whole source folder one
        # level deeper whenever $to already exists as a directory, which
        # is exactly the case here: artifacts/archive_*/'s *.json files
        # are not omitted from the archive (only the *.pkl are), so the
        # folder already exists with content in it before this loop runs.
        # The result was e.g.
        #   artifacts\archive_pre_user_split_fix\archive_pre_user_split_fix\*.pkl
        # - the restored files landing one directory too deep, silently.
        New-Item -ItemType Directory -Path $to -Force | Out-Null
        Copy-Item -Path (Join-Path $from '*') -Destination $to -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path (Split-Path $to -Parent) -Force | Out-Null
        Copy-Item -Path $from -Destination $to -Force
    }
    Write-Host "    restored  $relative"
}

# storage/ holds real accounts and is gitignored - carried across so the
# app keeps working locally, never committed.
$storage = Join-Path $backup 'storage'
if (Test-Path $storage) {
    Copy-Item (Join-Path $storage '*') (Join-Path $repo 'storage') -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "    restored  storage\  (local only - gitignored)"
}
$envFile = Join-Path $backup '.env'
if (Test-Path $envFile) {
    Copy-Item $envFile (Join-Path $repo '.env') -Force
    Write-Host "    restored  .env      (local only - gitignored)"
}

Write-Host ""
Write-Host "  Regenerating data\*_augmented.csv (tracked, ~1 min)..."
$python = if (Test-Path '.venv\Scripts\python.exe') { '.venv\Scripts\python.exe' } else { 'python' }
& $python -m models.augment_future_score
if ($LASTEXITCODE -ne 0) {
    Write-Warning "augment_future_score failed. Run it yourself before committing, or the augmented CSVs will be staged as deletions."
}

# ------------------------------------------------------------- verify

Write-Host ""
Write-Host "  --------------------------------------------------"
$columns = (& $python -c "import json;print(len(json.load(open('artifacts/feature_columns.json'))))")
if ($columns -eq '184') {
    Write-Host "  feature_columns.json : $columns columns  OK"
} else {
    Write-Warning "feature_columns.json has $columns columns, expected 184. CI will fail. Stop and check the archive."
}

git add -A
$deletions = (git status --short | Select-String '^D').Count
Write-Host "  staged deletions     : $deletions"
if ($deletions -lt 100) {
    Write-Warning "Expected several hundred deletions. If this is near zero the stale files were not there to begin with, which is fine - or .git was not carried across, which is not."
}
Write-Host "  --------------------------------------------------"
Write-Host ""
Write-Host "  Review, then:"
Write-Host "      git commit -m ""Replace the tree with the verified build"""
Write-Host "      git push"
Write-Host ""
Write-Host "  Backup kept at $backup - delete it once CI is green."
Write-Host ""
