[CmdletBinding()]
param(
    [string]$EnvFile = ".env.staging",
    [ValidateRange(1, 65535)]
    [int]$HttpPort = 18080,
    [string]$ArtifactsRoot = ".local\load-results"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$stages = @("20", "50", "100", "150", "200", "spike")
foreach ($stage in $stages) {
    $runId = "plan-$stage-$(Get-Date -Format 'MMddHHmmss')"
    & "$PSScriptRoot\run-load-stage.ps1" `
        -Stage $stage `
        -RunId $runId `
        -HttpPort $HttpPort `
        -EnvFile $EnvFile `
        -ArtifactsRoot $ArtifactsRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Hydra load plan stopped after failed stage $stage."
    }
}

Write-Host "All required Hydra load stages passed in order."
