param(
  [switch]$NoConfirm
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "[FATAL] .venv not found at $py. Activate / create venv first." -ForegroundColor Red
  exit 1
}

& .\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "UTF-8"

# DB auth password from .env (same env settings.load_db password for HTTP modal)
$initPw = (& $py -c "import os; from pathlib import Path; from dotenv import load_dotenv; load_dotenv(); print(os.environ.get('DB_INIT_PASSWORD',''))")
if ([string]::IsNullOrWhiteSpace($initPw)) {
  Write-Host "[FATAL] DB_INIT_PASSWORD not set in .env. Edit .env line 13+ with: DB_INIT_PASSWORD=<strong random pw>" -ForegroundColor Red
  exit 1
}

Write-Host "[1/2] Loading Horilla demo data via manage.py load_demo_data..." -ForegroundColor Cyan
Write-Host "      DB_INIT_PASSWORD loaded from .env (length: $($initPw.Length))" -ForegroundColor DarkGray

& $py manage.py load_demo_data
if ($LASTEXITCODE -ne 0) {
  Write-Host "[STOP] load_demo_data command exited non-zero." -ForegroundColor Red
  exit $LASTEXITCODE
}

Write-Host "[2/2] Verifying demo inventory..." -ForegroundColor Cyan
& $py manage.py demo_data_inventory

Write-Host "[DONE] Demo data loaded. Next: .\start-dev.ps1 → login to dashboard." -ForegroundColor Green
