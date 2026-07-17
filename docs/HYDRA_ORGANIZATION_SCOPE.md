# Hydra organization scope — TASK-1

## Status and reuse decision

Implemented on 2026-07-14 and hardened on 2026-07-15 with controlled access termination, durable lifecycle events, and retryable notifications.

| Concern | Decision | Rationale |
|---|---|---|
| Legal company | **REUSE** `base.Company` | It remains Horilla's legal-company identity. |
| Department | **REUSE** `base.Department` | Existing HR and employee relations remain authoritative. |
| Horilla selected company | **WRAP** for navigation only | Session selection, including `all`, is not authorization. |
| Location, section/stage and team | **NEW** `hydra_coordination` models | Horilla has no normalized physical/operational hierarchy at these levels. |
| Role actions | **REUSE** Django permissions/groups | Permissions answer which action is allowed. |
| Record scope | **NEW** effective-dated `ScopeGrant` | Grants answer where that action is allowed. |
| Person placement | **NEW** effective-dated `PersonAssignment` | Placement history must exist before Employee conversion and cannot be free text. |
| Access/assignment termination | **EXTEND**, never delete history | Ending access requires permission, reason, locking, audit, and notification. |
| Person access | **EXTEND** `hydra_people.selectors` | Reads intersect permission, active grant, and current assignment. |

## Implemented boundary

`hydra_coordination` owns:

- `Location`, linked to one reused Company;
- `Section`, linked to one Location and optionally one reused Department;
- `Team`, linked to one Section;
- `ScopeGrant`, linked to a user and exactly one organization target with inclusive validity dates;
- `PersonAssignment`, linking a Person to Team and Department with inclusive validity dates and a primary marker;
- `OrganizationAccessEvent`, recording every controlled scope/assignment end and notification delivery state.

Database constraints enforce hierarchy uniqueness, exactly one scope target, valid date intervals, termination metadata consistency, event subject/action/date consistency, and a real notification relation for every `sent` delivery. Transactional services enforce permissions, containment, company consistency, row locking, and non-overlapping primary assignments. Admin screens are read-only.

The organization UI at `/hydra/coordination/organization/` shows the scoped hierarchy, paginated manageable grant history, creation forms, and controlled **End access** actions. Managers see grants whose target is contained by their current scope, not merely grants assigned to themselves. Person details expose assign/end actions and effective-dated history when authorized.

## Authorization semantics

The effective Person queryset is:

`Django action permission ∩ active date-valid grant ∩ current organization assignment`

A company grant contains its locations, sections, and teams. Location contains its sections/teams; section contains teams; department and team grants match their assignment relations. A never-assigned Person remains visible to its creator for the first assignment. Once assigned, normal scope applies. Only Django superusers bypass scope.

`selected_company=all` is deliberately ignored by Hydra selectors. Direct object URLs use the same selectors and return 404 outside scope. Write services independently repeat permission and scope checks, so direct service use cannot bypass authorization.

ScopeGrant foreign keys now use `PROTECT`; deleting a user/company hierarchy object cannot silently erase authorization history. Deactivate identities and close access instead.

## Controlled end workflow

Both grants and Person assignments support:

- **scheduled end** — an inclusive last day that cannot be in the past, precede the start, or extend an existing end date;
- **immediate revocation** — sets the row inactive inside the locked transaction.

Every operation requires a normalized reason, records actor/time/mode, preserves the original row, and creates an append-only `OrganizationAccessEvent`. Repeating the exact action is idempotent. Event business facts cannot be changed or deleted through model/queryset APIs; only bounded delivery fields may change.

After commit, the affected user receives a Horilla notification. Delivery failure never rolls back urgent revocation: the event becomes `failed`, stores a non-sensitive error code, and can be retried with:

```text
python manage.py dispatch_organization_notifications
```

The command has a bounded batch size and attempt limit. A dedicated production maintenance worker must own retries; web workers must not run schedulers.

## Permissions

| Action | Required permission and scope |
|---|---|
| View hierarchy | `view_location` plus active grant; lower levels also require `view_section`/`view_team` |
| Create hierarchy level | matching `add_*` plus a containing active grant |
| View Person | `hydra_people.view_person` plus matching current assignment/grant |
| Assign Person | `view_person`, `add_personassignment`, `assign_person`, visible Person and target Team scope |
| Grant scope | `add_scopegrant`; a non-superuser may grant only a contained target/interval |
| End/revoke scope | `view_scopegrant`, `change_scopegrant`, and a current containing grant |
| End Person assignment | `view_person`, `change_personassignment`, `assign_person`, current Person visibility and Team scope |

Missing action permission returns 403. An out-of-scope direct grant/assignment ID returns 404 in the UI.

## Migrations

- `0001_initial.py` creates organization models and base constraints.
- `0004_organizationaccessevent_and_more.py` adds termination metadata, protected grant relations, the durable event/outbox model, indexes, custom permission, and PostgreSQL consistency constraints. It depends on Horilla's configured notification model.

## Verification

The focused PostgreSQL run passed 44/44 organization/readiness tests. Coverage includes permission-without-scope, company/team isolation, direct URL manipulation, `selected_company=all`, grant self-escalation prevention, assignment overlap, scheduled/immediate termination, date inclusivity, no-extension rules, idempotency, append-only facts, notification failure/retry, and UI permissions.

Manual production acceptance:

1. Give a manager action permissions and a company/location/team grant; confirm only contained hierarchy and grant records appear.
2. Change the Horilla company selector to `all`; confirm visibility does not widen.
3. Schedule a grant end; confirm access remains through the last day and disappears the next day.
4. Revoke another grant immediately; confirm access disappears at once while history remains.
5. Repeat direct URLs without change permission and from another company; expect 403 and 404.
6. End a Person assignment and verify the actor, reason, event, Person/team history, and employee notification.
7. Simulate notification failure; verify access still closes, the event is `failed`, and the retry command moves it to `sent` without another lifecycle event.
8. Repeat hierarchy, pagination, and both end forms at 390 px width.

## Production notes

- Access periods are intentionally not edited through generic CRUD. The end workflow only preserves or narrows access; extending/replacing access requires a reviewed new grant.
- Primary overlap is enforced transactionally; every production write path must use the service.
- With no current Hydra assignment, Horilla `EmployeeWorkInformation` remains a last-known compatibility projection; operational scope and reports use Hydra history.
- New translation-ready strings still need populated locale catalogs.
- Notification retries are owned by the monitored single-owner worker documented in `HYDRA_MAINTENANCE.md`.
