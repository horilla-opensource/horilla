[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("20", "50", "100", "150", "200", "spike")]
    [string]$Stage,
    [ValidatePattern('^[a-z0-9][a-z0-9-]{2,30}$')]
    [string]$RunId = "lt-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [ValidateRange(1, 65535)]
    [int]$HttpPort = 18080,
    [ValidateRange(0, 86400)]
    [int]$DurationOverrideSeconds = 0,
    [ValidateRange(10, 500)]
    [int]$DbConnectionSafetyLimit = 50,
    [string]$EnvFile = ".env.staging",
    [string]$ComposeFile = "docker-compose.staging.yaml",
    [string]$LoadComposeFile = "docker-compose.load.yaml",
    [string]$ArtifactsRoot = ".local\load-results",
    [switch]$KeepEnvironment
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$stageConfig = @{
    "20" = @{ Users = 20; Duration = 900; SpawnRate = 2; Shape = "standard" }
    "50" = @{ Users = 50; Duration = 1800; SpawnRate = 2; Shape = "standard" }
    "100" = @{ Users = 100; Duration = 3600; SpawnRate = 2; Shape = "standard" }
    "150" = @{ Users = 150; Duration = 3600; SpawnRate = 2; Shape = "standard" }
    "200" = @{ Users = 200; Duration = 7200; SpawnRate = 2; Shape = "standard" }
    "spike" = @{ Users = 200; Duration = 365; SpawnRate = 10; Shape = "spike" }
}
$config = $stageConfig[$Stage]
$requiredDuration = [int]$config.Duration
$duration = if ($DurationOverrideSeconds -gt 0) { $DurationOverrideSeconds } else { $requiredDuration }
$users = [int]$config.Users
$spawnWarmupSeconds = [int][math]::Ceiling($users / [double][int]$config.SpawnRate)
$runDuration = if ($config.Shape -eq "standard") {
    $duration + $spawnWarmupSeconds + 30
}
else {
    $duration
}
$projectName = "hydra-load-$RunId"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-RepoFile {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) { return (Resolve-Path -LiteralPath $Path).Path }
    return (Resolve-Path -LiteralPath (Join-Path $repoRoot $Path)).Path
}

function Convert-ToInvariantDouble {
    param([object]$Value)
    $text = ([string]$Value).Trim().TrimEnd('%')
    [double]$result = 0
    if ([double]::TryParse(
        $text,
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$result
    )) { return $result }
    return 0.0
}

$envPath = Resolve-RepoFile $EnvFile
$composePath = Resolve-RepoFile $ComposeFile
$loadComposePath = Resolve-RepoFile $LoadComposeFile
$artifactParent = if ([System.IO.Path]::IsPathRooted($ArtifactsRoot)) {
    [System.IO.Path]::GetFullPath($ArtifactsRoot)
}
else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $ArtifactsRoot))
}
$artifactPath = Join-Path (Join-Path $artifactParent $RunId) $Stage
if (Test-Path -LiteralPath $artifactPath) {
    if (@(Get-ChildItem -LiteralPath $artifactPath -Force).Count -gt 0) {
        throw "Artifact directory already contains data: $artifactPath"
    }
}
else {
    New-Item -ItemType Directory -Path $artifactPath -Force | Out-Null
}
$artifactPath = (Resolve-Path -LiteralPath $artifactPath).Path
$eventPath = Join-Path $artifactPath "events.jsonl"
$resourcePath = Join-Path $artifactPath "resources.csv"
$evidencePath = Join-Path $artifactPath "run-evidence.json"

function Add-RunEvent {
    param([string]$Kind, [string]$Detail)
    [ordered]@{
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
        kind = $Kind
        detail = $Detail
    } | ConvertTo-Json -Compress | Add-Content -LiteralPath $eventPath -Encoding UTF8
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is unavailable. Install and start Docker Engine (Docker Desktop on Windows) before running a Hydra load stage."
}
& docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Engine is unavailable. Start Docker Desktop on Windows or the Docker service on Linux before running a Hydra load stage."
}
$memoryText = (& docker info --format '{{.MemTotal}}').Trim()
[long]$dockerMemory = 0
if (-not [long]::TryParse($memoryText, [ref]$dockerMemory)) {
    throw "Could not determine Docker Engine memory capacity."
}
$minimumGiB = if ($users -ge 150) { 8 } else { 6 }
if ($dockerMemory -lt ($minimumGiB * 1GB)) {
    throw "Stage $Stage requires at least $minimumGiB GiB available to Docker Engine; detected $([math]::Round($dockerMemory / 1GB, 2)) GiB."
}

$password = [string]$env:HYDRA_LOAD_TEST_PASSWORD
if ($password.Length -lt 16 -or $password.ToLowerInvariant().Contains("replace")) {
    throw "Set HYDRA_LOAD_TEST_PASSWORD to at least 16 non-placeholder characters in the current PowerShell session."
}

$existing = @(& docker ps -a --filter "label=com.docker.compose.project=$projectName" --quiet)
if ($existing.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$existing[0])) {
    throw "Compose project $projectName already exists. Use a new RunId; existing containers will not be modified."
}

$revision = (& git -C $repoRoot rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($revision)) { $revision = "uncommitted-load" }
$env:HYDRA_DEPLOYMENT_REVISION = "$revision-load"
$env:HYDRA_LOAD_TEST_ENABLED = "True"
$env:HYDRA_LOAD_TEST_RUN_ID = $RunId
$env:HYDRA_LOAD_USERS = [string]$users
$env:HYDRA_LOAD_SPAWN_RATE = [string]$config.SpawnRate
$env:HYDRA_LOAD_DURATION = "${runDuration}s"
$env:HYDRA_LOAD_SHAPE = [string]$config.Shape
$env:HYDRA_LOAD_ARTIFACTS_PATH = $artifactPath
$env:HYDRA_HTTP_PORT = [string]$HttpPort
$env:HYDRA_WEB_REPLICAS = "2"
$env:HYDRA_LOAD_IMAGE = "hydra-load:$revision"
$env:HYDRA_LOAD_RUNTIME_UID = "10002"
$env:HYDRA_LOAD_RUNTIME_GID = "10002"
if ([System.IO.Path]::DirectorySeparatorChar -eq '/') {
    $runtimeUid = [string](& id -u)
    $runtimeUidExitCode = $LASTEXITCODE
    $runtimeGid = [string](& id -g)
    $runtimeGidExitCode = $LASTEXITCODE
    $runtimeUid = $runtimeUid.Trim()
    $runtimeGid = $runtimeGid.Trim()
    if (
        $runtimeUidExitCode -ne 0 -or
        $runtimeGidExitCode -ne 0 -or
        $runtimeUid -notmatch '^\d+$' -or
        $runtimeGid -notmatch '^\d+$'
    ) {
        throw "Could not determine the Linux host UID/GID for the load artifact bind mount."
    }
    $env:HYDRA_LOAD_RUNTIME_UID = $runtimeUid
    $env:HYDRA_LOAD_RUNTIME_GID = $runtimeGid
}

$composePrefix = @(
    "compose", "--project-name", $projectName,
    "--env-file", $envPath,
    "-f", $composePath,
    "-f", $loadComposePath,
    "--profile", "load"
)

function Invoke-Compose {
    param([string[]]$Arguments, [switch]$Capture)
    if ($Capture) {
        $output = @(& docker @composePrefix @Arguments)
        if ($LASTEXITCODE -ne 0) { throw "Docker Compose command failed: $($Arguments[0])" }
        return $output
    }
    & docker @composePrefix @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose command failed: $($Arguments[0])" }
}

function Invoke-Integrity {
    param([string]$Phase)
    $output = @(& docker @composePrefix exec -T server python manage.py hydra_load_integrity --run-id $RunId --users 200 --json)
    $ok = $LASTEXITCODE -eq 0 -and (($output -join "`n") -match '"status"\s*:\s*"ok"')
    ($output -join "`n") | Set-Content -LiteralPath (Join-Path $artifactPath "integrity-$Phase.json") -Encoding UTF8
    if (-not $ok) { throw "Load-test data integrity failed during $Phase."
    }
    return $true
}

function Write-QueryProfile {
    param([string]$Phase)
    $output = @(& docker @composePrefix exec -T server python manage.py hydra_load_profile_queries --run-id $RunId)
    if ($LASTEXITCODE -ne 0 -or -not (($output -join "`n") -match '"profiles"')) {
        throw "Load query profiling failed during $Phase."
    }
    ($output -join "`n") | Set-Content -LiteralPath (Join-Path $artifactPath "query-profile-$Phase.json") -Encoding UTF8
}

function Test-ExternalReadiness {
    try {
        $response = Invoke-WebRequest `
            -Uri "http://127.0.0.1:$HttpPort/health/ready/" `
            -Headers @{"X-Forwarded-Proto" = "https"} `
            -UseBasicParsing `
            -TimeoutSec 8
        return [int]$response.StatusCode -eq 200 -and $response.Content -match '"status"\s*:\s*"ready"'
    }
    catch { return $false }
}

function Get-ProjectStates {
    $ids = @(& docker ps -a --filter "label=com.docker.compose.project=$projectName" --quiet)
    $states = @()
    foreach ($id in $ids) {
        if ([string]::IsNullOrWhiteSpace([string]$id)) { continue }
        $line = (& docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}|{{.RestartCount}}|{{json .State}}' $id)
        if ($LASTEXITCODE -ne 0) { throw "Could not inspect project container state." }
        $parts = $line -split '\|', 3
        $states += [pscustomobject]@{
            Id = [string]$id
            Service = $parts[0]
            RestartCount = [int]$parts[1]
            State = ($parts[2] | ConvertFrom-Json)
        }
    }
    return $states
}

function Get-ContainerHealthStatus {
    param([object]$State)
    $healthProperty = $State.PSObject.Properties['Health']
    if ($null -eq $healthProperty -or $null -eq $healthProperty.Value) { return "" }
    $statusProperty = $healthProperty.Value.PSObject.Properties['Status']
    if ($null -eq $statusProperty) { return "" }
    return [string]$statusProperty.Value
}

function Add-ResourceSample {
    $ids = @(& docker ps --filter "label=com.docker.compose.project=$projectName" --quiet)
    [double]$cpu = 0
    [double]$memory = 0
    if ($ids.Count -gt 0) {
        $rows = @(& docker stats --no-stream --format '{{json .}}' @ids)
        if ($LASTEXITCODE -ne 0) { throw "Could not collect Docker resource metrics." }
        foreach ($row in $rows) {
            if ([string]::IsNullOrWhiteSpace([string]$row)) { continue }
            $sample = $row | ConvertFrom-Json
            $cpu += Convert-ToInvariantDouble $sample.CPUPerc
            $memory += Convert-ToInvariantDouble $sample.MemPerc
        }
    }
    $dbOutput = @(& docker @composePrefix exec -T db sh -ec 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql --no-psqlrc --tuples-only --no-align --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --command="SELECT count(*) FROM pg_stat_activity WHERE datname=current_database();"')
    if ($LASTEXITCODE -ne 0) { throw "Could not collect PostgreSQL connection metrics." }
    $dbConnections = [int](($dbOutput | Where-Object { [string]$_ -match '^\s*\d+\s*$' } | Select-Object -Last 1).Trim())
    if ($dbConnections -gt $DbConnectionSafetyLimit) {
        throw "SAFETY STOP: PostgreSQL connections exceeded the configured limit of $DbConnectionSafetyLimit."
    }
    $redisOutput = @(& docker @composePrefix exec -T redis sh -ec 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --raw INFO memory')
    if ($LASTEXITCODE -ne 0) { throw "Could not collect Redis memory metrics." }
    $usedLine = $redisOutput | Where-Object { [string]$_ -match '^used_memory:\d+' } | Select-Object -First 1
    [long]$redisBytes = 0
    if ($usedLine) { [void][long]::TryParse((([string]$usedLine -split ':', 2)[1]).Trim(), [ref]$redisBytes) }
    $values = @(
        (Get-Date).ToUniversalTime().ToString("o"),
        $cpu.ToString("0.###", [System.Globalization.CultureInfo]::InvariantCulture),
        $memory.ToString("0.###", [System.Globalization.CultureInfo]::InvariantCulture),
        $dbConnections,
        $redisBytes
    )
    ($values -join ',') | Add-Content -LiteralPath $resourcePath -Encoding UTF8
}

function Get-LatestLocustAggregate {
    $historyPath = Join-Path $artifactPath "locust_stats_history.csv"
    if (-not (Test-Path -LiteralPath $historyPath)) { return $null }
    try {
        return Import-Csv -LiteralPath $historyPath |
            Where-Object { $_.Name -eq "Aggregated" } |
            Select-Object -Last 1
    }
    catch { return $null }
}

$stackOwned = $false
$loadStarted = $false
$integrityBefore = $false
$integrityAfter = $false
$controlledRestartCompleted = $false
$safetyStopTriggered = $false
$safetyReason = ""
$readinessFailures = 0
$oomCount = 0
$restartLoopCount = 0
$failure = $null
$startedAt = $null
$elapsedSeconds = 0
$highErrorSince = $null
$highLatencySince = $null
$lastIntegrityAt = $null
$fullUsersSince = $null
$fullUserSeconds = 0
$restartAttempted = $false
$expectedCompletedServices = @("release", "redis-volume-init")
"timestamp,cpu_percent,memory_percent,db_connections,redis_used_memory_bytes" |
    Set-Content -LiteralPath $resourcePath -Encoding UTF8
Add-RunEvent "preflight" "Docker Engine, isolated project, and artifact runtime identity checks passed"

try {
    Invoke-Compose -Arguments @("config", "--quiet")
    Invoke-Compose -Arguments @("build", "--pull", "server", "load")
    $stackOwned = $true
    Invoke-Compose -Arguments @(
        "up", "-d", "--wait", "--wait-timeout", "1800", "--scale", "server=2",
        "db", "redis", "clamav", "release", "server", "maintenance", "proxy"
    )
    Add-RunEvent "stack_ready" "Two web replicas and supporting services are healthy"

    & docker @composePrefix exec -T -e HYDRA_LOAD_TEST_PASSWORD server python manage.py hydra_load_seed --run-id $RunId --users 200
    if ($LASTEXITCODE -ne 0) { throw "Authenticated load-test data seeding failed." }
    $integrityBefore = Invoke-Integrity -Phase "before"
    Write-QueryProfile -Phase "before"
    Add-RunEvent "seed_complete" "200 isolated authenticated accounts passed integrity checks"

    Invoke-Compose -Arguments @("up", "-d", "--no-deps", "load")
    $loadStarted = $true
    $startedAt = Get-Date
    $lastIntegrityAt = $startedAt
    Add-RunEvent "load_started" "Stage $Stage started with $users users and a $duration-second required hold"

    while ($true) {
        Start-Sleep -Seconds 10
        $now = Get-Date
        $elapsedSeconds = [int](($now - $startedAt).TotalSeconds)

        if (-not (Test-ExternalReadiness)) {
            $readinessFailures += 1
            throw "SAFETY STOP: application readiness was lost."
        }

        $states = @(Get-ProjectStates)
        foreach ($container in $states) {
            if ([bool]$container.State.OOMKilled) {
                $oomCount += 1
                throw "SAFETY STOP: OOM detected in $($container.Service)."
            }
            if ($container.RestartCount -ge 3) {
                $restartLoopCount += 1
                throw "SAFETY STOP: restart loop detected in $($container.Service)."
            }
            if (
                $container.State.Status -eq "running" -and
                (Get-ContainerHealthStatus -State $container.State) -eq "unhealthy"
            ) {
                throw "SAFETY STOP: unhealthy container detected in $($container.Service)."
            }
            if ($container.State.Status -eq "restarting") {
                $restartLoopCount += 1
                throw "SAFETY STOP: restarting container detected in $($container.Service)."
            }
            if ($container.State.Status -eq "exited" -and $container.Service -ne "load") {
                if (
                    $container.Service -in $expectedCompletedServices -and
                    [int]$container.State.ExitCode -eq 0
                ) {
                    continue
                }
                throw "SAFETY STOP: $($container.Service) exited with code $($container.State.ExitCode) during the stage."
            }
        }

        if (($now - $lastIntegrityAt).TotalSeconds -ge 60) {
            [void](Invoke-Integrity -Phase "running")
            $lastIntegrityAt = $now
        }
        Add-ResourceSample

        $aggregate = Get-LatestLocustAggregate
        if ($null -ne $aggregate) {
            $rps = Convert-ToInvariantDouble $aggregate.'Requests/s'
            $failuresPerSecond = Convert-ToInvariantDouble $aggregate.'Failures/s'
            $rollingErrorRate = if ($rps -gt 0) { $failuresPerSecond / $rps } else { 0.0 }
            $p95 = Convert-ToInvariantDouble $aggregate.'95%'
            $activeUsers = [int](Convert-ToInvariantDouble $aggregate.'User Count')
            if ($activeUsers -ge $users -and $null -eq $fullUsersSince) {
                $fullUsersSince = $now
                Add-RunEvent "full_concurrency_reached" "$users authenticated users are active"
            }
            if ($rollingErrorRate -gt 0.05) {
                if ($null -eq $highErrorSince) { $highErrorSince = $now }
                if (($now - $highErrorSince).TotalSeconds -ge 60) {
                    throw "SAFETY STOP: error rate exceeded 5% continuously for 60 seconds."
                }
            }
            else { $highErrorSince = $null }
            if ($p95 -gt 10000) {
                if ($null -eq $highLatencySince) { $highLatencySince = $now }
                if (($now - $highLatencySince).TotalSeconds -ge 180) {
                    throw "SAFETY STOP: p95 exceeded 10 seconds continuously for 180 seconds."
                }
            }
            else { $highLatencySince = $null }
        }

        if ($Stage -eq "200" -and -not $restartAttempted -and $elapsedSeconds -ge 900) {
            $restartAttempted = $true
            $serverIds = @(& docker @composePrefix ps --quiet server)
            $serverId = @($serverIds | Sort-Object)[0]
            if ([string]::IsNullOrWhiteSpace([string]$serverId)) {
                throw "SAFETY STOP: no web replica was available for the controlled restart."
            }
            Add-RunEvent "controlled_restart_started" "Restarting one web replica after 15 minutes"
            & docker restart --time 30 $serverId *> $null
            if ($LASTEXITCODE -ne 0) { throw "SAFETY STOP: controlled web replica restart failed." }
            $restartDeadline = (Get-Date).AddSeconds(90)
            do {
                Start-Sleep -Seconds 3
                $readyAfterRestart = Test-ExternalReadiness
            } while (-not $readyAfterRestart -and (Get-Date) -lt $restartDeadline)
            if (-not $readyAfterRestart) {
                $readinessFailures += 1
                throw "SAFETY STOP: readiness did not survive the controlled restart."
            }
            [void](Invoke-Integrity -Phase "after-restart")
            $controlledRestartCompleted = $true
            Add-RunEvent "controlled_restart_completed" "Readiness, shared sessions, and data integrity remained available"
        }

        $loadState = $states | Where-Object { $_.Service -eq "load" } | Select-Object -First 1
        if ($null -ne $loadState -and $loadState.State.Status -eq "exited") {
            if ([int]$loadState.State.ExitCode -ne 0) {
                throw "Load generator exited with code $($loadState.State.ExitCode)."
            }
            break
        }
    }

    $elapsedSeconds = [int](((Get-Date) - $startedAt).TotalSeconds)
    if ($fullUsersSince) { $fullUserSeconds = [int](((Get-Date) - $fullUsersSince).TotalSeconds) }
    $integrityAfter = Invoke-Integrity -Phase "after"
    Write-QueryProfile -Phase "after"
    Add-RunEvent "load_completed" "Stage completed and final integrity checks passed"
}
catch {
    $failure = $_.Exception.Message
    if ($loadStarted) {
        & docker @composePrefix stop --timeout 15 load *> $null
    }
    if ($failure -like "SAFETY STOP:*") {
        $safetyStopTriggered = $true
        $safetyReason = $failure
        Add-RunEvent "safety_stop" $failure
    }
    else {
        Add-RunEvent "run_failed" $failure
    }
}
finally {
    if ($startedAt) { $elapsedSeconds = [int](((Get-Date) - $startedAt).TotalSeconds) }
    if ($fullUsersSince) { $fullUserSeconds = [int](((Get-Date) - $fullUsersSince).TotalSeconds) }
    [ordered]@{
        stage = $Stage
        requested_users = $users
        required_duration_seconds = $requiredDuration
        configured_duration_seconds = $duration
        generator_run_time_seconds = $runDuration
        elapsed_seconds = $elapsedSeconds
        full_concurrency_seconds = $fullUserSeconds
        safety_stop_triggered = $safetyStopTriggered
        safety_reason = $safetyReason
        readiness_failures = $readinessFailures
        oom_count = $oomCount
        restart_loop_count = $restartLoopCount
        db_connection_safety_limit = $DbConnectionSafetyLimit
        integrity_before = $integrityBefore
        integrity_after = $integrityAfter
        controlled_restart_completed = $controlledRestartCompleted
        shortened_smoke_run = $duration -lt $requiredDuration
        completed_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $evidencePath -Encoding UTF8

    if ($stackOwned) {
        & docker @composePrefix ps -a *> (Join-Path $artifactPath "compose-ps.txt")
        & docker @composePrefix logs --no-color *> (Join-Path $artifactPath "compose.log")
        if (Test-Path -LiteralPath (Join-Path $artifactPath "locust_stats.csv")) {
            & docker @composePrefix run --rm --no-deps --entrypoint python load `
                /load/summarize.py --artifacts /artifacts --stage $Stage --users $users --duration-seconds $requiredDuration `
                *> (Join-Path $artifactPath "summary-command.txt")
            if ($LASTEXITCODE -ne 0 -and -not $failure) { $failure = "Load summary generation failed." }
        }
        if (-not $KeepEnvironment -and $projectName -match '^hydra-load-[a-z0-9][a-z0-9-]{2,30}$') {
            & docker @composePrefix down --volumes --remove-orphans *> (Join-Path $artifactPath "cleanup.txt")
            if ($LASTEXITCODE -ne 0 -and -not $failure) { $failure = "Isolated Compose cleanup failed." }
        }
    }
}

if ($failure) { throw "$failure Artifacts: $artifactPath" }
$summaryPath = Join-Path $artifactPath "summary.json"
if (-not (Test-Path -LiteralPath $summaryPath)) { throw "Summary is missing. Artifacts: $artifactPath" }
$summary = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
if (-not [bool]$summary.overall_pass) {
    throw "Stage completed but did not meet every acceptance gate. Artifacts: $artifactPath"
}
Write-Host "Hydra load stage $Stage passed. Artifacts: $artifactPath"
