[CmdletBinding()]
param(
    [string]$PostgresBin = "",
    [string]$DataDirectory = "",
    [int]$Port = 55432,
    [string]$Database = "hydra_phase0",
    [string]$Bind = "127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

function Test-PostgresRunning {
    param(
        [string]$BinDirectory,
        [string]$ClusterDirectory
    )

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

if (-not $PostgresBin) {
    $PostgresBin = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
        Sort-Object { [version]$_.Name } -Descending |
        ForEach-Object { Join-Path $_.FullName "bin" } |
        Where-Object { Test-Path (Join-Path $_ "pg_ctl.exe") } |
        Select-Object -First 1
}
if (-not $PostgresBin) {
    throw "PostgreSQL tools were not found. Pass -PostgresBin."
}
if (-not $DataDirectory) {
    $DataDirectory = Join-Path $repoRoot ".local\postgres-data"
}
$DataDirectory = [System.IO.Path]::GetFullPath($DataDirectory)
$secretPath = Join-Path $repoRoot ".local\django-secret.txt"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython) -or -not (Test-Path $secretPath) -or -not (Test-Path (Join-Path $DataDirectory "PG_VERSION"))) {
    throw "Local environment is incomplete. Run .\scripts\bootstrap-local.ps1 first."
}

if (-not (Test-PostgresRunning -BinDirectory $PostgresBin -ClusterDirectory $DataDirectory)) {
    & (Join-Path $PostgresBin "pg_ctl.exe") -D $DataDirectory -l (Join-Path $DataDirectory "postgres.log") -o "-p $Port -h 127.0.0.1" -w start
    if ($LASTEXITCODE -ne 0) {
        throw "Starting local PostgreSQL cluster failed with exit code $LASTEXITCODE."
    }
}

$env:DATABASE_URL = "postgresql://hydra_local@127.0.0.1:$Port/$Database"
$env:DEBUG = "True"
$env:SECRET_KEY = [System.IO.File]::ReadAllText($secretPath).Trim()
$env:ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:CSRF_TRUSTED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000"
$env:TIME_ZONE = "Europe/Warsaw"

& $venvPython manage.py runserver $Bind --noreload
