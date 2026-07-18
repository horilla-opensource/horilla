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
$servicesWereStopped = $false
try {
    & docker @compose stop proxy maintenance server
    if ($LASTEXITCODE -ne 0) { throw "Could not enter Hydra cold-backup downtime." }
    $servicesWereStopped = $true

    $run = $compose + @("--profile", "ops", "run", "--rm", "backup", "/ops/staging-backup.sh")
    if ($BackupId) { $run += $BackupId }
    & docker @run
    if ($LASTEXITCODE -ne 0) { throw "Cold backup failed." }
}
finally {
    if ($servicesWereStopped) {
        & docker @compose up -d --wait --wait-timeout 1800 server maintenance proxy
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Backup finished, but Hydra services did not restart."
        }
    }
}
