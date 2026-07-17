# Hydra production maintenance worker

## Purpose and decision

Hydra must not run scheduled jobs inside Gunicorn workers. Multiple web workers would duplicate notifications, race retention cleanup, and make backup consistency unpredictable. The production design therefore uses one dedicated `maintenance` process from the same reviewed image.

This is a focused **NEW OPERATIONS BOUNDARY**, not a generic workflow engine. It currently owns only concrete production work already required by implemented domains:

- retry pending/failed organization-access notifications;
- retry pending/failed legalization responsibility-transfer and deputy notifications;
- retry pending/failed universal-task assignment and lifecycle notifications after rechecking current recipient scope;
- lease, send and retry opt-in generic notification-center emails after rechecking recipient, scope, archive state and preference;
- alert on exhausted delivery attempts;
- generate idempotent legalization deadline/validity reminders and scoped escalations;
- expire approved legalization cases after their inclusive validity end date;
- generate idempotent upcoming-arrival reminders and scoped overdue escalations without deciding no-show;
- expire bounded temporary housing holds with deterministic Person/bed locks and append-only system evidence;
- reconcile bounded open onboarding handoffs against committed conversion, destination assignment and task facts;
- lease, deliver and retry the onboarding portal email outbox, then reconcile onboarding start independently from SMTP;
- purge expired document-quarantine blobs while preserving evidence rows;
- retry physical cleanup for logically deleted private documents.
- redact expired candidate-import source values while preserving non-sensitive audit evidence and applied-record links.

Future approved recurring jobs will be added as explicit bounded functions with their own tests and cadence; legacy Horilla APScheduler jobs remain disabled.

## Single ownership and failure model

`run_hydra_maintenance` requires PostgreSQL and obtains a fixed session-level advisory lock before registering itself. A second worker cannot run concurrently. The lock is automatically released if the database session or process dies.

`hydra_ops.MaintenanceState` records:

- opaque worker owner UUID and start time;
- heartbeat and cycle timestamps;
- last successful cycle;
- last notification dispatch, legalization/arrival/housing runs, onboarding reconciliation, portal-email dispatch and document purge;
- consecutive failure count and a bounded exception-class code.

Raw exception messages are never persisted because they may contain credentials, filenames, or personal data. A database connection failure exits the process so Compose can restart it. Other task errors are isolated, recorded, and retried; reaching `HYDRA_MAINTENANCE_MAX_FAILURES` exits the worker and fails its health check.

Notification events, task deliveries and portal emails whose attempt limit is exhausted remain a health error requiring operator action. The worker does not silently reset them. Portal email recovery uses the permissioned, scope-checked admin action and preserves the original payload/token while it is retained.

## Commands

Production worker:

```text
python manage.py run_hydra_maintenance
```

One bounded cycle for diagnostics:

```text
python manage.py run_hydra_maintenance --once
python manage.py run_hydra_maintenance --once --force-document-purge
```

Container/monitoring health check and recovery:

```text
python manage.py hydra_maintenance_health
python manage.py hydra_maintenance_health --json
python manage.py dispatch_organization_notifications --event-uuid <event-uuid>
python manage.py dispatch_legalization_work_notifications --event-uuid <event-uuid>
python manage.py reconcile_onboarding_handoffs --batch-size 200
python manage.py purge_candidate_import_data --limit 100
```

Health fails when no worker registered, the heartbeat is stale, or the failure threshold is reached.
The event-specific dispatch is the audited operator recovery path after correcting an exhausted delivery failure; it does not create another lifecycle event.
Portal-email retry is available only as the protected `OnboardingPortalDelivery` admin action; see `HYDRA_PORTAL_EMAIL.md`.

## Deployment and recovery

`entrypoint.sh` accepts only `HYDRA_PROCESS_ROLE=web` or `maintenance`:

- **web** performs deployment checks, committed migrations, static collection, readiness, then `exec`s Gunicorn;
- **maintenance** performs deploy checks and migration-drift verification, then `exec`s the worker. It never migrates the database.

Compose starts maintenance only after the web service is healthy. The worker has no published port, drops Linux capabilities, uses `no-new-privileges`, and mounts only private, outbox and quarantine volumes required for delivery and cleanup. Its container health check reads the database heartbeat.

Deploy and rollback scripts wait for database, ClamAV, web, and maintenance health. The backup script stops both database-writing Hydra processes before capturing the database and file archives, then waits for both to become healthy again. This preserves the cold recovery-point contract.

## Configuration

```text
HYDRA_NOTIFICATION_MAX_ATTEMPTS=10
HYDRA_MAINTENANCE_INTERVAL_SECONDS=30
HYDRA_MAINTENANCE_STALE_SECONDS=120
HYDRA_MAINTENANCE_PURGE_INTERVAL_SECONDS=3600
HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE=100
HYDRA_MAINTENANCE_NOTIFICATION_EMAIL_BATCH_SIZE=25
HYDRA_MAINTENANCE_DOCUMENT_BATCH_SIZE=100
HYDRA_MAINTENANCE_IMPORT_BATCH_SIZE=100
HYDRA_MAINTENANCE_LEGALIZATION_BATCH_SIZE=100
HYDRA_MAINTENANCE_ARRIVAL_BATCH_SIZE=100
HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE=100
HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE=100
HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE=25
HYDRA_MAINTENANCE_MAX_FAILURES=5
HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS=30,7,1
HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS=90,30,7
HYDRA_ARRIVAL_REMINDER_MINUTES=1440,120
HYDRA_IMPORT_PREVIEW_RETENTION_HOURS=72
HYDRA_IMPORT_APPLIED_RETENTION_HOURS=24
HYDRA_NOTIFICATION_BASE_URL=https://hydra.example.test/
HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS=60
HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS=3600
HYDRA_NOTIFICATION_EMAIL_LEASE_SECONDS=120
```

The complete portal-email timeout, backoff, lease, retention and attachment policy is documented in `HYDRA_PORTAL_EMAIL.md`; the separate internal generic notification-email contract is documented in `HYDRA_NOTIFICATIONS.md`.

Staging/production readiness rejects unbounded or inconsistent values: cycle 5–300 seconds, stale window at least twice the cycle, purge cadence no shorter than the cycle, all domain batches 1–1000, and positive failure/attempt limits.

## Verification

Focused PostgreSQL tests cover successful cycles, bounded organization/legalization-work notification and Housing-expiry batches/counters, heartbeat updates, portal-email dispatch counters, document/import purge cadence, non-sensitive error persistence, stale heartbeat, failure threshold, advisory-lock refusal, graceful one-cycle execution, and health-command failure. Integrated tests cover organization, legalization automation, responsibility/deputy, temporary Housing expiry and portal-email fail/commit/retry, document quarantine/deleted-file cleanup, and candidate-import redaction with append-only evidence.

The 2026-07-16 PostgreSQL 17 acceptance passed 21/21 portal-outbox tests, 24/24 worker/readiness tests, 43/43 combined import/worker/readiness tests, and 314/314 full Django tests after candidate-import retention and legalization renewal lineage were added. After legalization responsibility continuity was added, the focused continuity suite passed 11/11, the complete legalization module passed 52/52 and the full Django regression passed 325/325. After the Housing reservation/cancellation/atomic-move lifecycle was added, Housing passed 28/28, the wider housing/coordinator/report/readiness set passed 115/115, and a clean-database full Django regression passed 341/341. The later staging deploy/archive guards pass 6/6 offline tests and the complete `hydra_ops` set passes 30/30 on PostgreSQL. Universal tasks raised the clean regression to 408/408. After TASK-018 notification scope/state/email integration on 2026-07-17, focused notification/manifest tests pass 14/14, producer/maintenance regression passes 88/88 and the clean-database full regression passes 418/418. After TASK-020/021 hierarchy and temporary-hold expiry integration, focused Housing passes 39/39, the migration/backfill test passes 1/1, the cross-domain regression passes 96/96 and the complete PostgreSQL regression passes 431/431 with one environment-dependent skip. After TASK-024/025 immutable onboarding content and deterministic assignment rules, the focused onboarding suite passes 17/17, the cross-domain onboarding/arrival/readiness/timeline suite passes 48/48 and the clean PostgreSQL regression passes 448/448 with one environment-dependent skip. Earlier focused legalization and arrival runs remain recorded in their domain documents. Checks also verify migration drift, pending migrations, Python compilation, dependency consistency, YAML/PowerShell syntax, and `git diff --check`.

Manual production verification:

1. Start the stack and confirm both `/health/ready/` and `hydra_maintenance_health` pass.
2. Attempt a second `run_hydra_maintenance --once`; confirm it refuses the advisory lock.
3. Create failed organization-access and legalization responsibility/deputy notifications and confirm the worker retries them without another lifecycle event. Remove the responsibility/delegation before delivery and confirm the stale work event becomes `not_applicable`.
4. Age a non-production quarantine record, run a forced cycle, and confirm only the blob is purged while metadata remains.
5. Age non-production Ready and Applied candidate-import sessions, run a forced cycle, and confirm source values are redacted, Ready becomes Expired, Applied remains idempotent, and lifecycle evidence contains no personal data.
6. Stop maintenance; confirm its container becomes unhealthy after the configured stale window and monitoring alerts.
7. Run a cold backup and confirm both web and maintenance stop and return healthy.
8. Send SIGTERM and confirm the worker exits within the Compose grace period.

## Next production task

Run the target-host staging/restore/mobile and real-SMTP gates.
