# Hydra controlled onboarding handoff

## Status and reuse decision

The production decision is **EXTEND + WRAP**. Hydra reuses Horilla
`OnboardingStage`, `OnboardingTask`, `CandidateStage`, `CandidateTask` and the
token portal. It does not create a parallel onboarding engine. Hydra adds a
scoped, transactional handoff around the boundary between a confirmed arrival,
the reused onboarding records, Person-to-Employee conversion and the current
destination Team assignment.

The handoff is not a replacement for arrival, recruitment, employee or team
history. It is the confirmation trail that proves those independently owned
facts were connected for one application.

## Controlled flow

1. The arrival must be `confirmed`, with an actual arrival timestamp.
2. The linked Horilla application must be active, not cancelled and genuinely
   in a recruitment stage whose type is `hired`.
3. An authorized, in-scope operator starts the handoff from the arrival detail.
4. `onboarding.services.ensure_candidate_onboarding` locks the Candidate,
   creates/reuses its first configured `CandidateStage`, and assigns every
   configured recruitment task with the task's real stage.
5. The Person enters lifecycle state `onboarding` unless it is already an
   Employee. The Candidate `start_onboard` flag is changed only after the
   onboarding rows are valid.
6. Existing Hydra conversion and Team-assignment services reconcile the
   handoff in the same database transaction.
7. The handoff reaches `completed` only when conversion exists, a current
   primary Team assignment matches the arrival destination, and every assigned
   CandidateTask is `done`.

The state sequence is:

```text
started -> converted -> assigned (tasks pending) -> completed
```

Repeated start, conversion, assignment, task update and reconciliation calls
are idempotent. One application/arrival has one handoff, while one Person may
have separate handoffs for later applications. An existing Employee conversion
may satisfy a later application without creating another employee identity.

## Data and audit

`hydra_arrivals.OnboardingHandoff` protects the source arrival, Person,
Candidate and CandidateStage. Optional conversion and assignment references are
attached only through reconciliation. Database checks enforce the allowed
state/reference shapes, and `PROTECT` prevents removal of evidence.

`OnboardingHandoffEvent` is append-only and records these unique milestones:

- handoff started;
- employee conversion recorded;
- destination Team assignment recorded;
- handoff completed.

Each event records user/system source, actor rules, referenced milestone rows,
opaque identifiers and the task total/completed count. Event update and delete
are rejected by both model/queryset behavior and database constraints. Horilla
CandidateTask history remains the detailed task-status audit.

No Person name, email, transport reference or task title is placed in Hydra
notification verbs. Configured stage/task managers receive the generic local
notification only when they are active, hold the handoff permission and can
still access the destination arrival through current Hydra scope.

## Authorization and scope

Starting a handoff requires the complete arrival/Person/Candidate read boundary,
the dedicated `hydra_arrivals.initiate_onboardinghandoff` permission, Person and
Candidate change permissions, and the underlying Horilla onboarding view/add
permissions. A generic Django permission never widens location scope.

Task changes require:

- current visibility of the source arrival;
- `hydra_arrivals.view_onboardinghandoff`;
- Horilla CandidateTask view/change permissions;
- assignment as manager of the task or current onboarding stage (or
  superuser).

Hydra task updates are CSRF-protected POST operations. The old Horilla GET
mutation and bulk update return 405/409 for a Hydra handoff task, so they cannot
bypass destination scope, task-manager assignment or completion immutability.
Direct out-of-scope arrival URLs remain 404.

## Horilla defects repaired

- Candidate detail GET no longer creates onboarding state as a side effect.
- The invalid `OnboardingTask.recruitment_id` lookup was removed; task
  assignment uses `stage_id__recruitment_id` through the locked service.
- Portal email queue/failure no longer sets `Candidate.start_onboard` or
  creates stage/task rows.
- Confirmed worker delivery uses the same idempotent onboarding service; an
  onboarding-data conflict is reconciled without resending the email.
- The portal-mail and fallback error templates now correctly load the Django
  `i18n` tag library.

Portal mail remains operator-triggered, but SMTP is now asynchronous through
the durable, leased and auditable outbox documented in
`HYDRA_PORTAL_EMAIL.md`. The web request commits the exact token/payload and
returns immediately. Bounded retries, dead-letter recovery, attachment
scanning/private storage, redacted legacy logs and payload retention are part
of that boundary.

## Recovery and operations

Conversion and employee Team assignment reconcile immediately. The
single-owner maintenance worker also calls a bounded recovery scan so a
committed legacy/manual update cannot leave an open handoff stale indefinitely.

```text
python manage.py reconcile_onboarding_handoffs --batch-size 200
```

Configuration:

```text
HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE=100
HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE=25
```

Staging/production readiness requires a value from 1 to 1000. Maintenance
heartbeat state records the last successful onboarding reconciliation. A bad
record produces only an exception-class alarm and is never silently deleted or
merged.

## Migrations

- `hydra_arrivals/0003` creates handoff/event evidence and constraints;
- `hydra_arrivals/0004` permits multiple application handoffs per Person and
  reuse of existing conversion/assignment facts;
- `hydra_arrivals/0005` adds the explicit assigned/tasks-pending state;
- `hydra_arrivals/0006` adds the portal delivery outbox, retained attachments
  and append-only delivery events;
- `hydra_ops/0004` records the maintenance reconciliation timestamp;
- `hydra_ops/0005` records the portal-email dispatch timestamp.

## Verification

PostgreSQL-focused handoff coverage contains 14 tests for confirmed/hired
preconditions, complete permission and location denial, transactional rollback
on duplicate tasks, idempotency, multiple applications, non-sensitive
notifications, append-only events, destination-Team matching, conversion and
task completion, immutable completion, recovery batching, scoped UI, blocked
legacy mutation routes, queued/successful portal delivery and failed-mail
retry without premature onboarding. Dedicated outbox coverage is listed in
`HYDRA_PORTAL_EMAIL.md`.

The wider onboarding/arrival/conversion/team/worker integration run passed
79/79 tests. The 2026-07-16 outbox suite passed 21/21 and the complete current
PostgreSQL regression passed 296/296. Target-host evidence remains tracked in
`HYDRA_STAGING.md`.

## Manual acceptance still required

1. On a narrow mobile viewport, confirm the milestone and task tables collapse
   without horizontal overflow and each task form remains usable.
2. As a task manager with Location scope, complete a task; verify a generic
   notification, CandidateTask audit history and the final handoff event.
3. Repeat with another Location and verify list/direct URL/task POST denial.
4. Stop the maintenance worker, create an open milestone through a reviewed
   legacy path, restart the worker and verify bounded reconciliation.
5. Complete every real-SMTP, retry, dead-letter, ClamAV and crash-window gate in
   `HYDRA_PORTAL_EMAIL.md`; no failed attempt may mark onboarding started.
