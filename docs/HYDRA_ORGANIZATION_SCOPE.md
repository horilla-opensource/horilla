# Hydra organization scope — TASK-1

## Status and reuse decision

Implemented on 2026-07-14 as the second Hydra vertical slice.

| Concern | Decision | Rationale |
|---|---|---|
| Legal company | **REUSE** `base.Company` | It already owns Horilla company identity and address data. |
| Department | **REUSE** `base.Department` | Existing HR and employee relations remain authoritative. |
| Horilla selected company | **WRAP** for navigation only | `selected_company`, including `all`, is not an object-authorization boundary. |
| Location, section/stage and team | **NEW** `hydra_coordination` models | Horilla has no normalized physical/operational hierarchy for these levels. |
| Role actions | **REUSE** Django permissions/groups | Permissions answer which action is allowed. |
| Record scope | **NEW** effective-dated `ScopeGrant` | Grants answer on which company, department, location, section or team the action is allowed. |
| Person placement | **NEW** effective-dated `PersonAssignment` | Historical placement must exist before Employee conversion and cannot be stored in free-text work location. |
| Person access | **EXTEND** `hydra_people.selectors` | Every Person read now intersects model permission, active grants and current assignments. |

## Implemented vertical slice

The `hydra_coordination` app owns:

- `Location`, linked to one reused Horilla Company;
- `Section`, linked to one Location and optionally one reused Department;
- `Team`, linked to one Section;
- `ScopeGrant`, linked to a user and exactly one organization target, with validity dates;
- `PersonAssignment`, linking a Person to Team and Department with validity dates and a primary marker.

Database constraints enforce unique hierarchy codes/names, exactly one scope target and valid date intervals. Transactional services enforce permissions, grant containment, company consistency and non-overlapping active primary assignments. Admin registrations are read-only so operational writes use those services.

The server-rendered UI is available at `/hydra/coordination/organization/`. It provides the scoped hierarchy and creation forms for locations, sections, teams and grants. Person details show only assignment history visible to the actor and expose an assignment form when authorized.

## Authorization semantics

The effective Person queryset is:

`Django permission ∩ active date-valid grants ∩ current organization assignment`

A company grant contains its locations/sections/teams; a location grant contains its sections/teams; a section grant contains its teams; department and team grants match their respective assignment relations. An explicitly created but never assigned Person remains visible to its creator so the first assignment can be completed. Once assigned, normal scope applies. Only Django superusers have the explicit bypass.

Horilla's session value `selected_company=all` is deliberately ignored by Hydra selectors. Direct object URLs resolve through the same selector and return 404 when the object is outside scope. Write services independently re-check scope, so calling a service without a view cannot bypass authorization.

## Permissions

| Action | Required permission and scope |
|---|---|
| View hierarchy | `view_location` plus active grant; `view_section`/`view_team` reveal lower levels |
| Create hierarchy level | matching `add_*` permission plus a containing active grant |
| View Person | `hydra_people.view_person` plus matching active assignment/grant |
| Assign Person | `view_person`, `add_personassignment`, `assign_person`, visible Person and target Team scope |
| Grant scope | `add_scopegrant`; non-superusers may grant only a target and time interval contained by their own grant |

## Migration

`hydra_coordination/migrations/0001_initial.py` creates the five models and their constraints. It depends on the locally versioned `hydra_people.0001_initial` and generated Horilla `base.0002_initial` baseline. `.gitignore` explicitly retains Hydra coordination migrations while continuing to ignore generated upstream baseline migrations.

## Manual verification

1. Run the local PostgreSQL setup from `docs/LOCAL_DEVELOPMENT.md` and apply migrations.
2. Grant a coordinator the needed Django action permissions and a company/location/team `ScopeGrant`.
3. Open `/hydra/coordination/organization/`; confirm only the granted hierarchy is shown.
4. Open the page at 390 px width; confirm actions wrap and hierarchy/table content stays inside the viewport.
5. Create a Person, assign it to an in-scope Team, and confirm it appears in the Person list/detail.
6. Change the browser session company selector to `all`; confirm no additional Person or hierarchy becomes visible.
7. Paste an out-of-scope Person UUID into the detail URL; confirm HTTP 404.
8. Expire/deactivate the grant and confirm list, detail and write services deny access.

## Verification evidence

- all 27 discovered tests pass on PostgreSQL 17, including permission-without-scope, team A/team B isolation, direct URL manipulation, `selected_company=all`, expired grants, grant self-escalation, assignment overlap and every new form render;
- `manage.py check` and `makemigrations --check --dry-run` report no issues or model drift;
- `manage.py migrate --check`, Python compilation, `pip check` and `git diff --check` pass;
- PostgreSQL contains the five expected `hydra_coordination_*` tables and records `hydra_coordination.0001_initial` as applied;
- the local server health endpoint returned HTTP 200.

The required in-app browser check was attempted with a 390 × 844 viewport. The browser integration twice failed to attach a webview and exposed no recoverable tab, including after the documented fresh-tab and visible-webview recovery steps. The viewport and visibility overrides were reset. Server-side integration tests render the organization dashboard and all forms successfully, but the visual 390 px step remains a manual acceptance check rather than being reported as passed.

## Known limitations and next task

- The current UI creates grants and assignments but does not yet expose revoke/edit workflows; records remain manageable through future focused service-backed screens.
- Primary assignment overlap is enforced transactionally in the service for cross-database compatibility; all production write paths must continue to use it.
- A never-assigned Person is visible only to its creator (or superuser) until its first assignment.
- Translation catalogs for the new strings are not populated yet.
- Coordinator/brigadier operational dashboards, exports and reports are later tasks and must reuse these selectors rather than implement new scope logic.

Next: extend recruitment on top of the completed Hydra shell and organization boundary.
