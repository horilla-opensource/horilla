[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Revision,
    [Parameter(Mandatory = $true)]
    [uri]$BaseUrl,
    [string]$Image = "",
    [switch]$InitialDeployment,
    [string]$ComposeFile = "docker-compose.staging.yaml",
    [string]$EnvFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing $EnvFile."
}

$backupId = "none-initial-deployment"
if (-not $InitialDeployment) {
    $backupId = "predeploy-$Revision-$(Get-Date -Format 'yyyyMMddHHmmss')"
    & "$PSScriptRoot\staging-backup.ps1" -ComposeFile $ComposeFile -EnvFile $EnvFile -BackupId $backupId
}

$env:HYDRA_DEPLOYMENT_REVISION = $Revision
$compose = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile)

if ($Image) {
    $env:HYDRA_IMAGE = $Image
    & docker @compose pull server
}
else {
    & docker @compose build --pull server
}
if ($LASTEXITCODE -ne 0) { throw "Image preparation failed; backup id is $backupId." }

& docker @compose up -d db
if ($LASTEXITCODE -ne 0) { throw "Database start failed; backup id is $backupId." }
& docker @compose up -d --no-deps server
if ($LASTEXITCODE -ne 0) { throw "Application deployment failed; backup id is $backupId." }

& "$PSScriptRoot\staging-smoke.ps1" -BaseUrl $BaseUrl
Write-Host "Deployment $Revision passed smoke checks. Recovery point: $backupId"
