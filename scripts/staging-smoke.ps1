[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [uri]$BaseUrl,
    [switch]$ForwardedHttps
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-SmokeRequest {
    param([string]$Path, [int[]]$ExpectedStatus)
    $uri = [uri]::new($BaseUrl, $Path)
    $headers = @{}
    if ($ForwardedHttps) {
        $headers["X-Forwarded-Proto"] = "https"
    }
    try {
        $response = Invoke-WebRequest -Uri $uri -Headers $headers -UseBasicParsing -MaximumRedirection 0
        $status = [int]$response.StatusCode
    }
    catch {
        if ($_.Exception.Response) {
            $response = $_.Exception.Response
            $status = [int]$response.StatusCode
        }
        else {
            throw
        }
    }
    if ($status -notin $ExpectedStatus) {
        throw "$Path returned HTTP $status; expected $($ExpectedStatus -join ', ')."
    }
    return $response
}

$health = Invoke-SmokeRequest -Path "/health/" -ExpectedStatus @(200)
if ($health.Content -notmatch '"status"\s*:\s*"ok"') {
    throw "Liveness response is invalid."
}

$ready = Invoke-SmokeRequest -Path "/health/ready/" -ExpectedStatus @(200)
if ($ready.Content -notmatch '"status"\s*:\s*"ready"') {
    throw "Readiness response is invalid."
}

Invoke-SmokeRequest -Path "/initialize-database" -ExpectedStatus @(404) | Out-Null
Invoke-SmokeRequest -Path "/load-demo-database" -ExpectedStatus @(404) | Out-Null
$root = Invoke-SmokeRequest -Path "/" -ExpectedStatus @(200, 301, 302)

if (($BaseUrl.Scheme -eq "https" -or $ForwardedHttps) -and -not $root.Headers["Strict-Transport-Security"]) {
    throw "HTTPS response is missing Strict-Transport-Security."
}

Write-Host "Hydra staging smoke checks passed for $BaseUrl"
