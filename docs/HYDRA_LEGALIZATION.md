# Hydra legalization MVP — TASK-2

## Status and audit decision

Implemented on 2026-07-14 as the smallest complete legalization vertical slice.

The required Horilla inspection found employee and candidate document-request models with simple request/approve/reject states, issue/expiry dates and generic media delivery. Horilla has no pre-employment legalization case, responsible operator, controlled workflow or Person-scoped deadline view.

The implementation decision is:

- **NEW MODULE** for `hydra_legalization` and its domain workflow;
- **REUSE** `hydra_people.Person`, Django users/permissions and current organization scope;
- **WRAP** `hydra_documents.PrivateDocument` through an authorized case link;
- do not extend Horilla employee/candidate document status into a legalization workflow;
- leave the existing Horilla document-request screens and schema operational.

## Complete vertical slice

The server-rendered workspace at `/hydra/legalization/` provides:

- a searchable and status-filterable list of cases in the actor's current Person scope;
- creation from a scoped Person profile;
- case type, responsible operator, reference, deadline, validity period and notes;
- explicit status transitions with append-only history;
- linking existing Person-owned private documents without copying files or exposing storage keys;
- authorized download through the existing audited private-document endpoint;
- desktop and mobile Hydra navigation.

No generic workflow framework, SPA, microservice or external immigration-office integration was added.

## Domain model

`LegalizationCase` belongs to exactly one canonical Person and one responsible Django user. Supported MVP types are work permit, temporary residence, visa and other.

The status graph is intentionally closed:

```text
Draft -> Collecting documents -> Submitted -> Approved -> Expired -> Closed
   |              |                 |  \-> Rejected -> Closed
   |              |                 \-> Additional information -> Submitted/Rejected
   \--------------\-----------------------------------------------> Closed
```

Direct status field editing is excluded from forms. `transition_legalization_case()` locks the case, verifies the requested edge, validates domain dates and writes the case plus `LegalizationStatusHistory` in one transaction. Rejected and closed transitions require a reason. Approved cases require both validity dates; expired cases require a reached validity end date.

History rows are append-only through model/queryset APIs, read-only in admin and protect their case/actor foreign keys. Creation itself records an initial transition into Draft.

## Responsibility and deadlines

The responsible operator must be active, have both legalization and Person read permissions, and currently see the Person through Hydra scope. Assigning a case to someone other than oneself or changing responsibility requires `assign_legalizationcase`.

A deadline may be in the past because overdue work must remain representable. Non-terminal cases with a past deadline are marked **Overdue** in list/detail views. Validity is separate from the operational deadline.

## Authorization boundary

Every list/detail query passes through `legalization_cases_for_user()`, which intersects `view_legalizationcase` with `people_for_user()`. The selected-company session value is not used. Out-of-scope direct UUIDs return HTTP 404.

Writes repeat authorization inside transactional services:

- create: `add_legalizationcase`, `view_legalizationcase`, `view_person` and current Person scope;
- edit: `change_legalizationcase`, case view and scope; responsibility changes also require `assign_legalizationcase`;
- status: `transition_legalizationcase`, case view and scope;
- document link: `link_privatedocument`, `view_privatedocument`, case view, Person match and current Candidate/Person scope.

Superuser remains Django's explicit administrative bypass. Admin registrations are read-only so normal writes cannot bypass services.

## Private documents

`LegalizationCaseDocument` links a case to one existing `PrivateDocument` with a role: identity evidence, application, decision or other. A database uniqueness constraint prevents duplicate links.

The service requires the document Person to match the case Person and requires its Candidate application to remain visible to the actor. Detail templates show only the authorized download route; they never render `.url`, `/media/` or the opaque storage key. Linking the same document twice is idempotent.

## Migration and tests

`hydra_legalization/migrations/0001_initial.py` creates:

- `LegalizationCase` and query indexes for Person/status, responsible/status and deadline;
- append-only `LegalizationStatusHistory` with a case/time index;
- `LegalizationCaseDocument` with a unique case/document constraint;
- action permissions for assignment, transitions and private-document linking.

Focused tests cover:

- HTTP 403 without the model permission;
- list/search and direct-UUID denial across team scope;
- normalized creation and initial history;
- rejection of an inaccessible responsible operator;
- valid and invalid status paths, required reasons and transactional rollback;
- approval validity requirements;
- append-only history;
- assignment permission enforcement;
- same-Person/scoped/idempotent private-document linking;
- absence of storage/media paths in case detail;
- continued operation of Horilla's original document-request view.

The final PostgreSQL 17 acceptance run applied `hydra_legalization.0001_initial` and passed the combined 62/62 Hydra tests. `manage.py check`, `makemigrations --check --dry-run`, `migrate --check`, Python compilation, `pip check` and `git diff --check` also passed.

Browser QA used the real local Django/PostgreSQL stack and scoped `hydra-qa` account. The operator opened a Person profile, created `QA-LEG-2026-001`, linked the existing audited private PDF and performed Draft -> Collecting documents with reason `Documents requested`. Database inspection confirmed two ordered history events and the identity-document link. The detail rendered one active Legalization navigation item, no `/media/` link and no storage key.

At the default 762 px browser surface the detail had no horizontal overflow. At 390 x 844 px the document measured 380 px, details collapsed to one 316.8 px column, navigation used two columns, the private-document download and transition form remained available, and there was no horizontal overflow. The mobile list converted its case row to block/card layout and retained one active navigation item.

## Manual verification

1. Grant an operator `view_person`, `view_legalizationcase`, `add_legalizationcase`, `change_legalizationcase`, `transition_legalizationcase` and a current Hydra scope grant.
2. Open a visible Person and choose **Start legalization**.
3. Create a work-permit case, confirm Draft history and progress it to Collecting documents and Submitted.
4. Attempt Submitted -> Approved without validity dates and confirm validation blocks it; add the period and retry.
5. Link an existing private document and confirm the page contains only the authorized download link.
6. Try a case or document belonging to another team using its direct UUID and confirm HTTP 404.
7. Repeat list, detail and form checks at a viewport no wider than 390 px.

## Known limitations and next task

- Deadline reminders/notifications and automatic expiry jobs are deferred; expiry is an explicit reviewed transition in this MVP.
- One responsible operator is supported; queues, deputies and workload balancing are not modeled.
- Renewals are separate cases without an explicit predecessor link.
- External office submission/status synchronization is not implemented.
- Document scanning, retention and encrypted staging storage retain the limitations documented in `HYDRA_PRIVATE_DOCUMENTS.md`.
- The next numbered task is `023-excel-import.md`.
