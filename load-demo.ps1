param(
  [switch]$NoConfirm
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Local helper: invoke python via cmd /c so stderr (warnings) doesn't throw in PS Stop
function Invoke-Python([string]$ArgsList) {
  $cmd = "`"$script:py`" $ArgsList"
  & cmd /c "$cmd 2>&1"
  return $LASTEXITCODE
}

$script:py = Resolve-Path ".\.venv\Scripts\python.exe" -ErrorAction Stop
if (-not (Test-Path $script:py)) {
  Write-Host "[FATAL] .venv\Scripts\python.exe not found. Create venv first." -ForegroundColor Red
  exit 1
}

& .\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "UTF-8"

# DB init pw from .env (for HTTP auth modal)
$pwOutput = & cmd /c "`"$script:py`" -c `"import os; from pathlib import Path; from dotenv import load_dotenv; load_dotenv(); print(os.environ.get('DB_INIT_PASSWORD',''))`" 2>&1 | Out-String
$initPw = $pwOutput.Trim()
if ([string]::IsNullOrWhiteSpace($initPw)) {
  Write-Host "[FATAL] DB_INIT_PASSWORD not set in .env. Edit .env line 13+ with: DB_INIT_PASSWORD=<strong random pw>" -ForegroundColor Red
  exit 1
}

Write-Host "[1/2] Loading Horilla demo data via manage.py load_demo_data..." -ForegroundColor Cyan
Write-Host "      DB_INIT_PASSWORD loaded from .env (length: $($initPw.Length))" -ForegroundColor DarkGray

$rc = Invoke-Python "manage.py load_demo_data"
if ($rc -ne 0) {
  Write-Host "[STOP] load_demo_data command exited non-zero ($rc)." -ForegroundColor Red
  exit $rc
}

Write-Host "[2/2] Verifying demo inventory..." -ForegroundColor Cyan
$rc = Invoke-Python "manage.py demo_data_inventory"
if ($rc -ne 0) {
  Write-Host "[WARN] demo_data_inventory exited $rc. Load may have partial data." -ForegroundColor Yellow
}

Write-Host "[DONE] Demo data loaded. Next: .\start-dev.ps1 → login to dashboard." -ForegroundColor Green
