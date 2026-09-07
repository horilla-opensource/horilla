param(
  [switch]$PushOrigin,
  [switch]$ForceWithLease
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 1. Sanity checks
$gitOK = $false
try {
  $null = git rev-parse --is-inside-work-tree 2>&1
  $gitOK = ($LASTEXITCODE -eq 0)
} catch {}
if (-not $gitOK) {
  Write-Host "[FATAL] $PSScriptRoot is not a git repo." -ForegroundColor Red
  exit 1
}

$curBranch = git rev-parse --abbrev-ref HEAD
if ($curBranch -ne "my-customizations") {
  Write-Host "[STOP] Not on my-customizations. Currently on '$curBranch'." -ForegroundColor Red
  Write-Host "Switch first:  git checkout my-customizations" -ForegroundColor Yellow
  exit 1
}

if (-not (git remote get-url upstream 2>$null)) {
  Write-Host "[FATAL] 'upstream' remote not configured. Expected: https://github.com/horilla/horilla-hr.git" -ForegroundColor Red
  exit 1
}

# 2. Activate venv (also used to sanity-check dir)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "[WARN] .venv missing — skipping Django check, git-only sync." -ForegroundColor Yellow
  $haveVenv = $false
} else {
  $haveVenv = $true
  & .\.venv\Scripts\Activate.ps1
  $env:PYTHONIOENCODING = "UTF-8"
}

Write-Host "[1/7] Fetching upstream 2.0..." -ForegroundColor Cyan
git fetch upstream

# 3. Diff new upstream commits
$new = git log --oneline 2.0..upstream/2.0
if (-not $new) {
  Write-Host "[OK] Already up-to-date with upstream/2.0. Nothing to sync." -ForegroundColor Green
  exit 0
}
Write-Host "New upstream commits:`n$new`n" -ForegroundColor Magenta

# 4. Update clean base branch 2.0 (fast-forward only, never merge commit on base)
Write-Host "[2/7] Fast-forward local 2.0 to upstream/2.0..." -ForegroundColor Cyan
git checkout 2.0
git merge --ff-only upstream/2.0
if ($LASTEXITCODE -ne 0) {
  Write-Host "[STOP] 2.0 merge --ff-only failed. 2.0 likely dirty / manually committed to." -ForegroundColor Red
  Write-Host "FIX: git checkout 2.0 ; git reset --hard upstream/2.0  (DESTROYS local commits on 2.0 — use only if you never committed to 2.0)" -ForegroundColor Yellow
  exit 1
}

# 5. Push updated 2.0 to your fork
Write-Host "[3/7] Push 2.0 to origin (YOUR fork)..." -ForegroundColor Cyan
git push origin 2.0
if ($LASTEXITCODE -ne 0) { exit 1 }

# 6. Back to my-customizations → cheap backup branch → rebase
Write-Host "[4/7] Switching to my-customizations..." -ForegroundColor Cyan
git checkout my-customizations
$stashNeeded = $false
$dirty = git status --porcelain
if ($dirty) {
  Write-Host "[WARN] Working tree dirty — stashing before rebase." -ForegroundColor Yellow
  git stash push -u -m "sync-upstream auto-stash $(Get-Date -Format o)"
  $stashNeeded = $true
}

$backup = "my-customizations-BACKUP-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Write-Host "[5/7] Creating safety backup branch '$backup'..." -ForegroundColor Cyan
git branch $backup
Write-Host "   To revert catastrophic rebase:  git reset --hard $backup" -ForegroundColor DarkGray

Write-Host "[6/7] Rebasing my-customizations onto 2.0... (resolve conflicts, `git rebase --continue` / `git rebase --abort`)" -ForegroundColor Cyan
git rebase 2.0

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "[REBASE CONFLICT] Resolve the conflicts above." -ForegroundColor Red
  Write-Host "   After editing + git add <files> → run:  git rebase --continue" -ForegroundColor Yellow
  Write-Host "   If overwhelmed and want to undo → run:   git rebase --abort ; git reset --hard $backup" -ForegroundColor Yellow
  exit 1
}

if ($stashNeeded) {
  Write-Host "[6b/7] Reapplying stashed changes..." -ForegroundColor Cyan
  git stash pop
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Stash pop conflicts. Fix manually, then git add + git rebase --continue if inside rebase." -ForegroundColor Yellow
  }
}

# 7. Post-rebase: Django sanity check (migration/model integrity)
if ($haveVenv) {
  Write-Host "[7/7] Post-sync Django check..." -ForegroundColor Cyan
  & $py manage.py check
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Django check FAILED after rebase. Upstream likely changed imports/models. Inspect diffs." -ForegroundColor Yellow
  } else {
    Write-Host "   Post-rebase Django check OK." -ForegroundColor Green
  }
}

# Push
if ($PushOrigin) {
  if ($ForceWithLease) {
    Write-Host "Pushing rebased my-customizations with --force-with-lease..." -ForegroundColor Green
    git push origin my-customizations --force-with-lease
  } else {
    Write-Host "[HINT] After rebase, history diverged. To push safely, re-run with -PushOrigin -ForceWithLease." -ForegroundColor Yellow
    Write-Host "Pushing non-destructive attempt (will fail if diverged):" -ForegroundColor DarkGray
    git push origin my-customizations
  }
} else {
  Write-Host "[DONE] Local sync complete. Push to fork manually or re-run with: .\sync-upstream.ps1 -PushOrigin -ForceWithLease" -ForegroundColor Green
}
Write-Host "[INFO] Backup branch kept: $backup   (delete later with: git branch -D $backup)" -ForegroundColor DarkGray
