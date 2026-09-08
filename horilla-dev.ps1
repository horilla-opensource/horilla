param(
  [Parameter(Mandatory=$false, Position=0)]
  [ValidateSet("check","migrate","runserver","showmigrations","createsuperuser","loaddemo","shell","inventory")]
  [string]$Action = "runserver",

  [int]$Port = 8000,

  [switch]$SkipMigrationsCheck
)

$ErrorActionPreference = "Stop"

# ---- Helper: get project root, locate venv python ----
Set-Location -Path $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Host "[FATAL] .venv\Scripts\python.exe not found at $PSScriptRoot" -ForegroundColor Red
  Write-Host "Create venv first:  py -3.12 -m venv .\.venv" -ForegroundColor Yellow
  Write-Host "Then:              pip install -r requirements.txt" -ForegroundColor Yellow
  exit 1
}

# ---- UTF-8 env for Horilla emoji/warning strings ----
$env:PYTHONIOENCODING = "UTF-8"
$env:PYTHONUTF8      = "1"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}

# ---- Private: run python.exe, capture BOTH stdout+stderr without PS injecting stderr ErrorRecords ----
# Strategy: use System.Diagnostics.Process with RedirectStandardOutput + RedirectStandardError.
# Async event handlers collect all text. Return exit code ONLY; callers can inspect $script:LastPyLines for text.
function Run-Python {
  param(
    [Parameter(Mandatory=$true)]
    [string]$ArgumentList,
    [switch]$PassThru,
    [switch]$NoExitCheck
  )
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $python
  $psi.Arguments = $ArgumentList
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow  = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  foreach ($k in @("PYTHONIOENCODING","PYTHONUTF8")) {
    $v = (Get-Item "env:$k" -ErrorAction SilentlyContinue).Value
    if ($psi.EnvironmentVariables.ContainsKey($k)) {
      $psi.EnvironmentVariables[$k] = $v
    } else {
      [void]$psi.EnvironmentVariables.Add($k, $v)
    }
  }
  $outSb = New-Object System.Text.StringBuilder
  $errSb = New-Object System.Text.StringBuilder
  $outEvt = { if (-not [string]::IsNullOrEmpty($EventArgs.Data)) { [void]$outSb.AppendLine($EventArgs.Data) } }.GetNewClosure()
  $errEvt = { if (-not [string]::IsNullOrEmpty($EventArgs.Data)) { [void]$errSb.AppendLine($EventArgs.Data) } }.GetNewClosure()
  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  $outSub = Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $outEvt
  $errSub = Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived  -Action $errEvt
  [void]$proc.Start()
  $proc.BeginOutputReadLine()
  $proc.BeginErrorReadLine()
  $proc.WaitForExit()
  Start-Sleep -Milliseconds 150
  Unregister-Event -SubscriptionId $outSub.Id -Force
  Unregister-Event -SubscriptionId $errSub.Id -Force
  Remove-Job -Id $outSub.Id -Force
  Remove-Job -Id $errSub.Id -Force
  $outText = $outSb.ToString().TrimEnd()
  $errText = $errSb.ToString().TrimEnd()
  $script:LastPyLines = @()
  if (-not [string]::IsNullOrEmpty($outText)) { $script:LastPyLines += ($outText -split "`r?`n") ; Write-Output $outText }
  if (-not [string]::IsNullOrEmpty($errText)) { $script:LastPyLines += ($errText -split "`r?`n") ; Write-Host $errText -ForegroundColor DarkGray }
  $script:LastPyExit = $proc.ExitCode
  try { $proc.Dispose() } catch {}
  if (-not $NoExitCheck -and $script:LastPyExit -ne 0) {
    Write-Host "[STOP] python $ArgumentList exited non-zero ($($script:LastPyExit))." -ForegroundColor Red
    exit $script:LastPyExit
  }
  if ($PassThru) { return $script:LastPyExit }
  return $null
}

# ---- Dispatcher ----
switch ($Action) {
  "check" {
    Write-Host "→ Django system check" -ForegroundColor Cyan
    Run-Python "manage.py check"
    Write-Host "OK" -ForegroundColor Green
  }
  "showmigrations" {
    Write-Host "→ Django showmigrations" -ForegroundColor Cyan
    Run-Python "manage.py showmigrations --plan"
    $pending = @($script:LastPyLines | Select-String "\[ \]")
    if ($pending.Count -gt 0) { Write-Host "$($pending.Count) migration(s) pending." -ForegroundColor Yellow }
    else { Write-Host "All migrations applied." -ForegroundColor Green }
  }
  "migrate" {
    Write-Host "→ Django migrate" -ForegroundColor Cyan
    Run-Python "manage.py migrate"
    Write-Host "Migrate complete." -ForegroundColor Green
  }
  "createsuperuser" {
    Write-Host "→ Django createsuperuser (interactive)" -ForegroundColor Cyan
    & $python manage.py createsuperuser   # attached (need stdin)
  }
  "loaddemo" {
    Write-Host "→ Load Horilla demo data (uses load_demo_data management command)" -ForegroundColor Cyan
    $pwText = (& $python -c "import os; from dotenv import load_dotenv; load_dotenv(); print((os.environ.get('DB_INIT_PASSWORD') or '').strip())") 2>&1 | Out-String
    $pw = $pwText.Trim()
    if ([string]::IsNullOrWhiteSpace($pw)) {
      Write-Host "[WARN] DB_INIT_PASSWORD not set in .env. Skipping HTTP modal validation check. Running command directly..." -ForegroundColor Yellow
    } else {
      Write-Host "  DB_INIT_PASSWORD loaded from .env (length=$($pw.Length))." -ForegroundColor DarkGray
    }
    Run-Python "manage.py load_demo_data"
    Write-Host "Demo data load complete. Verifying inventory..." -ForegroundColor Green
    Run-Python "manage.py demo_data_inventory"
  }
  "inventory" {
    Write-Host "→ Demo data inventory" -ForegroundColor Cyan
    Run-Python "manage.py demo_data_inventory"
  }
  "shell" {
    Write-Host "→ Django shell_plus fallback to plain shell" -ForegroundColor Cyan
    & $python manage.py shell
  }
  "runserver" {
    if (-not $SkipMigrationsCheck) {
      Write-Host "→ Pre-flight: check" -ForegroundColor Cyan
      Run-Python "manage.py check"
      Run-Python "manage.py showmigrations --plan" -NoExitCheck
      $pending = @($script:LastPyLines | Select-String "\[ \]")
      if ($pending.Count -gt 0) {
        Write-Host "→ Pre-flight: $($pending.Count) migration(s) pending → migrate" -ForegroundColor Yellow
        Run-Python "manage.py migrate"
      } else {
        Write-Host "→ Pre-flight: all migrations applied." -ForegroundColor Green
      }
    } else {
      Write-Host "→ Pre-flight: check" -ForegroundColor Cyan
      Run-Python "manage.py check"
    }
    Write-Host "→ Django dev server starting on http://127.0.0.1:$Port/   ([Ctrl+C] to stop)" -ForegroundColor Green
    # Launch via cmd.exe with stderr/stdout merged so PowerShell doesn't turn Python RuntimeWarning stderr into aborts.
    $runBat = Join-Path $env:TEMP ("horilla-runserver-" + [guid]::NewGuid().ToString("N") + ".bat")
@"
@echo off
setlocal
set PYTHONIOENCODING=UTF-8
set PYTHONUTF8=1
"$python" manage.py runserver "127.0.0.1:$Port"
"@ | Set-Content -Path $runBat -Encoding ASCII -Force
    try {
      & cmd /c "`"$runBat`""
    } finally {
      Remove-Item -Path $runBat -ErrorAction SilentlyContinue
    }
  }
}
