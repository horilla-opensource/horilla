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

& docker @compose up -d --wait --wait-timeout 1800 db clamav
if ($LASTEXITCODE -ne 0) { throw "Database/scanner start failed; backup id is $backupId." }

if ($InitialDeployment) {
    $databaseStateCommand = 'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql --no-psqlrc --tuples-only --no-align --set ON_ERROR_STOP=1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT COUNT(*) FROM pg_class WHERE relnamespace = ''public''::regnamespace AND relkind IN (''r'', ''p'', ''v'', ''m'', ''S'', ''f'');"'
    $stateOutput = @(& docker @compose exec -T db sh -c $databaseStateCommand)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not prove that the initial-deployment database is empty. No application service was started."
    }
    $lastStateLine = $stateOutput |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
        Select-Object -Last 1
    [long]$publicRelationCount = 0
    if ($null -eq $lastStateLine -or -not [long]::TryParse(([string]$lastStateLine).Trim(), [ref]$publicRelationCount)) {
        throw "Could not parse the initial-deployment database state. No application service was started."
    }
    if ($publicRelationCount -ne 0) {
        throw "InitialDeployment refused: the database already contains $publicRelationCount public relation(s). Run without -InitialDeployment so Hydra creates and verifies a recovery point."
    }
}

& docker @compose stop maintenance
if ($LASTEXITCODE -ne 0) { throw "Could not stop the maintenance writer; backup id is $backupId." }
& docker @compose up -d --wait --wait-timeout 1800 server maintenance
if ($LASTEXITCODE -ne 0) { throw "Application deployment failed; backup id is $backupId." }

& "$PSScriptRoot\staging-smoke.ps1" -BaseUrl $BaseUrl
& docker @compose exec -T maintenance python manage.py hydra_maintenance_health
if ($LASTEXITCODE -ne 0) { throw "Maintenance worker health check failed; backup id is $backupId." }
Write-Host "Deployment $Revision passed smoke checks. Recovery point: $backupId"
