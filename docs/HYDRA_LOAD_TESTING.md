# Authenticated Hydra load testing on Windows

This runbook executes the required multi-role workload against an isolated,
production-like Hydra stack using Windows PowerShell and Docker Desktop. It
does not use WSL or Agent Lab. A stage is evidence only when its generated
`summary.json` says `measured: true` and `overall_pass: true`.

## Workload contract

Every virtual user performs a normal CSRF-protected Django login with a unique
account and retains a separate shared Redis-backed session. The standard stages
allocate integer accounts deterministically while preserving the required role
profile as closely as an indivisible user permits:

| Users | Recruiter | HR/admin | Coordination | Employee | Legal/housing | Onboarding | Dashboard |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 5 | 4 | 3 | 3 | 2 | 2 | 1 |
| 50 | 13 | 10 | 8 | 7 | 5 | 5 | 2 |
| 100 | 25 | 20 | 15 | 15 | 10 | 10 | 5 |
| 150 | 38 | 30 | 23 | 22 | 15 | 15 | 7 |
| 200 | 50 | 40 | 30 | 30 | 20 | 20 | 10 |

Reads exercise scoped candidates, reports, teams/arrivals, tasks/notifications,
housing/legalization, onboarding, and dashboard selectors. Writes use the real
candidate-stage, Person, assignment, task-transition, housing, and onboarding
domain services. The dashboard role is intentionally read-only. The mix is 80%
reads and 20% writes for writing roles.

After each completed business action, a user spends 15-25 seconds reading the
screen, reviewing data, or completing the next form. This fixed think-time is
part of the committed workload contract, not an operator-tunable acceptance
shortcut, and is recorded in every `run-evidence.json` and summary. At the
acceptance limits, a two-hour 200-user stage still executes roughly 360 actions
per user (about 72,000 authenticated business operations in total), while
avoiding the unrealistic assumption that every HR user submits another form
every one to three seconds for two hours.

The standard 20-, 50-, and 100-user stages use the production-like default of
two stateless web replicas. The 150-, 200-user, and spike stages use three
replicas, still within the supported two-to-four-replica topology. This
evidence-driven scale-out preserves the same business workload and acceptance
thresholds while adding web CPU capacity at the point where a measured
two-replica 150-user run reached 331.45% aggregate CPU and a strict 2,000 ms
login p95 (the contract requires less than 2,000 ms). Every run records the
actual replica count in `run-evidence.json`, `summary.json`, and `summary.csv`.

The seed command creates only `hydra-load-<run-id>-*` accounts and
`HYDRA_LOAD_<RUN_ID>_*` business objects in a new Compose project and volume
set. Load endpoints return 404 unless explicitly enabled in `staging`, supplied
a valid run ID, and called by the exact prefixed account in the exact role
group. Readiness forbids this boundary in production.

## Prerequisites

1. Install and start Docker Desktop with Docker Compose v2.
2. Assign at least 6 GiB for stages through 100 users and at least 8 GiB for
   stages 150, 200, and spike. More headroom is recommended.
3. Copy `.env.staging.example` to ignored `.env.staging` and replace every
   placeholder. Keep `HYDRA_LOAD_TEST_ENABLED=False`; the runner enables it
   only for its isolated project.
4. Set the load password in the current process without placing it in the
   command line or `.env.staging`:

```powershell
$secure = Read-Host "Temporary Hydra load password" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:HYDRA_LOAD_TEST_PASSWORD = `
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
```

The value must contain at least 16 non-placeholder characters. It is passed to
the seeder and Locust container through their process environments, is never
printed, and is not included in Compose logs or committed artifacts.

## Required execution order

Run the complete plan unattended only in a reserved maintenance window; it
takes more than five hours:

```powershell
Set-Location C:\Users\FF\Documents\Codex\2026-07-14\re\outputs\hydra-project
.\scripts\run-load-plan.ps1 -EnvFile .env.staging
```

The plan runs these exact stages and stops at the first failure:

| Stage | Duration | Command |
|---|---:|---|
| 20 | 15 min | `.\scripts\run-load-stage.ps1 -Stage 20` |
| 50 | 30 min | `.\scripts\run-load-stage.ps1 -Stage 50` |
| 100 | 60 min | `.\scripts\run-load-stage.ps1 -Stage 100` |
| 150 | 60 min | `.\scripts\run-load-stage.ps1 -Stage 150` |
| 200 | 120 min | `.\scripts\run-load-stage.ps1 -Stage 200` |
| spike | 5 s to establish 50 sessions, 50 to 200 in exactly 60 s, then 300 s hold | `.\scripts\run-load-stage.ps1 -Stage spike` |

### Isolated GitHub runner fallback

When Docker Desktop is unavailable, the same committed PowerShell runner can
execute on an isolated Ubuntu GitHub Actions runner. This is an explicit
operator action, not an automatic PR load. Push one uniquely named tag at a
time, in the required order, only after the preceding stage passes:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$tag = "hydra-load-20-$stamp"
git tag $tag
git push fork $tag
```

Accepted tag prefixes are `hydra-load-20-`, `hydra-load-50-`,
`hydra-load-100-`, `hydra-load-150-`, `hydra-load-200-`, and
`hydra-load-spike-`. A tag run skips the ordinary regression/staging jobs and
runs only the isolated authenticated stage with a four-hour hard timeout. It
generates and masks ephemeral secrets, uses the same safety stops, destroys its
owned Compose project, and retains the load evidence artifact for 30 days.
Never reuse a tag or advance to the next stage after a failed safety or
acceptance gate.

Inspect and download the result with GitHub CLI:

```powershell
gh run list --repo OleksandrKiris/hydra-platform --workflow hydra-staging-ci.yml
gh run download <run-id> --repo OleksandrKiris/hydra-platform --dir .local\remote-load
```

Each invocation receives a unique run ID by default. `-DurationOverrideSeconds`
exists only for harness smoke diagnostics: a shortened result fails the
required-duration acceptance gate and must never be reported as a completed
stage. Standard stages add a two-login-per-second warm-up and a 30-second
sampling margin. Their acceptance duration starts only after the monitor
observes every required authenticated user active. Standard-stage statistics
retain all login requests so the login p95 gate is based on the complete ramp
rather than a late subset. Thus the 200-user gate proves a full 7,200 seconds at
concurrency 200 rather than counting login ramp time.

## Safety and restart proof

The runner checks readiness and container state every 10 seconds, records
Docker CPU/RAM, PostgreSQL connections, and Redis memory, and runs the isolated
domain-integrity command every 60 seconds. It stops the generator immediately
for:

- any OOM kill or unavailable readiness response;
- any unexpected exit, unhealthy running dependency, failed one-shot service,
  or detected restart loop;
- any data-integrity or organization-isolation failure;
- error rate above 5% continuously for 60 seconds;
- aggregate p95 above 10 seconds continuously for 180 seconds.
- PostgreSQL connection count above the explicit safety limit (50 by default).

At minute 15 of the required 200-user stage, the runner restarts exactly one
web replica, then proves that readiness and integrity remain available while
the other replica serves the existing Redis-backed sessions. This event is a
mandatory 200-user acceptance gate.

## Evidence and cleanup

Artifacts are written under ignored
`.local/load-results/<run-id>/<stage>/`: Locust CSV/HTML, `summary.json`,
`summary.csv`, resource samples, integrity snapshots, safety/restart events,
Compose state, and redacted application logs. Before and after profiles record
bounded ORM query counts and PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` plans by
role without emitting raw SQL. The summary checks the exact duration and active-
user peak plus error-rate and p95/p99 acceptance limits.

The runner refuses an existing Compose project name. On completion or failure,
it removes only the newly owned `hydra-load-<run-id>` containers, network, and
volumes. `-KeepEnvironment` is an explicit diagnostic exception. It never
targets `hydra-staging` or another user's volumes. Raw test artifacts remain
ignored and must not be committed; only reviewed aggregate evidence belongs in
the engineering report.

## Current measured status

The harness contract has passed repository tests for role counts, real password
authentication, separate sessions, all six business writes, authorization
boundaries, integrity, and machine-summary gates. Docker Desktop is not
installed or discoverable on the audit workstation, so no timed stage is
currently measured. The 200-user objective therefore remains **FAIL / NOT
RUN**, not a forecasted pass.
