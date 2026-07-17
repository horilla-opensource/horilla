# Hydra coordinator panel

## Status

Task `041-coordinator-panel.md` is implemented as a read-only, mobile-first operational exception dashboard for a coordinator's directly granted Locations.

The supplied `041-coordinator-panel (1).md` was mislabelled and repeated the already implemented candidate Excel import brief. The scope below follows `TARGET_ARCHITECTURE.md`, the accepted reuse matrix and the numerical delivery order.

## Reuse decision

The solution is **NEW + WRAP**. The dashboard is a new Hydra presentation/selector slice, while all business facts remain owned by existing modules:

- `hydra_arrivals.ArrivalPlan` owns planned, confirmed and no-show arrivals;
- `hydra_coordination.PersonAssignment` owns effective-dated Team membership;
- `hydra_legalization.LegalizationCase` owns workflow deadlines and validity;
- `hydra_housing.HousingAssignment` owns effective accommodation;
- `hydra_coordination.ScopeGrant` owns the authorization boundary;
- `hydra_tasks.HydraTask` owns universal operational work and its deadline.

No duplicate arrival, assignment, legalization, Person or Location model was created. The view is thin and delegates all composition and scope enforcement to `hydra_coordination.coordinator_selectors`.

## Scope and permissions

Access requires the five existing panel/domain permissions plus read permissions for all four Housing inventory/assignment models:

| Permission | Purpose |
|---|---|
| `hydra_coordination.view_coordinator_panel` | explicit access to the operational dashboard |
| `hydra_coordination.view_location` | Location identity visibility |
| `hydra_people.view_person` | scoped Person identity visibility |
| `hydra_arrivals.view_arrivalplan` | arrival-state visibility |
| `hydra_legalization.view_legalizationcase` | legalization-state visibility |
| `hydra_housing.view_housingfacility`, `view_housingroom`, `view_housingbed`, `view_housingassignment` | scoped housing inventory and occupancy visibility |

A normal user sees only active Locations named by current, direct `ScopeGrant.location` records. Company, Department, Section and Team grants do not open or widen this dashboard. The global company selector, including `selected_company=all`, is ignored. Superuser access is the explicit administrative bypass.

Unknown, malformed or out-of-scope `location` URL parameters return 404. The selector repeats the Location authorization check and raises `PermissionDenied`, so bypassing the form or view cannot expose another Location.

## Exception semantics

The selected operational day cannot be in the future. The dashboard composes five independently scoped exception lists:

1. **Arrival exceptions**: open planned arrivals overdue at the selected-day cutoff, plus no-shows scheduled for that day.
2. **Assignment gaps**: confirmed arrivals at the Location, arrived no later than the selected day, whose Person has no active primary Team assignment effective on that day.
3. **Housing gaps**: confirmed arrivals at the Location, arrived no later than the selected day, whose Person has no active Housing assignment at that Location effective on that day.
4. **Legalization attention**: cases for Persons with an active primary assignment in the Location, covering missing or overdue workflow deadlines, deadlines within 30 days, missing approved validity, validity ending within 30 days and expired validity.
5. **Overdue tasks**: open/in-progress universal tasks whose Person has a current primary assignment at the Location and whose Company matches it. This section is omitted unless the coordinator separately holds task-view permission.

The summary counters show arrivals scheduled on the day and the full count of each exception group. Each detailed list is capped at 25 rows to keep the operational page bounded and mobile-friendly.

The dashboard highlights review work only. It does not change arrival outcomes, create Team assignments, transition legalization cases or make final HR/legal decisions.

## Migration

`hydra_coordination/migrations/0003_alter_location_options.py` adds the custom `view_coordinator_panel` permission while preserving Location ordering. No domain table or business field is added.

## Verification

Focused PostgreSQL coverage contains 10 tests for direct current Location grants, expired grants, composed cross-domain exceptions, selector re-authorization, URL tampering, company `all`, broad Company grants, missing permissions, future dates and malformed identifiers.

The complete implemented Hydra regression passes:

```text
Ran 190 tests - OK
```

`manage.py check`, `makemigrations --check --dry-run` and `migrate --check` pass.

The original browser journey was completed against the real PostgreSQL schema using the `hydra-qa` operator. At 390 x 844 pixels it exposed only direct-granted Browser Location A despite broader Company and Team grants, rendered the arrival/assignment/legalization exceptions and kept the active Coordinator navigation state. The document width was 380 pixels for the 390-pixel viewport and the tested page emitted no console warnings or errors. Direct navigation to `?location=2` returned 404. Housing integration is additionally covered by the current full regression and the dedicated 390 px Housing journey documented in `HYDRA_HOUSING.md`.

## Deliberate limits

- The panel is read-only; all mutations remain in their owning modules.
- Legalization is mapped only through an effective primary Team assignment, avoiding guesses for unassigned Persons.
- Housing mutations remain in the Housing module; this panel provides the authorized assignment link only when the actor has its write permission.
- Task transitions remain in `hydra_tasks`; the panel shows only a permission-aware link and never broadens the base coordinator role.
- The scoped operational report and audited CSV export are implemented in task `044-reports.md`.
- Translation catalogs for new strings are not populated yet.

Tasks 042-045 are now implemented; see `HYDRA_TEMPLATES.md`, `HYDRA_PUBLIC_LINKS.md`, `HYDRA_REPORTS.md`, and `HYDRA_STAGING.md`.
