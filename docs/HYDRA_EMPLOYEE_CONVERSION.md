# Hydra Person-to-Employee conversion

## Status

Task `032-employee-conversion.md` is implemented as a permissioned, PostgreSQL-backed vertical slice that creates or explicitly links one Horilla Employee without losing the Person/application history.

## Horilla reuse decision

The implementation **REUSES** Horilla `employee.Employee`, `EmployeeWorkInformation`, Django `User`, `Candidate.converted_employee_id`, Company, Department and JobPosition. It **EXTENDS** `hydra_people` with one append-only `EmployeeConversion` decision record and **WRAPS** all writes in one transaction service.

For the Hydra path, the unsafe Horilla behavior that derives a new account password from the employee phone is **REPLACED**. Hydra creates an inactive account with an unusable password. Account activation and credential delivery are separate controlled operations.

No parallel employee model was created.

## Workflow

An authorized operator opens the conversion action from a scoped Person. The form contains only active, hired applications linked to that Person and visible in the operator's company/person scope. The operator confirms:

- the hired application;
- the unique employee/account email;
- employee phone;
- joining date.

The service locks Person and Candidate rows, validates the complete decision and then either:

1. creates an inactive User, Employee and EmployeeWorkInformation; or
2. links the Employee already referenced explicitly by `Candidate.converted_employee_id`, without overwriting its fields.

The same transaction updates `Person.employee`, Person lifecycle, `Candidate.converted_employee_id`, Candidate converted state and the immutable conversion record. Repeating the same complete decision returns the existing Employee/record without creating duplicates. Conflicting Person and Candidate employee links are rejected and rolled back.

## Field ownership

| Target | Source/decision |
|---|---|
| Employee first/last name | canonical Person fields |
| Employee date of birth and gender | canonical Person fields |
| Employee/account email | explicit operator input |
| Employee phone | explicit operator input |
| Company | selected Candidate recruitment |
| Department and job position | selected Candidate job position |
| Joining date | explicit operator input |
| User activation | inactive, unusable password |

`source_snapshot` preserves the pre-conversion lifecycle/link state plus Person, Candidate, submitted and resulting Employee values. `field_decisions` records why each target value was chosen. The record rejects update and delete operations at both instance and queryset level.

## Permissions and scope

Conversion requires the dedicated `hydra_people.convert_person_to_employee` permission together with Person change, Candidate view/change and Employee/WorkInformation view/add permissions. The Person and Candidate must also pass the normal Hydra selectors. Changing the Person UUID or posting an out-of-scope Candidate returns no usable object.

Conversion history is exposed only with `hydra_people.view_employeeconversion` and only through the already-scoped Person detail.

## Existing Horilla paths

- The direct Horilla conversion action redirects a Hydra-linked Candidate to the controlled Hydra form, including HTMX requests.
- Unlinked legacy Candidates retain the original Horilla direct-conversion behavior.
- Completing the Horilla onboarding bank-details step synchronizes a linked Person through the same idempotent linking/audit service.

Hydra private Person/Candidate documents are not copied into generic Horilla public media during conversion.

## Verification

Focused PostgreSQL verification contains 14 tests for creation/mapping, inactive credentials, idempotency, hired-state enforcement, email collision, explicit existing-Employee linking, conflicting links, rollback, append-only history, onboarding synchronization, permission denial, direct-URL scope, scoped form choices and both linked/legacy Horilla conversion behavior.

The complete implemented Hydra suite passes:

```text
Ran 101 tests - OK
```

The browser journey was exercised in local Microsoft Edge/Chromium against the real PostgreSQL schema. It selected the one eligible hired QA application, created the Employee, returned to Person detail and verified lifecycle `Employee`, company, joining date, source, actor and inactive account. At 390 x 844 pixels the document width was 390 pixels, the conversion detail collapsed to one column, action buttons fit the viewport, and the browser reported no console errors or failed HTTP requests.

## Deliberate limits

- No account activation, password reset delivery or SSO provisioning is included.
- No contract, payroll, bank, housing or automatic team assignment is created during conversion. Team assignment is the separate, now-implemented task 033 workflow.
- Existing Employee values are not silently synchronized from Person after conversion.
- Conversion does not create attendance and does not redefine passport identity ownership.

Team assignment is documented in `docs/HYDRA_TEAM_ASSIGNMENT.md`. The next authoritative task is `040-brigadier-panel.md`.
