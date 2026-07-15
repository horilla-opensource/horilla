[CmdletBinding()]
param(
    [string]$ComposeFile = "docker-compose.staging.yaml",
    [string]$EnvFile = ".env.staging",
    [string]$BackupId = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing $EnvFile. Copy .env.staging.example and replace every placeholder first."
}

if ($BackupId -and $BackupId -notmatch '^[A-Za-z0-9._-]+$') {
    throw "BackupId may contain only letters, digits, dot, underscore, and dash."
}

$compose = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile)
$serverWasStopped = $false
try {
    & docker @compose stop server
    if ($LASTEXITCODE -ne 0) { throw "Could not stop the application server." }
    $serverWasStopped = $true

    $run = $compose + @("--profile", "ops", "run", "--rm", "backup", "/ops/staging-backup.sh")
    if ($BackupId) { $run += $BackupId }
    & docker @run
    if ($LASTEXITCODE -ne 0) { throw "Cold backup failed." }
}
finally {
    if ($serverWasStopped) {
        & docker @compose up -d server
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Backup finished, but the application server did not restart."
        }
    }
}
