# Hydra brigadier panel

## Status

Task `040-brigadier-panel.md` is implemented as a read-only, mobile-first operational view for a brigadier's directly granted Teams and hardened on 2026-07-15 with attendance/leave/shift reconciliation.

## Reuse decision

The panel **EXTENDS** the Hydra coordination layer and **WRAPS** existing legacy HR platform attendance data. It reuses:

- Hydra `Team`, effective-dated `PersonAssignment` and `ScopeGrant` for roster membership and authorization;
- Hydra `Person` and its controlled Employee link;
- legacy HR platform `Employee`, `Attendance`, late/early markers, approved `LeaveRequest`, and `EmployeeShiftSchedule` for the selected day's operational state.

No parallel attendance, absence, Employee or Team model was created. The new code is a thin selector/view/template slice in `hydra_coordination`.

## Scope and permission boundary

Access requires all five permissions:

| Permission | Purpose |
|---|---|
| `hydra_coordination.view_brigadier_panel` | explicit access to the operational panel |
| `hydra_people.view_person` | identity/roster visibility |
| `employee.view_employee` | linked Employee visibility |
| `attendance.view_attendance` | attendance-state visibility |
| `leave.view_leaverequest` | approved-leave visibility required for reconciliation |

For a normal user, the Team chooser and every roster query use only active, current `ScopeGrant` records whose object is that exact Team. Company, Location, Section and Department grants never widen this panel. The global company selector, including `all`, does not affect the result. Superuser access remains an explicit administrative bypass.

An unknown or out-of-scope `team` URL parameter returns 404. The selector repeats the Team authorization check, so bypassing the form or view cannot expose another Team.

## Roster and exception semantics

The roster is built from primary `PersonAssignment` records effective on the selected day. It includes only active Persons linked to active Employees whose employment interval covers that day. Search is applied after Team scope and matches names or the readable Hydra identifier.

The panel composes these read-only states:

- missing expected attendance only when the employee is scheduled and not on approved full-day leave;
- approved full-day or partial-day leave;
- no assigned shift and an unscheduled day;
- attendance during approved full-day leave or outside the assigned schedule;
- overlapping approved-leave records;
- missing clock-in;
- currently at work;
- completed attendance;
- pending validation;
- late arrival;
- early departure.

The shift currently stored in `EmployeeWorkInformation` is authoritative, including legacy HR platform's applied shift changes and rotations. A matching active weekday schedule establishes the work expectation. No schedule for an assigned shift means a legitimate unscheduled day; no shift assignment is a configuration exception. Full-day approved leave removes the attendance expectation, while partial leave preserves it. First-half leave suppresses a late-arrival marker and second-half leave suppresses an early-departure marker because those observations are expected for the approved portion.

This remains a read-only operational interpretation. It never writes, validates, rejects, or fabricates attendance or leave records.

The selected date cannot be in the future. Results are paginated at 50 employees per page.

## Migration

`hydra_coordination/migrations/0002_alter_team_options.py` adds the custom `view_brigadier_panel` permission while preserving Team ordering. No domain table is added.

## Verification

Focused PostgreSQL coverage contains 18 tests for direct-Team scoping, permission composition, scheduled missing attendance, full/partial approved leave, late/early suppression, missing shift configuration, unscheduled days, attendance/leave and attendance/schedule conflicts, exception counts, URL tampering, company `all`, broad Company grants, future dates and scoped search.

The complete implemented Hydra regression passes:

```text
Ran 240 tests - OK
```

`manage.py check`, `makemigrations --check --dry-run` and `migrate --check` pass. The local HTTP endpoint responds and redirects unauthenticated requests to login. Automated 390 x 844 browser navigation was not accepted in this desktop run because the browser retained its initial connection-error data page and its URL policy then blocked a retry; no browser screenshot is claimed.

## Deliberate limits

- The panel is read-only; attendance correction and validation remain in legacy HR platform.
- It reports operational inconsistencies but does not decide payroll, discipline, or legal absence.
- It does not expose Company/Location-wide coordinator scope.
- It does not include reports, exports or mutation actions.

Task `041-coordinator-panel.md` is implemented in `docs/HYDRA_COORDINATOR_PANEL.md`. The next authoritative task is `042-template-module.md`.
