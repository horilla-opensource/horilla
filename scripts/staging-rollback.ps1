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
& docker @compose up -d --no-deps server
if ($LASTEXITCODE -ne 0) { throw "Code rollback failed." }

& "$PSScriptRoot\staging-smoke.ps1" -BaseUrl $BaseUrl
Write-Host "Rollback to $PreviousRevision passed smoke checks."
