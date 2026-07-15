[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$BackupId,
    [string]$ComposeFile = "docker-compose.staging.yaml",
    [string]$EnvFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing $EnvFile."
}

$arguments = @(
    "compose", "--env-file", $EnvFile, "-f", $ComposeFile,
    "--profile", "ops", "run", "--rm", "backup",
    "/ops/staging-restore-verify.sh", $BackupId
)
& docker @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Restore verification failed. The backup must not be promoted."
}
