# Hydra housing lifecycle

## Status and reuse decision

Tasks `020-implement-housing-hierarchy.md`, `021-implement-reservations.md` and the already completed assignment/move boundary are implemented as the `hydra_housing` Django app. The production extension adds optional formal building/floor structure and expiring temporary holds with renewal/confirmation to the existing Location-scoped inventory and effective-dated occupancy lifecycle.

The solution is **EXTEND + WRAP**:

- `hydra_people.Person` remains the canonical person identity;
- `hydra_coordination.Location` remains the physical-site and authorization anchor;
- existing `ScopeGrant` records and Hydra Person selectors remain the access boundary;
- legacy HR platform audit fields record creation and modification actors, while Hydra owns immutable housing lifecycle facts;
- Housing owns only facilities, optional buildings/floors, rooms, beds and accommodation periods. It does not duplicate Company, Location, Team or employee work information.

## Domain model

- `HousingFacility`: one named, addressed accommodation object at one Location;
- `HousingBuilding`: an optional named structure inside a facility;
- `HousingFloor`: an ordered floor inside a building;
- `HousingRoom`: a room within a facility, optionally linked to a formal floor. The redundant Facility anchor is retained for stable scope and existing references; validation/readiness require a linked floor to belong to the same Facility;
- `HousingBed`: a uniquely labelled bed within a room;
- `HousingAssignment`: a Person-to-bed period with inclusive `valid_from` and optional `valid_until` dates. A future active start is a reservation. Optional `reservation_expires_at` makes it a temporary hold; an unconfirmed hold never counts as current occupancy;
- `HousingAssignmentEvent`: append-only `assigned`, `reserved`, `renewed`, `confirmed`, `expired`, `ended`, `cancelled`, `moved_out` and `moved_in` evidence with effective date, reason, actor/source and an optional protected related assignment.

Facility names are unique inside a Location, room names inside a facility and bed labels inside a room. Invalid date ranges are rejected by model validation and a database check. Open-ended active assignments have database uniqueness constraints for both Person and bed. The service also rejects every inclusive overlap, including finite periods.

Migration `hydra_housing.0002` creates the event model and dedicated permissions. Its bounded data migration gives every existing assignment exactly one non-notifying system origin event. Existing inactive or already ended periods also receive a system terminal baseline without inventing a human actor. Migration `0003_housing_hierarchy_reservations` adds Building/Floor and temporary expiry. Existing non-empty free-text floor labels are preserved and deterministically grouped below a visibly named `Legacy building` placeholder per Facility; blank labels remain unstructured rather than inventing facts. Migration `0004_housing_reservation_event_constraints` extends terminal uniqueness to expiry and permits only one confirmation event per assignment.

## Reservation, move and conflict policy

All supported writes use services inside `transaction.atomic`:

1. Person and bed rows are locked in deterministic order;
2. permissions, Location scope and active inventory are rechecked after locking;
3. the Person must be visible through the canonical selector and have an effective Team assignment, a confirmed arrival, or -- only for a future reservation -- a planned arrival no later than the reservation start at the facility Location;
4. every active Person/bed overlap rejects the complete transaction;
5. the actor and immutable origin/terminal events are recorded in the same commit.

A temporary hold must expire in the future and no later than midnight at its scheduled start. It can be extended only forward with the dedicated renewal permission, or confirmed to remove the expiry while preserving the same protected Person/bed period. Both operations require a reason and are idempotent for identical retries. Due holds are locked, deactivated and given exactly one system `expired` event by the single-owner maintenance worker. They never become current occupancy before confirmation. Overdue active holds fail readiness, so a stopped maintenance worker cannot silently turn a temporary hold into a stay.

Locking Person serializes attempts to place one Person in different beds. Locking each bed serializes attempts to place different people in the same bed. Adjacent periods are supported when the earlier `valid_until` is the day before the next `valid_from`.

Reservation cancellation narrows `is_active` and never deletes the row. An already expired hold cannot be cancelled, renewed, confirmed or moved. A move locks Person, the source assignment and both beds and preserves an unexpired temporary deadline on the destination. It either shortens/deactivates the source, creates the destination and records both linked move events, or rolls the complete operation back. Identical cancellation, renewal, confirmation, end and move retries are idempotent; changed retry facts are rejected.

`HousingAssignment` blocks core-fact rewrites, lifecycle changes outside the service, queryset update/delete and reactivation. `HousingAssignmentEvent` blocks every update/delete path. Read-only admin querysets are scope-filtered; a staff account cannot bypass Location scope through admin. Superuser remains the explicit global bypass.

## Scope and permissions

Housing reads require all of:

- `hydra_housing.view_housingfacility`;
- `hydra_housing.view_housingroom`;
- `hydra_housing.view_housingbed`;
- `hydra_housing.view_housingassignment`;
- `hydra_coordination.view_location`;
- `hydra_people.view_person`.

Normal users see facilities only at Locations covered by a current direct Company or Location grant. Department, Section and Team grants do not widen facility inventory. Direct facility, room, bed and assignment URLs use the same selectors and return 404 outside scope.

Sensitive actions are separated:

- `add_housingassignment` creates a current/past period;
- `reserve_housingassignment` is additionally required for a future period;
- `renew_housingreservation` plus reserve/change permissions extends a live temporary hold;
- `confirm_housingreservation` plus reserve/change permissions converts a live temporary hold to a confirmed reservation;
- `cancel_housingreservation` plus `change_housingassignment` cancels a reservation;
- `move_housingassignment` plus assignment add/change permissions records a move; a future move also requires reservation permission;
- `view_housingassignmentevent` exposes the scoped audit trail.

## Operator routes and integration

- `/hydra/housing/` -- scoped inventory, current occupants and upcoming reservations;
- `/hydra/housing/facilities/create/` -- facility creation;
- `/hydra/housing/facilities/<uuid>/` -- current occupancy and nearest future reservation per bed;
- `/hydra/housing/facilities/<uuid>/buildings/create/` -- scoped building creation;
- `/hydra/housing/buildings/<uuid>/floors/create/` -- scoped floor creation;
- `/hydra/housing/facilities/<uuid>/rooms/create/` -- room creation;
- `/hydra/housing/rooms/<uuid>/beds/create/` -- bed creation;
- `/hydra/housing/people/<uuid>/assign/` -- effective-dated assignment or reservation;
- `/hydra/housing/assignments/<uuid>/end/` -- reasoned end-of-stay transition;
- `/hydra/housing/assignments/<uuid>/move/` -- atomic current or scheduled move;
- `/hydra/housing/reservations/<uuid>/cancel/` -- reasoned future-reservation cancellation.
- `/hydra/housing/reservations/<uuid>/renew/` -- reasoned forward-only temporary-hold renewal;
- `/hydra/housing/reservations/<uuid>/confirm/` -- reasoned temporary-hold confirmation.

Person detail shows scoped housing history, authorized actions and append-only audit. The coordinator panel reports a Housing gap when a confirmed arrival has no effective assignment/reservation at its destination on the selected day. The operational report adds current facility/room/bed data, a missing-housing attention filter and stable CSV columns:

```text
HOUSING_FACILITY
HOUSING_ROOM
HOUSING_BED
HOUSING_VALID_FROM
HOUSING_VALID_UNTIL
```

Both integrations use scoped selectors. Scheduled reservations count for their effective day; neither integration reads an unscoped manager as an authorization boundary.

Production readiness checks active interval overlap independently for Person and bed, an origin event for every assignment, terminal-event/state consistency, cross-Facility floor links, overdue temporary holds and confirmed rows that still retain an expiry. This detects historical or direct-database corruption that service locks alone cannot prevent. Maintenance processes at most `HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE` holds per cycle and records `last_housing_run_at` in the single-owner heartbeat row.

## Verification

The PostgreSQL functional Housing suite passes **39/39**, and the separate actual `0001 -> 0004` migration/backfill test passes **1/1**. It covers original scope/conflict behavior plus:

- dedicated reservation/move/cancel permissions;
- planned-arrival reservation eligibility;
- cancellation and move idempotency;
- atomic current and scheduled moves;
- complete rollback on destination conflict;
- cross-Location service and admin denial;
- immutable assignments and events;
- readiness corruption detection;
- formal Building/Floor creation, invalid hierarchy and cross-scope denial;
- temporary hold validation, renewal, confirmation, system expiry and UI actions;
- an actual `0001 -> 0004` migration/backfill cycle.

The clean-database Housing/maintenance/readiness/coordinator/report/timeline regression passes **96/96**. The clean-database run is intentional: targeted migration tests use `TransactionTestCase`, whose flush removes rows created by data migrations from a reused `--keepdb` database even though the schema remains valid.

After the hierarchy and temporary-reservation extension, the complete PostgreSQL Django regression passes **431/431** with one environment-dependent test skipped. The reviewed migration manifest covers **73** migration source files.

The browser journey was completed against PostgreSQL with the `hydra-qa` operator in Microsoft Edge (Chromium). It covered a current atomic move, a future reservation and cancellation, scoped Person/facility audit evidence, desktop layout and 390 x 844 mobile layout. The dashboard, facility, move and cancellation pages had no horizontal document overflow. A pre-existing ordinary-dashboard `ReferenceError` was traced to unconditional birthday-canvas animation, guarded when the canvas is absent, and rechecked with zero JavaScript exceptions and zero console errors.

The 2026-07-17 hierarchy/temporary-hold browser journey added a Building, Floor and structured Room, verified a cross-Location rejection, then created, renewed and confirmed an eligible temporary hold. The final reservation was `Scheduled` with no expiry, both reasoned events remained visible, and the Housing dashboard, Facility and Person views had no horizontal overflow at 390 x 844 with an empty browser console.

Run:

```powershell
python manage.py test hydra_housing
python manage.py test hydra_housing hydra_coordination hydra_reports hydra_ops.tests.test_readiness
python manage.py test --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
```

## Manual verification

1. Grant a housing operator the complete read boundary, inventory add permissions, add/change assignment, reservation, renewal, confirmation, cancellation, move and event-view permissions plus one direct Location grant.
2. Create a Building, Floor, Room and Bed; verify the formal hierarchy appears on Facility and Person views and a floor from another Facility is rejected.
3. Reserve a bed with an expiry for a planned arrival; verify it appears as a temporary hold but never as a current occupant.
4. Renew the hold forward, then confirm it; verify the deadline is removed and both reasoned events remain append-only.
5. Let another hold expire through `run_hydra_maintenance --once`; verify it becomes inactive with one system event and releases conflict protection.
6. Attempt the same Person and same bed period concurrently; confirm exactly one transaction succeeds.
7. Move a current occupant and a scheduled reservation; confirm the source/destination periods, paired events and readiness checks.
8. Repeat list, direct UUID and admin requests from another Location; confirm no foreign facility, hierarchy, assignment or event appears.
9. Verify Housing, facility detail, Person detail, renew/confirm/cancel and move forms at desktop and no wider than 390 px.

## Remaining limits

- Dates are day-granular. A current stay can move today only if its source period started before today; rewriting two beds inside the first recorded day would fabricate ordering the schema cannot represent. A future reservation may move on its original start date because occupancy has not begun.
- Building/Floor is optional because historical rooms may not have enough trustworthy information. `Legacy building` is an explicit migration placeholder, not a claim about a real building; an operator should rename it after verification.
- Inventory edits/deactivation and bulk moves are not exposed. A bulk move requires a reviewed batch/idempotency contract and must not loop through the single-row service with partial success.
- Pricing, rent, deposits, inspections, maintenance, guests and landlord contracts remain outside the original workforce-accommodation scope.
- Housing is internal operator functionality; there is no candidate self-service accommodation portal.
- Translation catalogs for new strings still require the project-wide localization pass.
