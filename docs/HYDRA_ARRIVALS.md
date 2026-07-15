# Hydra arrivals

## Status

Task `030-arrivals.md` is implemented as the smallest location-scoped vertical slice for planning an arrival and recording either confirmation or no-show. The module is server-rendered, mobile-first and verified against PostgreSQL.

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

## Authorization and scope

Access requires the relevant Django model permission and current Hydra scope. Normal users see arrival plans only for locations covered by a direct current company or location grant. A team, section or department grant does not implicitly disclose every arrival at that location.

Direct object URLs use the same scoped selector as the list and return `404` outside scope. Creating or moving a plan validates destination scope, Person/application linkage and company consistency. Assigning another coordinator requires the dedicated assignment permission; that coordinator must also have the required arrival permissions and direct scope for the destination.

Transitions are limited to:

- `planned -> confirmed`;
- `planned -> no_show` after the planned time, with a required reason.

Repeating the same terminal transition is idempotent. Attempting the opposite terminal transition is rejected. Row locks serialize transition races.

## User interface

The Hydra shell contains an **Arrivals** entry for authorized users. The coordinator list provides the current queue, daily counters and filters. A Person page links to arrival planning when the user has the complete permission set. Detail pages expose planning data, the outcome form and immutable status history without relying on a broad Horilla recruitment view.

Templates use the existing Hydra responsive shell. Tables collapse into card rows at narrow widths and forms use a single-column mobile layout.

## Verification

Acceptance was run with the real PostgreSQL schema:

```text
python manage.py test hydra_people hydra_coordination hydra_shell hydra_documents hydra_legalization hydra_imports hydra_arrivals --keepdb
Ran 87 tests - OK
```

The 14 focused arrival tests cover missing permissions, list and direct-URL isolation, team-grant non-expansion, out-of-scope form data, coordinator assignment, normalization and history, Person/application/company consistency, the single-planned constraint, terminal edit denial, idempotent confirmation, no-show rules, conflicting terminal outcomes and append-only history. A regression test also confirms the original Horilla onboarding candidate view still responds.

Operational checks include `manage.py check`, migration drift detection, pending-migration detection, bytecode compilation, dependency consistency and whitespace validation.

The browser journey was also exercised in local Microsoft Edge/Chromium against the running PostgreSQL-backed application: login, plan creation, detail display, `planned -> confirmed`, automatic actual-arrival time and two immutable history rows. At 390 x 844 pixels the detail and queue had no horizontal overflow, queue/history rows rendered as cards, the filter grid collapsed to one column and **Arrivals** was the single active Hydra navigation item.

The inherited Horilla shell still reports tracking-prevention warnings for third-party CDN scripts and requests its unconfigured `/media/images/ui/company.png` placeholder. These pre-existing shell assets did not affect the arrival journey and are not introduced by `hydra_arrivals`.

## Deliberate limits

- This task does not send notifications or ingest live transport data.
- It does not convert a Person into an Employee or create attendance.
- It does not implement bulk planning, route optimization or a generic workflow engine.
- Broader coordinator dashboards belong to task `041-coordinator-panel.md`.

The next authoritative task is `032-employee-conversion.md`.
