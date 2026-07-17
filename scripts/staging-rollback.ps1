[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$PreviousRevision,
    [Parameter(Mandatory = $true)]
    [string]$PreviousImage,
    [Parameter(Mandatory = $true)]
    [uri]$BaseUrl,
    [Parameter(Mandatory = $true)]
    [switch]$SchemaBackwardCompatible,
    [string]$ComposeFile = "docker-compose.staging.yaml",
    [string]$EnvFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $SchemaBackwardCompatible) {
    throw "In-place rollback is allowed only for a reviewed backward-compatible schema. Use the blue/green recovery runbook for database rollback."
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing $EnvFile."
}

$env:HYDRA_DEPLOYMENT_REVISION = $PreviousRevision
$env:HYDRA_IMAGE = $PreviousImage
$compose = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile)

& docker @compose pull server
if ($LASTEXITCODE -ne 0) { throw "Could not pull the previous image." }
& docker @compose stop maintenance
if ($LASTEXITCODE -ne 0) { throw "Could not stop the maintenance writer." }
& docker @compose up -d --no-deps --wait --wait-timeout 300 server
if ($LASTEXITCODE -ne 0) { throw "Code rollback failed." }
& docker @compose up -d --no-deps --wait --wait-timeout 300 maintenance
if ($LASTEXITCODE -ne 0) { throw "Maintenance rollback failed." }

& "$PSScriptRoot\staging-smoke.ps1" -BaseUrl $BaseUrl
& docker @compose exec -T maintenance python manage.py hydra_maintenance_health
if ($LASTEXITCODE -ne 0) { throw "Maintenance worker health check failed." }
Write-Host "Rollback to $PreviousRevision passed smoke checks."
