# Hydra implementation decisions — Phase 0

## Status

These decisions are the output of the source audit and define the boundary for numbered implementation tasks.

Phase 0 was accepted on 2026-07-14. TASK-1 Person identity, organization scope and the Hydra shell are implemented. TASK-2 recruitment extension, private candidate documents, legalization MVP and transactional candidate Excel import are implemented. TASK-3 arrival planning, controlled Person-to-Employee conversion and employee team assignment are also implemented. The direct-Team brigadier panel, direct-Location coordinator exception dashboard, scoped template/Szablonizator export module, controlled public Hydra link directory and scoped operational report are implemented for TASK-4; see `docs/HYDRA_PERSON_IDENTITY.md`, `docs/HYDRA_ORGANIZATION_SCOPE.md`, `docs/HYDRA_SHELL.md`, `docs/HYDRA_RECRUITMENT.md`, `docs/HYDRA_PRIVATE_DOCUMENTS.md`, `docs/HYDRA_LEGALIZATION.md`, `docs/HYDRA_EXCEL_IMPORT.md`, `docs/HYDRA_ARRIVALS.md`, `docs/HYDRA_EMPLOYEE_CONVERSION.md`, `docs/HYDRA_TEAM_ASSIGNMENT.md`, `docs/HYDRA_BRIGADIER_PANEL.md`, `docs/HYDRA_COORDINATOR_PANEL.md`, `docs/HYDRA_TEMPLATES.md`, `docs/HYDRA_PUBLIC_LINKS.md` and `docs/HYDRA_REPORTS.md`.

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
| `hydra_legalization` | cases, statuses, responsibility, validity/deadlines | public file delivery |
| `hydra_arrivals` | planned/confirmed/no-show arrival events | employee attendance |
| `hydra_housing` | facility/room/bed and effective assignments | team hierarchy |
| `hydra_imports` | upload session, preview, validation, duplicate decisions, transactional apply | generic ETL/no-code engine |
| `hydra_templates` | message templates, placeholder registry and authorized exports | desktop runtime execution |
| `hydra_reports` | scoped operational report composition and append-only export audit | unscoped domain reads or browser-side authorization |

Private document storage/access may be a focused shared app if it serves multiple domains; its API must accept an already-authorized owner/domain object and still record access.

## Service and selector conventions

- Multi-record mutations use `transaction.atomic`.
- Service input is typed/validated data, not raw request objects.
- Services enforce state transitions and idempotency.
- Notifications use `transaction.on_commit`.
- Selectors accept the acting user/scope context and return already-scoped querysets.
- Object views call selectors, not an unscoped manager followed by a late permission check.
- Bulk operations validate the complete plan before writing.
- Imports expose preview/errors before apply and store a stable import fingerprint.
- Effective-dated assignments use database constraints to prevent invalid overlaps where PostgreSQL supports them.

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
6. Arrival planning, Person-to-Employee conversion and team assignment **implemented**.
7. Brigadier and coordinator panels, the scoped template/Szablonizator export module, controlled Hydra public links and scoped operational reports **implemented**.
8. Hardened staging, backup/restore and pilot verification **implemented**; target-environment and business-owner gates remain in `HYDRA_STAGING.md`.

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
| Upstream baseline migrations and dynamic Django User migration were not versioned | Non-deterministic schema/deployments | Task 045 surfaces all generated migrations for version control and injects the pinned Django 4.2.24 auth compatibility migration into the staging image; review/commit remains a go/no-go gate |
| Mostly unpinned upstream dependencies | Builds can change without code changes | Staging installs the audited CPython 3.11 lock; Linux image build remains target-environment evidence |
| Session/thread-local company filter | Cross-scope disclosure | Mandatory Hydra selectors and object denial tests |
| Generic authenticated media route | Passport/legalization disclosure | New private delivery boundary before sensitive uploads |
| No effective upstream tests/CI | Regressions invisible | Add CI and focused Hydra tests from the first module |
| Legacy schedulers previously started in every eligible process | Noisy/racy checks and duplicate jobs in multi-worker deployment | Task 045 centralizes the disable decision and requires all schedulers off in staging web workers |
| Fixed admin credentials in upstream container entrypoint | Immediate compromise if reused | Removed; staging uses one-time interactive secure admin provisioning |
| Two candidate-to-employee paths | Duplicate/partial conversion | Route both through one idempotent service |
| Public PWA cache policy | Private content could be cached if reused | Keep service worker on public portal only |
| No .NET SDK on audit workstation | Desktop tests not independently executed | Verify Szablonizator in its own CI/release workflow; no runtime integration |
