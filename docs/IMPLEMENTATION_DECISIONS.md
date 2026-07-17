# Hydra implementation decisions — Phase 0

## Status

These decisions are the output of the source audit and define the boundary for numbered implementation tasks.

Phase 0 was accepted on 2026-07-14. TASK-1 Person identity, organization scope and the Hydra shell are implemented. TASK-2 recruitment extension, private candidate documents, legalization MVP and transactional candidate Excel import are implemented. TASK-3 arrival planning, controlled Person-to-Employee conversion and employee team assignment are also implemented. The direct-Team brigadier panel, direct-Location coordinator exception dashboard, scoped template/Szablonizator export module, controlled public Hydra link directory and scoped operational report are implemented for TASK-4. The Full Engineering Package audit/timeline TASK-008, controlled recruitment workflow TASK-010, legalization configuration/reminders TASK-014/016, universal tasks TASK-017 and notification center/delivery policy TASK-018 are implemented; see `docs/HYDRA_TIMELINE.md`, `docs/HYDRA_RECRUITMENT_WORKFLOW.md`, `docs/HYDRA_TASKS.md`, `docs/HYDRA_NOTIFICATIONS.md` and the domain documents referenced by `docs/PRODUCTION_COMPLETION_MATRIX.md`.

## Accepted architecture decisions

1. **Fork and extend Horilla branch `1.0`.** Do not rewrite HRMS behavior from zero.
2. **Use a Django monolith with server-rendered, mobile-first templates.** No React SPA, microservices or native mobile app in the MVP.
3. **Create `hydra_people.Person` as canonical pre-employment identity.** A Person can exist without email, have multiple recruitment applications and optionally link one-to-one to Horilla Employee after hiring.
4. **Keep application and person separate.** Horilla Candidate remains the recruitment/application record. New Hydra intake creates the Person link transactionally; legacy Candidates enter an explicit, company-scoped review/backfill queue.
5. **Reuse Horilla Employee only after employment.** All creation/linking goes through one idempotent transaction service.
6. **Reuse Company and Department.** Add Location, operational Section/Stage, Team and effective-dated assignments; do not duplicate or overload the Horilla models.
7. **Wrap permissions with explicit Hydra scope.** Django model permissions answer what action a role may perform; Hydra scope answers on which records. Both must pass.
8. **Use selectors for all scoped reads and services for business writes.** Views remain thin. Direct `.objects.get(pk=url_id)` is prohibited for scoped Hydra objects.
9. **Replace private media delivery.** Passports/legalization documents use private storage, authorized streaming and immutable access logging. Generic `/media/` is not acceptable.
10. **Reuse notifications and audit primitives.** Emit notifications after commit; add explicit domain transition and document-read logs.
11. **Keep the current public portal deployed.** Link to it during MVP; do not cache authenticated data with its service worker.
12. **Keep Szablonizator as a desktop tool.** MVP provides compatible authorized XLSX exports. Server-side DOCX generation is deferred.
13. **PostgreSQL is the target database.** SQLite may be useful only for quick upstream diagnostics, not Hydra acceptance tests.
14. **No universal workflow, rule, plugin or dashboard framework in month one.** Implement only concrete domain statuses and services.
15. **Priva remains outside Hydra.** No production-row or productivity integration.
16. **Treat future housing periods as reservations and moves as one transaction.** Do not create a parallel booking identity. A move narrows/deactivates the protected source, creates the destination and appends paired evidence under deterministic Person/bed locks; day-granular facts are never rewritten to fabricate intra-day ordering.
17. **Treat deployment shortcuts and backup archives as untrusted input.** `-InitialDeployment` may skip a recovery point only after PostgreSQL proves the application schema empty. Sensitive restore archives are validated for normalized unique paths and regular file/directory types before extraction; an operator flag, checksum file or archive metadata alone is not authority to overwrite recovery storage.
18. **Project one Person timeline from authoritative histories; do not dual-write a second event store.** Horilla auditlog and explicit append-only Hydra domain facts retain ownership. The user-facing aggregate independently rechecks Person scope and every source permission, exposes only safe labels/context, caps work per source and never renders raw audit changes or sensitive payloads.
19. **Wrap Horilla recruitment stages with one controlled transition contract for linked applications.** Keep Recruitment, Stage, Candidate and pipeline UX, but require a directed active rule, current Person scope and one locked service for every linked Candidate stage change. Preserve immutable actor/source/reason evidence; expose only from/to Stage labels on the Person timeline. Direct save and bulk stage updates are invalid bypasses, while unlinked Candidates remain outside Hydra until reviewed.
20. **Extend legalization with fixed-field policy dictionaries, not a generic workflow engine.** Keep the closed, code-reviewed core transition graph, then configure Company/global procedure labels, enabled normalized statuses, document requirements and approved authorities. Snapshot the complete selected policy on case creation and the selected case-policy authority on every external fact, so later configuration changes affect only future cases. An authority mapping that cannot be inferred from legacy facts remains a readiness failure until a superuser performs the explicit one-time, reasoned and append-only adoption.
21. **Own one closed universal-task contract and wrap Horilla notifications.** Horilla project, onboarding and helpdesk task models keep their existing domain ownership. `hydra_tasks` owns a Person/Company-scoped task with only five code-reviewed target types, optimistic versioning and append-only events. Durable notification delivery rechecks the recipient's current permissions and scope and never carries task/Person PII; it does not pre-empt TASK-018's general notification-center policy.

## Data ownership and synchronization

### Person owns

- UUID and readable Hydra identifier;
- legal/passport name and normalized personal identity;
- date of birth, gender and citizenship;
- preferred language;
- candidate contact channels, with email optional;
- pre-employment lifecycle and history;
- link to applications and optional Employee.

### Recruitment application owns

- recruitment/campaign and position;
- stage, outcome, source, schedule and application-specific answers;
- application documents/status that are not canonical identity facts;
- recruiter decisions and application history.

### Employee/WorkInformation owns

- active Horilla user relationship;
- work email/account after employment;
- company, department, job, manager, shift, work type and employment dates;
- selected attendance/leave/employment features.

### Synchronization policy

- Person-to-Employee synchronization is one explicit service, never two-way signals.
- Conversion snapshots the source values and records field-level decisions.
- Later employee work changes do not overwrite passport identity.
- Person contact updates do not silently change login username/work email.
- Conversion is idempotent and protected by database constraints/row locks.
- Conflicts require an explicit operator decision and audit record.

## Scope model

### Role versus scope

Roles use Django Groups/Permissions for actions such as view, change, approve, import or export. Separate scope grants constrain records by:

- company where relevant;
- physical location;
- department where required;
- operational team;
- validity interval for historical assignment/scope.

A user's effective queryset is the intersection of permission, active grants and object relationships. Superuser/support bypasses must be explicit, audited and absent from normal coordinator/brigadier roles.

### Required denial tests

At minimum, later permission tasks must prove:

- brigadier A cannot list, view, edit, export or download team B data;
- changing URL IDs does not cross team/location scope;
- coordinator scope does not cross assigned locations;
- company `all` selection does not widen Hydra scope;
- generic Django permission without scope returns no out-of-scope object;
- document authorization is re-evaluated on every request;
- inactive/expired scope grants stop access;
- reports and imports/exports apply the same selectors.

## Module boundaries

| Module | Owns | Must not own |
|---|---|---|
| `hydra_people` | Person, lifecycle, application links, Employee link/conversion service | Horilla work information or recruitment stages |
| `hydra_coordination` | Location, section/stage, team, role scope grants, historical assignments | Company/Department duplicates |
| `hydra_documents` | private file metadata/storage, content validation, authorized download and append-only access events | generic public media or legalization workflow |
| `hydra_legalization` | Company/global procedure/requirement/authority policy, immutable case snapshots, cases, statuses, bounded deputies, audited responsibility transfer, scoped workload, evidence-backed authority correspondence and renewal lineage | generic workflow engines, inferred leave access, silent load balancing, public file delivery, guessed legacy policy/chain mappings or unsupported authority API integration |
| `hydra_arrivals` | planned/confirmed/no-show arrival events and the scoped cross-domain onboarding handoff | employee attendance or duplicate onboarding tasks/stages |
| `hydra_housing` | facility/room/bed and effective assignments | team hierarchy |
| `hydra_imports` | memory-only workbook parsing, bounded preview data, validation, duplicate decisions, transactional apply and append-only purge evidence | indefinite source-data retention or generic ETL/no-code engine |
| `hydra_templates` | message templates, placeholder registry and authorized exports | desktop runtime execution |
| `hydra_reports` | scoped operational report composition and append-only export audit | unscoped domain reads or browser-side authorization |
| `hydra_tasks` | scoped Person/domain tasks, lifecycle events and durable task-notification delivery evidence | generic workflows/plugins, copied domain state or a parallel notification center |

Private document storage/access may be a focused shared app if it serves multiple domains; its API must accept an already-authorized owner/domain object and still record access.

## Service and selector conventions

- Multi-record mutations use `transaction.atomic`.
- Service input is typed/validated data, not raw request objects.
- Services enforce state transitions and idempotency.
- Local database notifications are written in the same atomic unit or from `transaction.on_commit`; external transports require a durable delivery fact/outbox.
- Recurring Hydra work runs only in the advisory-lock-protected maintenance process. Legalization reminders and automatic expiry use durable, append-only delivery facts; expiry history identifies a system source instead of impersonating a user.
- Arrival reminders use the same single-owner boundary and append-only delivery facts. Overdue automation escalates only within current destination scope and never fabricates the human no-show decision.
- Task delivery uses the same maintenance owner for bounded retries; current assignee eligibility and task visibility are rechecked before notification creation.
- Selectors accept the acting user/scope context and return already-scoped querysets.
- Object views call selectors, not an unscoped manager followed by a late permission check.
- Bulk operations validate the complete plan before writing.
- Imports expose preview/errors before apply and store a stable import fingerprint.
- Effective-dated assignments use database constraints to prevent invalid overlaps where PostgreSQL supports them.

## Controlled onboarding decision

Horilla onboarding is **EXTEND + WRAP**, not replaced. A confirmed Hydra arrival
may start the existing CandidateStage/CandidateTask structure only through the
locked, scoped handoff service. Employee conversion, a current primary Team at
the arrival destination, and all assigned tasks in `done` state are independent
facts required before completion. The handoff/event models preserve the
cross-domain evidence without duplicating ownership.

One application/arrival has one handoff; a Person may have multiple handoffs
over time and may reuse an existing Employee conversion. Legacy GET/bulk task
mutations are rejected for Hydra handoffs. Recovery runs as an explicit bounded
maintenance job. External portal email does not change onboarding state unless
delivery succeeds. The implemented Hydra outbox persists the stable token and
verified attachments, uses one-active-row/idempotency constraints, leases and
capped retry, preserves append-only events, redacts Horilla's legacy mail log,
and purges sensitive payload after resolution. SMTP remains honestly
at-least-once because remote acceptance cannot share the database transaction.

## Private document minimum design

- separate private storage prefix/bucket from public media;
- opaque, generated object keys with no passport/name in path;
- metadata row links Person/domain, document type, status and checksum;
- upload content/size checks plus malware-scanning integration point;
- no direct storage URL in templates;
- authorized endpoint streams or redirects using a short-lived signed URL;
- access decision checks action and current scope;
- log actor, object, action, timestamp, outcome and request correlation data;
- safe response headers (`Content-Disposition`, `nosniff`, restrictive cache control);
- retention/deletion policy and restore behavior documented before pilot data.

## Delivery order after Phase 0 review

1. Person identity and application linkage.
2. Organization/location/team scope plus denial tests. **Implemented.**
3. Hydra shell/branding without core rewrite. **Implemented.**
4. Recruitment extension and private candidate documents **implemented**.
5. Legalization and transactional candidate import **implemented**.
6. Arrival planning, Housing, Person-to-Employee conversion and team assignment **implemented**.
7. Brigadier and coordinator panels, the scoped template/Szablonizator export module, controlled Hydra public links and scoped operational reports **implemented**.
8. Hardened staging, backup/restore and pilot verification **implemented**; target-environment and business-owner gates remain in `HYDRA_STAGING.md`.
9. Universal Person/domain tasks, append-only history, privacy-safe delivery and coordinator integration **implemented**; the general notification center remains TASK-018.

The numerical task order remains authoritative when it differs from this dependency summary.

## Go/no-go gates before business coding

Phase 0 review should explicitly accept:

- the Person/Application/Employee split;
- the Company/Department versus Location/Team split;
- the scope policy approach;
- replacement of private document delivery;
- continued external portal and Szablonizator boundaries;
- a remediation decision for upstream baseline migrations and dependency locking.

## Blocking risks

| Risk | Impact | Required response |
|---|---|---|
| Upstream baseline migrations and dynamic Django User migration were not versioned | Non-deterministic schema/deployments | Task 045 surfaces all generated migrations, pins the Django 4.2.24 auth compatibility source, and enforces an exact 70-file normalized-SHA-256 manifest in CI and the image build; review/commit remains a go/no-go gate |
| Mostly unpinned upstream dependencies | Builds can change without code changes | Staging installs the audited CPython 3.11 lock; Linux image build remains target-environment evidence |
| Session/thread-local company filter | Cross-scope disclosure | Mandatory Hydra selectors and object denial tests |
| Scope or assignment records deleted/edited without a lifecycle fact | Silent authorization-history loss | Protected foreign keys, narrowing-only end service, locked rows, append-only organization access event, and retryable user notification |
| Legalization owner changed or absent without a controlled handoff | Lost deadlines or an unnotified second writer | Dedicated reasoned transfer, bounded case deputy, independent Person scope, locked overlap checks, append-only work event and durable notification |
| Generic authenticated media route | Passport/legalization disclosure | New private delivery boundary before sensitive uploads |
| Untrusted uploads accepted after signature-only MIME checks | Malware persistence or delivery | Dedicated quarantine plus fail-closed ClamAV `INSTREAM`; clean results alone are promoted, scanner health is a staging readiness gate |
| Undefined document disposal and legal preservation | Premature deletion or indefinite retention | Per-document retention, permissioned legal hold, tombstone deletion, immutable lifecycle events, and scheduled storage purge |
| No effective upstream tests/CI | Regressions invisible | Add CI and focused Hydra tests from the first module |
| Legacy schedulers previously started in every eligible process | Noisy/racy checks and duplicate jobs in multi-worker deployment | Task 045 centralizes the disable decision and requires all schedulers off in staging web workers |
| Fixed admin credentials in upstream container entrypoint | Immediate compromise if reused | Removed; staging uses one-time interactive secure admin provisioning |
| Two candidate-to-employee paths | Duplicate/partial conversion | Route both through one idempotent service |
| Public PWA cache policy | Private content could be cached if reused | Keep service worker on public portal only |
| No .NET SDK on audit workstation | Desktop tests not independently executed | Verify Szablonizator in its own CI/release workflow; no runtime integration |
