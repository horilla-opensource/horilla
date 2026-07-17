# Hydra staging, recovery, and pilot gate

Task 045 supplies the hardened staging boundary for Hydra. It does not silently authorize a business pilot: deployment readiness and business approval are separate gates, and both must pass.

## Delivered staging boundary

The staging stack uses Python 3.11, PostgreSQL 17, pinned Python dependencies, a non-root web container, a single-owner maintenance container, a non-superuser application database role, private named volumes, internal ClamAV malware scanning, loopback-only HTTP publication, explicit secrets, and dedicated health probes. PostgreSQL and ClamAV are not published on host ports.

For `HYDRA_PROCESS_ROLE=web`, the production entrypoint performs only reviewed operations:

1. `manage.py check --deploy`;
2. apply committed migrations;
3. collect static files;
4. run the fail-closed `hydra_readiness` command;
5. replace the shell with Gunicorn.

For `HYDRA_PROCESS_ROLE=maintenance`, the same image checks deployment/schema state and starts the advisory-lock-protected worker documented in `HYDRA_MAINTENANCE.md`; it never migrates. Neither role runs `makemigrations` or creates a fixed administrator. The upstream browser database initializer and demo loader are hidden. Legacy APScheduler remains disabled in every process.

Relevant files:

- `docker-compose.staging.yaml` — isolated staging services and volumes;
- `.env.staging.example` — placeholder-only configuration contract;
- `Dockerfile` and `entrypoint.sh` — pinned, non-root runtime and fail-closed boot;
- `hydra_ops/` — readiness rules, private public response, and tests;
- `hydra_ops/maintenance.py` — PostgreSQL single-owner lock, heartbeat, bounded job cycles, and health state;
- `hydra_documents/` — fail-closed ClamAV client, quarantine, retention/legal hold, secure deletion, and purge/rescan commands;
- `scripts/staging-deploy.ps1` — pre-deploy recovery point, rollout, and smoke test;
- `scripts/staging-backup.ps1` — cold application recovery point;
- `scripts/staging-restore-verify.ps1` — isolated restore and private-object verification;
- `scripts/staging-validate-archive.sh` — fail-closed member/path/type validation before sensitive archive extraction;
- `scripts/staging-rollback.ps1` — code-only rollback with an explicit schema-compatibility acknowledgement;
- `scripts/staging-smoke.ps1` — external liveness/readiness/security smoke checks.
- `scripts/verify-migration-manifest.py` and `deployment/migration-manifest.sha256` — exact reviewed migration-source set and normalized SHA-256 content gate;
- `.github/workflows/hydra-staging-ci.yml` — clean Linux/PostgreSQL regression plus live Compose, recovery, and evidence gate.

## Configuration and secrets

Copy `.env.staging.example` to `.env.staging` on the deployment host. `.env.staging` and backup output are ignored by Git and excluded from the Docker build context. Replace every `REPLACE_*` value with an independently generated secret. Do not reuse the PostgreSQL administrator password as the application password.

Readiness rejects staging when any of these conditions is false:

- `DEBUG=False` and a non-default secret key of at least 50 characters;
- explicit `ALLOWED_HOSTS`, explicit HTTPS CSRF origins, HTTPS redirect, secure cookies, and HSTS;
- PostgreSQL with a non-superuser application role;
- a non-placeholder deployment revision;
- disabled web database initialization and disabled in-process schedulers;
- applied migrations and a successful database query;
- no legacy Person/case-type group with more than one active legalization case;
- no overlapping legalization deputy windows, stale current/future deputy principal, or case without a responsibility baseline;
- no overlapping active housing period per Person or bed, assignment without an origin event, or cancelled/moved lifecycle state mismatch;
- distinct, readable, writable public, private, and quarantine roots;
- positive document/quarantine retention policies, bounded candidate-import source-data windows, plus a configured and responsive ClamAV daemon;
- bounded maintenance cadence, stale window, batch size, delivery attempts, and failure threshold;
- collected static assets.

The public probes intentionally disclose no internal detail:

```text
GET /health/        -> 200 {"status":"ok"}
GET /health/ready/  -> 200 {"status":"ready"} or 503 {"status":"not_ready"}
```

Operators get the detailed result inside the container:

```powershell
docker compose --env-file .env.staging -f docker-compose.staging.yaml exec server `
  python manage.py hydra_readiness --json
```

## First deployment

The host must provide Docker Compose v2, TLS termination/reverse proxy, encrypted persistent storage, restricted backup storage, monitoring, and a secret-management process. The application port binds only to loopback and is intended to sit behind that reverse proxy. Capacity planning must reserve the memory required by ClamAV signature loading and updates; scanner health and signature freshness require alerts.

Validate configuration before starting:

```powershell
docker compose --env-file .env.staging -f docker-compose.staging.yaml config --quiet
```

For the first empty environment:

```powershell
.\scripts\staging-deploy.ps1 `
  -Revision <reviewed-git-sha> `
  -BaseUrl https://staging.example.com `
  -InitialDeployment
```

`-InitialDeployment` is not an operator promise. After PostgreSQL becomes
healthy, the deploy script queries `pg_catalog` and starts no application
service unless the `public` schema is proven to contain zero application
relations. An unreadable state or any existing table, partition, view,
sequence, materialized view or foreign table refuses the shortcut. A partially
completed first deployment must therefore be rerun without
`-InitialDeployment`, so the normal cold-backup gate applies.

Create the first administrator once, interactively, after readiness passes:

```powershell
docker compose --env-file .env.staging -f docker-compose.staging.yaml exec server `
  python manage.py createsuperuser
```

Do not automate an administrator password in Compose, the image, shell history, or source control. Assign only the scoped Hydra permissions required for the pilot role.

For later releases omit `-InitialDeployment`. The deployment script creates a cold recovery point before changing the image and prints its backup id.

## Backup contract

The supported staging backup is the PowerShell wrapper, not a direct call to the container helper. It stops both database-writing Hydra services (web and maintenance), captures one PostgreSQL custom-format dump plus public/private media and retained portal-email outbox archives, hashes every artifact, atomically publishes the backup directory, and waits for both services to return healthy. Quarantine blobs are intentionally excluded so known-untrusted content is not propagated into recovery sets; their database evidence remains.

```powershell
.\scripts\staging-backup.ps1 -BackupId before-release-20260715
.\scripts\staging-restore-verify.ps1 -BackupId before-release-20260715
```

Each backup contains:

```text
database.dump
media.tar.gz
private-media.tar.gz
portal-email-outbox.tar.gz
manifest.json
SHA256SUMS
```

Verification fails unless all artifact hashes match, a temporary database can be created and restored with `pg_restore --exit-on-error`, migration history exists, every `PrivateDocument.file` object exists in the restored private archive, and every retained portal-email attachment exists in the outbox archive with the SHA-256 recorded in database metadata. Before extraction, the private and outbox archives must also contain only unique opaque paths and regular files/directories; absolute/traversal paths, control/unsupported characters, duplicates, symlinks, hardlinks, devices and FIFOs are rejected. Extraction never restores archive ownership or permission bits. The temporary database and extracted objects are removed in a trap.

The deployment platform must additionally copy successful, verified backups to encrypted off-host storage with retention and access logging. Backup retention is part of the personal-data policy because older database dumps can contain import-preview values that the live database later redacts. A backup that has not passed restore verification is not a recovery point.

## Rollback and recovery

Code-only rollback is allowed only when the migration review confirms backward compatibility:

```powershell
.\scripts\staging-rollback.ps1 `
  -PreviousRevision <previous-git-sha> `
  -PreviousImage <immutable-registry-image> `
  -BaseUrl https://staging.example.com `
  -SchemaBackwardCompatible
```

Never reverse a destructive schema change in place and never run `docker compose down --volumes` during rollback. For database recovery use blue/green recovery:

1. remove the environment from traffic and preserve the failed volumes;
2. provision a separate project name and empty encrypted volumes;
3. restore the selected verified dump and media archives into the new environment;
4. start maintenance and drain due candidate-import/document cleanup, then run `hydra_readiness`, the automated smoke script, private-object checksum verification, and the manual scoped journeys below;
5. switch traffic only after approval; retain the previous environment until the recovery window closes.

## Pilot verification

Automated gates:

```powershell
python manage.py check
python scripts/verify-migration-manifest.py
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python manage.py test
python manage.py hydra_readiness
python manage.py hydra_maintenance_health
.\scripts\staging-smoke.ps1 -BaseUrl https://staging.example.com
```

Every pull request and push to `main` or `codex/**` also runs **Hydra staging CI**. Its first job installs the pinned set on clean Ubuntu/Python 3.11, installs the reviewed auth compatibility migration, verifies the exact 67-file migration source manifest, applies the committed baseline to PostgreSQL 17, checks model drift/readiness, and runs the full Django suite. The manifest covers every first-party numbered migration plus the pinned Django auth compatibility source; hashes normalize CRLF to LF so Windows and Linux checkouts are equivalent. A missing, added, replaced, or edited migration fails until both the source and manifest change are reviewed. The image build independently executes the same verifier before creating runtime directories. The second CI job starts the real Compose stack, checks the non-root container and non-superuser database role, runs external smoke checks, creates a cold backup, restores it into an isolated database, repeats smoke checks, and uploads redacted operational evidence for 14 days. It never publishes an image or deploys to a shared environment.

Manual acceptance uses non-production test identities and at least two companies/teams:

1. Sign in as coordinator and brigadier roles; confirm each navigation item and action matches the approved permission matrix. Confirm the legalization-operator role has both authority-event permissions and both renewal-link permissions. Grant `view_legalizationworkload`, `view_legalizationcasedelegation`, `manage_legalizationdelegation`, `view_legalizationworkevent`, and `assign_legalizationcase` only to the approved responsibility roles.
2. Repeat direct UUID/ID requests across teams for People, applications, arrivals, assignments, legalization cases/authority events/renewal links, private documents, templates, and reports; expect the documented 403/404 behavior and audit events.
3. Preview and commit a candidate XLSX twice; confirm validation, duplicate handling, idempotency, all-or-nothing rollback, manual discard, deadline masking and maintenance redaction. Confirm the importer role has `purge_candidateimportsession`.
4. Convert one Person to Employee twice; confirm a single Employee and stable Person link.
5. On a non-production legalization case, record submission, an information request/response and a decision with scanned evidence. Start its renewal and separately link a verified historical pair with a reason. Appoint/revoke a bounded same-scope deputy, transfer responsibility and inspect the scoped workload queue. Confirm idempotency, independent deputy scope, automatic delegation revocation on transfer, no copied external facts, readiness invariants, scoped admin visibility and append-only history/lineage/work facts.
6. Assign and reassign an Employee team; confirm current scope and immutable history. Reserve housing for a planned arrival, cancel one reservation, and move one current/scheduled assignment; confirm scope, paired append-only events, conflict rollback and all four housing readiness checks.
7. Verify brigadier and coordinator exception views at desktop and 390 px width.
8. Upload/download one approved inert test document, verify its clean scan, then confirm scanner-down, detected-test-artifact, denied, and cross-scope behavior plus the restored SHA-256. Exercise retention/legal hold, tombstone deletion, and maintenance purge on non-production data.
9. Export a scoped template workbook and operational CSV; confirm excluded-team data and dangerous spreadsheet formulas are absent.
10. Confirm the Hydra public-link directory exposes no identity data and still points only to allowlisted HTTPS destinations.
11. Review logs, database/volume monitoring, backup copy, restore evidence, and rollback owner/contact details.

## Go/no-go decision

The code-level staging package and local recovery drill are complete. The current business-pilot decision remains **NO-GO** until the target staging environment records all of the following:

- successful **Hydra staging CI** run plus Linux container build, Compose start, readiness, and external smoke test on the target host;
- TLS/reverse-proxy validation, encrypted volumes, secret-manager injection, monitoring, and encrypted off-host backup;
- restore verification using a backup created by the actual staging stack;
- review and commit of the surfaced upstream baseline migrations and the pinned Django auth compatibility migration;
- target-host evidence for ClamAV health/signature updates, quarantine purge scheduling, approved retention/legal-hold policy, encrypted storage, and the private-document failure/false-positive runbook;
- target-host evidence for maintenance heartbeat/failure alerts, advisory-lock exclusivity, organization/automation/responsibility notification retry and exhaustion handling, candidate-import redaction, bounded encrypted-backup retention, and backup stopping both writers;
- signed permission matrix, pilot data set, support owner, rollback owner, maintenance window, and acceptance record.

After every item is evidenced, the accountable business and technical owners may record **GO**. Readiness alone is never business approval.

## Verification evidence for task 045

Verified locally through 2026-07-16 with PostgreSQL 17:

- focused `hydra_ops` tests: 34/34 passed;
- exact migration-manifest tests: 4/4 passed, and the verifier matched all 67 reviewed migration sources including the pinned Django auth compatibility source, controlled recruitment workflow, Person duplicate-merge, private-document version and legalization-configuration migrations;
- focused Person-timeline tests: 7/7 passed, and the combined organization-scope/timeline run passed 20/20;
- focused controlled-recruitment-workflow tests: 11/11 passed; the affected onboarding-handoff/portal-email regression passed 35/35 after their fixtures were moved through the same public transition service;
- offline staging-script safety tests: 6/6 passed for empty/non-empty initial deployment plus safe, traversal, duplicate-path and symlink archives;
- full clean-database Django regression: 394/394 passed after organization-access lifecycle, maintenance-worker, configurable snapshotted legalization policy and authority correspondence, renewal lineage and responsibility continuity, legalization/arrival automation, candidate-import source-data retention, attendance reconciliation, controlled recruitment transitions, controlled onboarding handoff, durable portal-email outbox, the reasoned Housing reservation/cancellation/atomic-move lifecycle, the scope-safe Person timeline, privileged duplicate comparison/canonical merge, logical private-document rules/version chains and readiness integrity guards, the staging deploy/archive safety guards, and exact migration-source verification; focused PostgreSQL evidence is recorded in the domain documents;
- `manage.py check`, `migrate --check`, `makemigrations --check --dry-run`, readiness, migration-manifest verification, Python compilation, workflow YAML parsing, dependency consistency, and `git diff --check` passed;
- real custom-format database dump restored into an isolated temporary database;
- restored database contained 84 migration records and one private-document metadata row;
- the restored private object SHA-256 was `653893bd4c4d8f6a0a472815d1f88b92e46ada775277c3a973cf7b7a64d22606`, equal to database metadata;
- PowerShell and Bash scripts passed syntax parsing; Compose passed YAML parsing.

Docker is not installed on the audit workstation, so the workflow definition is locally syntax-validated but its Linux image/Compose jobs must pass in GitHub before they count as evidence. A successful CI run reduces risk but does not replace the target-host and business-owner gates.
