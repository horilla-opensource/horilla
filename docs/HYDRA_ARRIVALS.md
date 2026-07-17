# Hydra arrivals

## Status

Task `030-arrivals.md` is implemented as the smallest location-scoped vertical slice for planning an arrival and recording either confirmation or no-show. It was hardened on 2026-07-15 with durable reminders and location-scoped overdue escalation owned by the production maintenance worker. The module is server-rendered, mobile-first and verified against PostgreSQL.

## Horilla reuse decision

The decision is **NEW MODULE** for the arrival domain.

- **REUSE** `hydra_people.Person`, the linked Horilla `recruitment.Candidate`, Django users and `hydra_coordination.Location`/`ScopeGrant`.
- **WRAP** every read in arrival selectors and every mutation in transactional arrival services.
- Leave Horilla `Candidate.joining_date`, onboarding and attendance unchanged. A pre-employment journey and pickup event is not an employment start date or an attendance fact.

This boundary avoids three common errors: treating travel date as employment date, granting a coordinator broad recruitment access, and allowing competing confirmation/no-show writes.

## Implemented domain

`ArrivalPlan` records:

- the Person and linked recruitment application;
- destination location and assigned coordinator;
- planned arrival time, transport type, reference and pickup point;
- `planned`, `confirmed` or `no_show` status;
- the actual arrival time or normalized no-show reason.

`ArrivalStatusHistory` is append-only. Creation writes the initial `planned` event; each terminal transition writes the actor, time and optional reason in the same database transaction.

There can be only one active `planned` arrival for a recruitment application. Terminal records remain as history and cannot be edited through the planning form.

`ArrivalAutomationEvent` is an append-only outbox/audit fact for upcoming and overdue notifications. Its unique key includes the plan, planned-time snapshot, threshold and recipient, making repeated worker cycles idempotent while still allowing a changed plan time or coordinator to create the correct new event. Only delivery status, attempt count, bounded error code and notification relation are mutable.

## Authorization and scope

Access requires the relevant Django model permission and current Hydra scope. Normal users see arrival plans only for locations covered by a direct current company or location grant. A team, section or department grant does not implicitly disclose every arrival at that location.

Direct object URLs use the same scoped selector as the list and return `404` outside scope. Creating or moving a plan validates destination scope, Person/application linkage and company consistency. Assigning another coordinator requires the dedicated assignment permission; that coordinator must also have the required arrival permissions and direct scope for the destination.

Transitions are limited to:

- `planned -> confirmed`;
- `planned -> no_show` after the planned time, with a required reason.

Repeating the same terminal transition is idempotent. Attempting the opposite terminal transition is rejected. Row locks serialize transition races.

Routine reminders go only to the current coordinator at the nearest crossed configured threshold (defaults: 24 hours and 2 hours). Overdue plans notify the current coordinator plus active users with `receive_arrival_escalations`, transition permission, the complete arrival view permission set and current Company/Location scope covering the destination. Delivery repeats scope, status, planned-time and coordinator checks; a confirmed, no-show, rescheduled, reassigned or newly inaccessible event becomes `not_applicable` without sending.

The worker never infers or writes `no_show`. An overdue plan remains `planned` until an authorized operator records confirmation or a reasoned no-show outcome.

Operators can run one bounded diagnostic/backfill cycle and recover a specific exhausted delivery after correcting the notification backend:

```text
python manage.py run_arrival_automation --limit 100
python manage.py run_arrival_automation --at 2026-07-15T10:00:00+02:00 --limit 100
python manage.py dispatch_arrival_notifications --event-uuid <event-uuid>
```

Future diagnostic timestamps are rejected. Notification verbs contain no Person name, transport reference, pickup point or other personal data.

## User interface

The Hydra shell contains an **Arrivals** entry for authorized users. The coordinator list provides the current queue, daily counters and filters. A Person page links to arrival planning when the user has the complete permission set. Detail pages expose planning data, the outcome form and immutable status history without relying on a broad Horilla recruitment view.

Templates use the existing Hydra responsive shell. Tables collapse into card rows at narrow widths and forms use a single-column mobile layout.

## Verification

Acceptance was run with the real PostgreSQL schema:

```text
python manage.py test hydra_people hydra_coordination hydra_shell hydra_documents hydra_legalization hydra_imports hydra_arrivals --keepdb
Ran 87 tests - OK
```

The original 14 focused arrival tests cover missing permissions, list and direct-URL isolation, team-grant non-expansion, out-of-scope form data, coordinator assignment, normalization and history, Person/application/company consistency, the single-planned constraint, terminal edit denial, idempotent confirmation, no-show rules, conflicting terminal outcomes and append-only history. The 2026-07-15 arrival/worker acceptance run passed 41/41 tests, adding threshold catch-up, duplicate prevention, location-scoped escalation, stale-event invalidation, non-sensitive failure evidence, exhausted-attempt recovery, append-only automation facts, command validation, readiness policy and bounded worker integration. The complete current PostgreSQL regression passed 296/296 after the controlled onboarding, durable portal-email integration and authority-evidence legalization workflow.

Operational checks include `manage.py check`, migration drift detection, pending-migration detection, bytecode compilation, dependency consistency and whitespace validation.

The browser journey was also exercised in local Microsoft Edge/Chromium against the running PostgreSQL-backed application: login, plan creation, detail display, `planned -> confirmed`, automatic actual-arrival time and two immutable history rows. At 390 x 844 pixels the detail and queue had no horizontal overflow, queue/history rows rendered as cards, the filter grid collapsed to one column and **Arrivals** was the single active Hydra navigation item.

The inherited Horilla shell still reports tracking-prevention warnings for third-party CDN scripts and requests its unconfigured `/media/images/ui/company.png` placeholder. These pre-existing shell assets did not affect the arrival journey and are not introduced by `hydra_arrivals`.

## Deliberate limits

- This task does not ingest live transport data or automatically decide no-show outcomes.
- It does not convert a Person into an Employee or create attendance.
- It does not implement bulk planning, route optimization or a generic workflow engine.
- Broader coordinator dashboards belong to task `041-coordinator-panel.md`.

The controlled onboarding handoff and confirmation trail are implemented in `HYDRA_ONBOARDING.md`. Arrival remains the source fact and never automatically marks a Candidate hired, creates an Employee, chooses a Team or completes a task.
