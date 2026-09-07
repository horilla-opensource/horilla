param(
  [int]$Port = 8000,
  [switch]$SkipMigrationsCheck
)

$ErrorActionPreference = "Stop"

# -- 1. Ensure we're in the script directory (project root) --
Set-Location -Path $PSScriptRoot

# -- 2. Sanity: venv must exist --
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  Write-Host "[FATAL] .venv\Scripts\Activate.ps1 not found in $PSScriptRoot" -ForegroundColor Red
  Write-Host "Create venv first:  py -3.12 -m venv .venv" -ForegroundColor Yellow
  exit 1
}

# -- 3. Activate venv --
Write-Host "[1/5] Activating project .venv..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1
# Confirm activation worked (else fallback to explicit python.exe path for remainder)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "[FATAL] $py missing. Recreate venv." -ForegroundColor Red
  exit 1
}

# -- 4. UTF-8 output encoding (prevents UnicodeEncodeError on Windows with emoji ⚠️ in Horilla warnings) --
Write-Host "[2/5] Setting PYTHONIOENCODING=UTF-8..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = "UTF-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# -- 5. Django system check --
Write-Host "[3/5] Running: python manage.py check" -ForegroundColor Cyan
& $py manage.py check
if ($LASTEXITCODE -ne 0) {
  Write-Host "[STOP] Django system check FAILED. Fix errors before starting server." -ForegroundColor Red
  exit $LASTEXITCODE
}

# -- 6. Migrations check (skip via -SkipMigrationsCheck) --
if (-not $SkipMigrationsCheck) {
  Write-Host "[4/5] Checking unapplied migrations..." -ForegroundColor Cyan
  $unapplied = & $py manage.py showmigrations --plan 2>&1 | Select-String "\[ \]"
  if ($unapplied) {
    Write-Host "[WARN] Migrations pending. Running: python manage.py migrate ..." -ForegroundColor Yellow
    & $py manage.py migrate
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[STOP] migrate FAILED. Resolve before runserver." -ForegroundColor Red
      exit $LASTEXITCODE
    }
  } else {
    Write-Host "   All migrations applied." -ForegroundColor Green
  }
} else {
  Write-Host "[4/5] Skipped migrations check (-SkipMigrationsCheck)." -ForegroundColor DarkGray
}

# -- 7. Launch Django dev server --
Write-Host "[5/5] Starting Django dev server on http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host "   [Ctrl+C] to stop." -ForegroundColor DarkGray
& $py manage.py runserver "127.0.0.1:$Port"
