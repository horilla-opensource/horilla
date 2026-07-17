# Hydra universal tasks

## Status and reuse decision

Full Engineering Package TASK-017 is implemented. The decision is **NEW MODULE
+ REUSE/WRAP**:

- `hydra_tasks` owns one canonical operational task contract because Horilla's
  project, onboarding and helpdesk tasks have different owners and cannot link
  one scoped task consistently to `hydra_people.Person` and Hydra domain facts;
- Horilla's database `notifications.Notification` and `notify` signal are
  reused behind a durable, scope-rechecking delivery boundary;
- Company, Person, legalization, arrival, housing and onboarding records remain
  owned by their existing modules. Tasks reference them but never copy their
  business state or become a generic workflow/plugin engine.

The next TASK-018 still owns the general notification center, read-state UX,
digest/email and browser-push policy. TASK-017 supplies assignment/change
notifications for tasks only.

## Task contract

`HydraTask` has an opaque UUID, unique idempotency key, Company, canonical
Person, assignee, title, bounded description, priority, optional deadline,
status and optimistic version. Every task also stores one approved target kind,
target UUID and a safe immutable label snapshot.

Approved target kinds are deliberately closed and code reviewed:

- Person;
- Legalization case;
- Arrival plan;
- Housing assignment;
- Onboarding handoff.

There is no generic Django content-type relation. Creation resolves the target
through its authoritative scoped selector and proves it belongs to the same
Person and Company. Direct UUID substitution and unsupported target types fail
before a row is written. Readiness rechecks stored target integrity without
requiring an obsolete historical Person-to-Company relationship to remain
current.

## Authorization and assignment

Every list/detail read intersects `hydra_tasks.view_hydratask`, current Person
scope and current Company scope. Unless the actor has
`hydra_tasks.view_all_hydratask`, only tasks assigned to or created by that user
are returned. Direct out-of-scope URLs resolve as 404.

Creation and editing require the matching Django model permission. Assignment
requires `assign_hydratask`; lifecycle changes require
`transition_hydratask`; reopening additionally requires `reopen_hydratask`.
An assignee must be active, hold Person-view plus task-view/transition
permissions, and currently cover both the Person hierarchy and Company. This is
rechecked in the service and again before a notification is delivered.

The normal administrator is read-only for task identity/history. No task delete
permission is generated.

## Lifecycle and concurrency

Allowed transitions are:

```text
open <-> in_progress
open|in_progress -> completed|cancelled
completed|cancelled -> open (permission plus reason required)
```

Completion, cancellation and reopening require a reason. Terminal timestamp
and resolution shapes are database constrained. Creation, edit, reassignment
and transition use atomic services, row locks and the caller's expected
version; a stale browser submission writes nothing.

Tasks cannot be hard deleted. Normal manager updates, identity/target rewrites
and uncontrolled instance changes raise immediately. `HydraTaskEvent` is an
append-only sequence with one event per task version and records safe changed
field names, status/assignee/deadline/priority facts and reason without copying
the description. Database constraints protect positive unique sequences.

## Notifications and recovery

Each event that changes task ownership or work state creates one durable
`HydraTaskNotificationDelivery`. After commit, dispatch rechecks that the
recipient is active and can still see the task. Stale assignment/scope becomes
`not_applicable`; transient failure is retained with a bounded error code for
retry. Notification text and JSON contain no task title, Person name, Hydra ID
or description, only a permission-aware task-detail redirect.

The single-owner Hydra maintenance worker retries pending/failed task
deliveries and exposes selected/sent counters. Exhausted attempts remain an
operator-visible readiness error; delivery rows are durable evidence and
cannot be deleted or re-parented.

## User interface and integration

The server-rendered responsive UI is available at `/hydra/tasks/` and provides:

- bounded, paginated search plus status, priority, ownership and deadline
  filters;
- create-from-Person with Company, approved target, assignee and due-date
  choices derived on the server;
- detail, edit, reassignment and controlled transition screens;
- immutable history on the task detail;
- an open-task section and create action on Person detail;
- permission-aware task events in the Person timeline;
- overdue, Location-scoped tasks in the coordinator panel.

The coordinator panel keeps its existing domain permissions. Task data appears
only when the user separately holds task-view permission; adding TASK-017 does
not widen or break the base panel role.

## Operations and integrity

Migration `hydra_tasks/migrations/0001_initial.py` creates the task, event and
delivery tables, constraints and operational indexes. It is included in the
exact SHA-256 migration manifest.

Readiness verifies:

- every stored target still resolves to the same Person and Company;
- every active task has a currently eligible assignee;
- task versions and append-only event sequences are continuous and delivery
  rows refer to the same task as their event.

Manual operator recovery consists of correcting the recipient permission/scope
or transport failure and allowing the maintenance process to retry. Tasks and
events are never rewritten to hide a failed delivery.

## Verification scope

Automated PostgreSQL coverage includes idempotency, input and target tampering,
an approved Legalization-case target, cross-scope denial, assignee eligibility,
involvement versus view-all visibility, optimistic locking, lifecycle/reopen,
hard-delete and append-only guards, notification privacy and stale-scope
handling, Person timeline projection, readiness invariants, direct URL denial,
coordinator Location isolation and maintenance retry integration.

The completed verification run on 2026-07-17 passed the 17 focused task and
coordinator tests and the clean PostgreSQL regression at 408/408. Django system
checks, migration drift detection and the exact 70-file migration manifest also
passed. Browser QA created a task linked to an approved Legalization case and
confirmed its detail, immutable creation event, Person open-task projection and
timeline event. Desktop and 390 x 844 mobile task list/form views had no global
horizontal overflow, duplicate DOM identifiers, unlabeled visible controls or
browser console warnings/errors.

Before production GO, the target environment still requires role journey and
monitoring evidence under TASK-036. General notification-center behavior is the
next implementation package, TASK-018.
