# Hydra employee team assignment

## Status

Task `033-team-assignment.md` is implemented as a scoped, transactional vertical slice for assigning a converted Hydra Person/Employee to the operational hierarchy.

## Reuse decision

The implementation **REUSES** Horilla `Company`, `Department`, `Employee` and `EmployeeWorkInformation`. It **EXTENDS** the existing Hydra `Location` → `Section` → `Team` hierarchy and effective-dated `PersonAssignment`. It **WRAPS** the Horilla work-information update inside the same transaction and permission boundary.

No parallel employee, department, team or assignment model was created. `PersonAssignment` remains the source of truth; Horilla work information is a compatibility projection for its existing employee screens.

## Workflow

For a Person already linked to an Employee, an authorized operator selects an in-scope active Team and an effective date. The server:

1. locks the Person, Team and overlapping primary assignments;
2. verifies Person visibility, target-Team scope and all action permissions;
3. derives Department, Company and Location from the selected Team hierarchy;
4. ends the previous primary assignment on the day before the new one, or marks a same-day record as replaced;
5. creates the new primary `PersonAssignment` with actor attribution;
6. synchronizes Horilla `EmployeeWorkInformation` in the same transaction.

Repeated submission of the same current assignment returns the existing record. History is never deleted. The Person detail shows Team, normalized Location, Department, validity interval and current/ended/replaced state.

The existing pre-employment Person assignment remains available. It is intentionally separate from employee synchronization because Hydra scope can be needed before conversion.

## Data synchronization

| Source of truth | Horilla projection |
|---|---|
| Team → Section → Location → Company | `EmployeeWorkInformation.company_id` |
| Team → Section → Department | `EmployeeWorkInformation.department_id` |
| normalized Hydra Location name | `EmployeeWorkInformation.location` |
| Hydra PersonAssignment | no Team field is added to Horilla |

If the existing Horilla JobPosition belongs to another Department, JobPosition and JobRole are cleared instead of retaining an invalid cross-department combination. Horilla simple-history records the work-information update and attributes it to the operator.

## Permissions and scope

The employee path requires:

- `hydra_people.view_person` and visibility through the normal Person selector;
- `hydra_coordination.add_personassignment`;
- `hydra_coordination.assign_person`;
- `employee.view_employee`;
- `employee.change_employeeworkinformation`;
- an active Hydra grant covering the target Team.

The form queryset is scoped, but the service independently repeats every authorization check. Posting an out-of-scope Team cannot bypass the boundary. A Team without a mapped Section Department and an unconverted Person are rejected.

## Migration

No schema migration is required. The task deliberately extends `PersonAssignment` from `hydra_coordination/migrations/0001_initial.py` and Horilla `EmployeeWorkInformation`; `makemigrations --check --dry-run` reports no changes.

## Verification

Focused PostgreSQL coverage contains 10 tests for reassignment history, Horilla synchronization, incompatible JobPosition cleanup, idempotency, missing work-information permission, out-of-scope targets, missing Department, unconverted Person, future dates, scoped form choices and direct form denial.

The complete implemented Hydra regression suite passes:

```text
Ran 106 tests - OK
```

`manage.py check`, Python compilation and migration-drift checks pass.

The browser journey was completed against the real PostgreSQL schema using the `hydra-qa` operator. At 390 × 844 pixels it moved Employee Person `e6ae2352-cb51-44bf-9b28-273683045fae` from Browser Team Alpha to Browser Team Beta, showed the success message, current Beta row and ended Alpha row, and synchronized Company, Department and Location in Horilla. The document width was 380 pixels for a 390-pixel viewport; the form and card-style history stayed inside the viewport. The tested Hydra assignment/detail URLs emitted no console warnings or errors. The initial upstream Horilla root page still emits its pre-existing `ReferenceError: c is not defined` before navigation into Hydra.

## Deliberate limits

- Employee team assignment is effective immediately or may be backdated. Future scheduling is rejected until a reliable due-assignment activation job exists.
- JobPosition/JobRole are not guessed for the new Department.
- Shift, reporting manager, contract and payroll data are outside this task.
- Translation catalogs for new strings are not populated yet.

Tasks `040-brigadier-panel.md` and `041-coordinator-panel.md` are implemented in `docs/HYDRA_BRIGADIER_PANEL.md` and `docs/HYDRA_COORDINATOR_PANEL.md`. The next authoritative task is `042-template-module.md`.
