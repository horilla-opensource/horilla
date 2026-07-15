# Hydra brigadier panel

## Status

Task `040-brigadier-panel.md` is implemented as a read-only, mobile-first operational view for a brigadier's directly granted Teams.

## Reuse decision

The panel **EXTENDS** the Hydra coordination layer and **WRAPS** existing Horilla attendance data. It reuses:

- Hydra `Team`, effective-dated `PersonAssignment` and `ScopeGrant` for roster membership and authorization;
- Hydra `Person` and its controlled Employee link;
- Horilla `Employee`, `Attendance` and late/early markers for the selected day's operational state.

No parallel attendance, absence, Employee or Team model was created. The new code is a thin selector/view/template slice in `hydra_coordination`.

## Scope and permission boundary

Access requires all four permissions:

| Permission | Purpose |
|---|---|
| `hydra_coordination.view_brigadier_panel` | explicit access to the operational panel |
| `hydra_people.view_person` | identity/roster visibility |
| `employee.view_employee` | linked Employee visibility |
| `attendance.view_attendance` | attendance-state visibility |

For a normal user, the Team chooser and every roster query use only active, current `ScopeGrant` records whose object is that exact Team. Company, Location, Section and Department grants never widen this panel. The global company selector, including `all`, does not affect the result. Superuser access remains an explicit administrative bypass.

An unknown or out-of-scope `team` URL parameter returns 404. The selector repeats the Team authorization check, so bypassing the form or view cannot expose another Team.

## Roster and exception semantics

The roster is built from primary `PersonAssignment` records effective on the selected day. It includes only active Persons linked to active Employees whose employment interval covers that day. Search is applied after Team scope and matches names or the readable Hydra identifier.

The panel composes these read-only states:

- no attendance record;
- missing clock-in;
- currently at work;
- completed attendance;
- pending validation;
- late arrival;
- early departure.

"No record" is an operational exception for review. It is deliberately not labelled as a confirmed absence, approved leave or schedule breach because this slice does not yet reconcile leave and shift scheduling.

The selected date cannot be in the future. Results are paginated at 50 employees per page.

## Migration

`hydra_coordination/migrations/0002_alter_team_options.py` adds the custom `view_brigadier_panel` permission while preserving Team ordering. No domain table is added.

## Verification

Focused PostgreSQL coverage contains 9 tests for direct-Team scoping, Horilla attendance composition, exception counts, URL tampering, company `all`, broad Company grants, missing permissions, future dates and scoped search.

The complete implemented Hydra regression passes:

```text
Ran 115 tests - OK
```

`manage.py check`, `makemigrations --check --dry-run` and `migrate --check` pass. The local HTTP endpoint responds and redirects unauthenticated requests to login. Automated 390 x 844 browser navigation was not accepted in this desktop run because the browser retained its initial connection-error data page and its URL policy then blocked a retry; no browser screenshot is claimed.

## Deliberate limits

- The panel is read-only; attendance correction and validation remain in Horilla.
- It does not infer leave, shift expectations or confirmed absence.
- It does not expose Company/Location-wide coordinator scope.
- It does not include reports, exports or mutation actions.

Task `041-coordinator-panel.md` is implemented in `docs/HYDRA_COORDINATOR_PANEL.md`. The next authoritative task is `042-template-module.md`.
