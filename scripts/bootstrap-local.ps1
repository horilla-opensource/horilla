[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$PostgresBin = "",
    [string]$DataDirectory = "",
    [int]$Port = 55432,
    [string]$Database = "hydra_phase0",
    [switch]$RecreateVenv
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

function Assert-NativeSuccess {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

function Test-PostgresRunning {
    param(
        [string]$BinDirectory,
        [string]$ClusterDirectory
    )

    # PowerShell 5 can promote a native program's stderr to a terminating
    # error when ErrorActionPreference is Stop. pg_ctl uses stderr for the
    # expected "not running" status, so inspect its exit code explicitly.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & (Join-Path $BinDirectory "pg_ctl.exe") -D $ClusterDirectory status 2>$null | Out-Null
        $statusExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    return ($statusExitCode -eq 0)
}

function Get-PythonMajorMinor {
    param([string]$Executable)

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $version = & $Executable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $versionExitCode = $LASTEXITCODE
    }
    catch {
        return $null
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($versionExitCode -ne 0) {
        return $null
    }
    return ($version | Out-String).Trim()
}

function Resolve-PostgresBin {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        $resolved = (Resolve-Path $RequestedPath).Path
        if (-not (Test-Path (Join-Path $resolved "initdb.exe"))) {
            throw "PostgresBin does not contain initdb.exe: $resolved"
        }
        return $resolved
    }

    $root = "C:\Program Files\PostgreSQL"
    $candidate = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
        Sort-Object {
            $versionText = $_.Name
            if ($versionText -notmatch "\.") {
                $versionText = "$versionText.0"
            }
            [version]$versionText
        } -Descending |
        ForEach-Object { Join-Path $_.FullName "bin" } |
        Where-Object { Test-Path (Join-Path $_ "initdb.exe") } |
        Select-Object -First 1
    if (-not $candidate) {
        throw "PostgreSQL 16 or 17 tools were not found. Install PostgreSQL or pass -PostgresBin."
    }
    return $candidate
}

$pgBin = Resolve-PostgresBin $PostgresBin
$localRoot = Join-Path $repoRoot ".local"
if (-not $DataDirectory) {
    $DataDirectory = Join-Path $localRoot "postgres-data"
}
$DataDirectory = [System.IO.Path]::GetFullPath($DataDirectory)
$secretPath = Join-Path $localRoot "django-secret.txt"
$venvDirectory = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDirectory "Scripts\python.exe"

$bootstrapPythonVersion = Get-PythonMajorMinor $Python
if ($bootstrapPythonVersion -ne "3.11") {
    throw "Hydra local bootstrap requires CPython 3.11; '$Python' reported '$bootstrapPythonVersion'. Pass -Python with an absolute CPython 3.11 path."
}

New-Item -ItemType Directory -Force -Path $localRoot | Out-Null
$venvVersion = Get-PythonMajorMinor $venvPython
if ((Test-Path $venvDirectory) -and $venvVersion -ne "3.11") {
    if (-not $RecreateVenv) {
        throw "The existing .venv is unusable or is not CPython 3.11. Re-run with -RecreateVenv to replace only this derived environment."
    }
    $resolvedParent = (Resolve-Path (Split-Path $venvDirectory -Parent)).Path
    if ($resolvedParent -ne $repoRoot -or (Split-Path $venvDirectory -Leaf) -ne ".venv") {
        throw "Refusing to remove an unexpected virtual-environment path: $venvDirectory"
    }
    Remove-Item -LiteralPath $venvDirectory -Recurse -Force
    $venvVersion = $null
}
if ($venvVersion -ne "3.11") {
    & $Python -m venv $venvDirectory
    Assert-NativeSuccess "Creating Python virtual environment"
}
& $venvPython -m pip install --upgrade pip
Assert-NativeSuccess "Upgrading pip"
& $venvPython -m pip install -r (Join-Path $repoRoot "requirements.phase0-windows-py311.lock")
Assert-NativeSuccess "Installing Python dependencies"

if (-not (Test-Path (Join-Path $DataDirectory "PG_VERSION"))) {
    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    & (Join-Path $pgBin "initdb.exe") -D $DataDirectory -U hydra_local -A trust --encoding=UTF8 --locale=C
    Assert-NativeSuccess "Initializing local PostgreSQL cluster"
}

if (-not (Test-PostgresRunning -BinDirectory $pgBin -ClusterDirectory $DataDirectory)) {
    $logPath = Join-Path $DataDirectory "postgres.log"
    & (Join-Path $pgBin "pg_ctl.exe") -D $DataDirectory -l $logPath -o "-p $Port -h 127.0.0.1" -w start
    Assert-NativeSuccess "Starting local PostgreSQL cluster"
}

$databaseExists = & (Join-Path $pgBin "psql.exe") -h 127.0.0.1 -p $Port -U hydra_local -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$Database'"
Assert-NativeSuccess "Checking local PostgreSQL database"
if (($databaseExists | Out-String).Trim() -ne "1") {
    & (Join-Path $pgBin "createdb.exe") -h 127.0.0.1 -p $Port -U hydra_local $Database
    Assert-NativeSuccess "Creating local PostgreSQL database"
}

if (-not (Test-Path $secretPath)) {
    $bytes = [byte[]]::new(48)
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    }
    finally {
        $random.Dispose()
    }
    [System.IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($bytes))
}

$env:DATABASE_URL = "postgresql://hydra_local@127.0.0.1:$Port/$Database"
$env:DEBUG = "True"
$env:SECRET_KEY = [System.IO.File]::ReadAllText($secretPath).Trim()
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:CSRF_TRUSTED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000"
$env:TIME_ZONE = "Europe/Warsaw"

# Upstream branch 1.0 does not version baseline migrations. This command is
# intentionally required for a clean clone and is documented as a Phase 0 risk.
& $venvPython manage.py makemigrations --noinput
Assert-NativeSuccess "Generating upstream baseline migrations"
& $venvPython manage.py migrate --noinput
Assert-NativeSuccess "Applying database migrations"
& $venvPython manage.py check
Assert-NativeSuccess "Running Django system checks"

Write-Output "Local Hydra bootstrap completed."
Write-Output "Run: .\scripts\run-local.ps1 -PostgresBin `"$pgBin`" -DataDirectory `"$DataDirectory`" -Port $Port -Database $Database"
