param(
  [int]$Port = 8000,
  [switch]$SkipMigrationsCheck
)

$ErrorActionPreference = "Continue"   # Horilla writes warnings to stderr; let through. Explicit checks below.
Set-StrictMode -Version Latest

# -- 0. Local helper: run python, return exit code (warnings -> printed, no abort) --
function Invoke-Python {
  param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$ArgsList,
    [Parameter(Position=1)]
    [AllowNull()]
    $OutputLines = $null
  )
  $id = [guid]::NewGuid().ToString("N")
  $tmpOut = Join-Path $env:TEMP "py-out-$id.log"
  $tmpExit = Join-Path $env:TEMP "py-exit-$id.txt"
  $pythonExe = $script:py
  $bat = Join-Path $env:TEMP "py-run-$id.bat"
  $batContent = @"
@echo off
setlocal
set PYTHONIOENCODING=UTF-8
set PYTHONUTF8=1
"$pythonExe" $ArgsList > "$tmpOut" 2>&1
echo %ERRORLEVEL% > "$tmpExit"
"@
  Set-Content -Path $bat -Value $batContent -Encoding ASCII -Force
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "cmd.exe"
  $psi.Arguments = "/c `"`"$bat`"`""
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()
  $p.WaitForExit()
  $codeText = Get-Content -Path $tmpExit -Raw -ErrorAction SilentlyContinue
  $rc = -999
  if ($null -ne $codeText) { [void][int]::TryParse($codeText.Trim(), [ref]$rc) }
  $lines = @()
  if (Test-Path $tmpOut) { $lines = @(Get-Content -Path $tmpOut) }
  if ($null -ne $OutputLines) { $OutputLines.Value = $lines }
  if ($lines.Count -gt 0) { Write-Output $lines }
  try { $p.Dispose() } catch {}
  Remove-Item -Path $tmpOut, $tmpExit, $bat -ErrorAction SilentlyContinue
  return $rc
}

# -- 1. Ensure we're in the script directory (project root) --
Set-Location -Path $PSScriptRoot

# -- 2. Sanity: venv must exist --
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  Write-Host "[FATAL] .venv\Scripts\Activate.ps1 not found in $PSScriptRoot" -ForegroundColor Red
  Write-Host "Create venv first:  py -3.12 -m venv .venv" -ForegroundColor Yellow
  exit 1
}

# -- 3. Activate venv + resolve python path --
Write-Host "[1/5] Activating project .venv..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1
$script:py = (Resolve-Path ".\.venv\Scripts\python.exe" -ErrorAction Stop).Path

# -- 4. UTF-8 (prevents UnicodeEncodeError on emoji warnings in Horilla) --
Write-Host "[2/5] Setting PYTHONIOENCODING=UTF-8..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = "UTF-8"
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# -- 5. Django system check --
Write-Host "[3/5] Running: python manage.py check" -ForegroundColor Cyan
$rc = Invoke-Python -ArgsList "manage.py check"
if ($rc -ne 0) {
  Write-Host "[STOP] Django system check FAILED (exit=$rc). Fix errors before starting server." -ForegroundColor Red
  exit $rc
}

# -- 6. Migrations check (skip via -SkipMigrationsCheck) --
if (-not $SkipMigrationsCheck) {
  Write-Host "[4/5] Checking unapplied migrations..." -ForegroundColor Cyan
  $showOut = $null
  $rc = Invoke-Python -ArgsList "manage.py showmigrations --plan" -OutputLines ([ref]$showOut)
  if ($rc -ne 0) {
    Write-Host "[STOP] showmigrations FAILED (exit=$rc)." -ForegroundColor Red
    exit $rc
  }
  $unapplied = @($showOut | Select-String "\[ \]")
  if ($unapplied.Count -gt 0) {
    Write-Host "[WARN] $($unapplied.Count) migrations pending. Running: python manage.py migrate ..." -ForegroundColor Yellow
    $rc = Invoke-Python "manage.py migrate"
    if ($rc -ne 0) {
      Write-Host "[STOP] migrate FAILED (exit=$rc). Resolve before runserver." -ForegroundColor Red
      exit $rc
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
& "$script:py" manage.py runserver "127.0.0.1:$Port"
