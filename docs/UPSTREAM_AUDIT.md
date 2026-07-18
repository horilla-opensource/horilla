# Horilla audit — Phase 0

## Audit snapshot

- Repository: `https://github.com/horilla/horilla-hr.git`
- Audited branch: `1.0`
- Commit: `11c4e3a2596c58f2381bda4c6bbc319a4430b097`
- Commit date: 2026-07-09
- Audit date: 2026-07-14

The audit is based on the checked-out source, not on product marketing or assumptions. No Hydra business model was added in Phase 0.

## Executive conclusion

Horilla is a suitable Django foundation, but it is not yet a safe Hydra authorization or document-storage layer. Authentication, employee/work information, recruitment stages, onboarding, attendance, notifications and audit primitives should be reused or extended. Hydra must add a canonical pre-employment `Person`, explicit location/team scope, private document delivery and domain modules for legalization, arrivals and housing.

The highest-priority blockers before pilot data is loaded are:

1. upstream migrations are not versioned and are generated at runtime;
2. the upstream dependency list is mostly unpinned;
3. company filtering is request/session-dependent and is not an object authorization boundary;
4. generic media delivery checks only authentication, not ownership or scope;
5. candidate document access is not consistently tied to the candidate in the session;
6. the checked-out branch has no effective automated test suite or CI workflow.

## Runtime and project configuration

### Versions

- `Dockerfile`: Python 3.10 on Debian Bullseye.
- `requirements.txt`: Django 4.2.24 and PyMuPDF 1.24.5 are pinned; most other packages are not.
- `docker-compose.yaml`: PostgreSQL 16 Bullseye.
- Verified Phase 0 workstation: CPython 3.11.9 and PostgreSQL 17.2 on Windows x64.

The Windows lock in `requirements.phase0-windows-py311.lock` captures the environment actually tested. It is deliberately not presented as a production/Linux lock.

### Settings and applications

`hydra/settings.py` declares the Django core plus notifications, base, employee, recruitment, leave, PMS, onboarding, asset, attendance and payroll. Importing `horilla/__init__.py` mutates settings further through `horilla/hydra_apps.py`, adding audit, documents, automations, biometric, helpdesk, offboarding, backup, project and other Horilla apps. App `ready()` methods append URL patterns dynamically.

Relevant settings:

- SQLite is the fallback when no database environment variable exists.
- `DATABASE_URL` takes precedence and was used for the PostgreSQL verification.
- `MEDIA_ROOT` is local `media/`; `MEDIA_URL` is `/media/`.
- Google or S3 storage can be selected through environment variables.
- `simple_history.middleware.HistoryRequestMiddleware` and `auditlog.middleware.AuditlogMiddleware` are active.
- Django notifications use database storage, soft delete and watched state.

The dynamic settings and URL registration work, but they make startup side effects harder to reason about. Hydra apps should register through normal `AppConfig` and URL includes where possible.

## Employee and employment data

### `employee.Employee`

Useful existing behavior:

- optional one-to-one link to Django `User`;
- names, phone, address, date of birth and gender;
- active state and audit-related behavior;
- automatic creation of `EmployeeWorkInformation`;
- Django permissions for own profile;
- company-aware manager through `employee_work_info__company_id`.

Critical identity constraint: `Employee.email` is required and unique. The model represents employment, can create a user using the email as username, and cannot represent a person without an email or without employment. It therefore cannot be Hydra's canonical candidate identity.

### `employee.EmployeeWorkInformation`

Reusable fields include department, job position, job role, reporting manager, shift, work type, employee type, company, work email, joining date and contract end date. It already uses Horilla audit history and company filtering.

The existing free-text `location` is not sufficient for referential, scoped access to a greenhouse site. It must not be overloaded as Hydra `Location`.

Decision: extend/link the employee domain after hiring; do not fork or replace it.

## Organization

### Reusable models

- `base.Company`: organization/legal entity information, HQ marker and locale formats.
- `base.Department`: reusable department linked many-to-many to companies.
- `JobPosition`, `JobRole`, work types and shifts: reusable for Horilla employment features.

### Missing Hydra levels

There is no normalized physical location, greenhouse section/stage, team or effective-dated team assignment. Hydra needs new coordination models for those concepts and must keep them distinct from legal company and HR department.

Decision: reuse `Company` and `Department`; add only the missing physical and operational levels.

## Recruitment and candidate conversion

### Existing recruitment pipeline

`recruitment.Recruitment`, `Stage` and `Candidate` provide campaigns, open positions, stage managers, recruitment managers, ordered stages, hiring/cancel states, interviews, surveys, ratings and document requests. `Candidate` uses `HydraCompanyManager` through its recruitment's company and has simple-history audit records.

### Why `Candidate` is not `Person`

`Candidate` is an application record:

- it belongs to one recruitment;
- email is required;
- resume is required;
- uniqueness is `(email, recruitment)`;
- it can link directly to one converted employee;
- it mixes application lifecycle with personal data.

One real person can have multiple applications and may lack email or resume at intake. A new `hydra_people.Person` is therefore required, with each Horilla candidate/application linking to that person.

### Existing conversion

The direct conversion view is transactional and creates an `Employee`, updates work information, copies document records, and sets `converted_employee_id`. The onboarding portal provides a second conversion path that builds employee and bank details in multiple requests.

The conversion logic assumes candidate email can become employee/user identity and currently transfers duplicate personal fields. Hydra should wrap it in one explicit service that:

- locks the Person and application rows;
- creates or links exactly one Employee;
- applies the documented ownership/synchronization policy;
- records the conversion idempotently;
- copies only approved employment data;
- preserves application and Person history.

## Onboarding

Horilla already provides stages, tasks, candidate-stage tracking, task status and a tokenized onboarding portal. These are useful for assigned onboarding after recruitment.

The portal is closely coupled to `Candidate` and the email-driven Employee conversion flow. It should be extended only after Person linkage and private-document boundaries are in place. The current public Hydra training portal remains separate during the MVP.

Decision: extend, not replace.

## Permissions and company scoping

### Existing mechanisms

- Django `User`, `Group`, model permissions and user permissions.
- View decorators such as `permission_required`, recruitment manager checks and owner/manager checks.
- Reporting-manager subordinate selection.
- `CompanyMiddleware` stores a selected company in the session.
- `HydraCompanyManager` applies a model-level `company_filter` when a selected company exists.

### Limitations

- Selecting `all` removes company filtering.
- Filtering is held in thread-local request state and dynamically attached to model classes.
- `HydraCompanyManager.entire()` deliberately bypasses the filter.
- broad Django model permissions do not encode a user's location, department or team scope;
- manager decorators decide whether someone is a manager globally and do not prove access to the object in the URL;
- swallowed exceptions in the manager can return unscoped querysets;
- there is no reusable server-side policy proving “this brigadier may access this team/person.”

This is useful UI/data partitioning, but not a sufficient Hydra authorization boundary. Hydra needs explicit scope assignments and mandatory scoped selectors for every list and object fetch. Direct URL denial must be tested.

Decision: wrap Django/Horilla permissions with a small Hydra scope policy; do not create a generic rule engine.

## Notifications

The local notifications app is based on Django notifications and stores actor, recipient, target/action object, verb, timestamps, read/deleted state and JSON data. Horilla adds localized verb fields and uses the `notify` signal broadly.

Decision: reuse. Hydra services may emit notifications after transaction commit. Sensitive personal data must not be placed in notification verbs or unstructured JSON.

## Audit and history

There are two overlapping mechanisms:

1. `django-auditlog` is configured to include all models and records actor/request context through middleware. `HydraModel` exposes an auditlog history field and created/modified users.
2. `django-simple-history` is used selectively through `HydraAuditLog` for Candidate, EmployeeWorkInformation, Attendance and other models, with diff UI helpers.

Decision: reuse both where they already operate, but define one convention per Hydra model. Business status transitions should have explicit history records, and private document reads/downloads need a dedicated immutable access log because model-change history does not record reads.

## Documents and media

### Existing components

- `hydra_legacy_documents.DocumentRequest` and `Document` support employee document requests, upload status, issue/expiry dates and file-size/extension checks.
- recruitment has parallel `CandidateDocumentRequest` and `CandidateDocument` models.
- local files are served through `/media/<path>` by `base.views.protected_media`.
- optional GCP storage uses private ACLs; S3 support is configurable.

### Security findings

- `/media/<path>` allows any authenticated session or valid JWT to retrieve any non-public media path that it can discover; it performs no object-level document authorization and writes no access log.
- three path prefixes are deliberately public, including candidate profile content.
- candidate document model querysets are not consistently company-scoped.
- the candidate `view_file` endpoint checks that some candidate is logged in, but does not verify the requested document belongs to that candidate.
- templates contain direct `.url` links for resumes and other uploads, bypassing the stricter object-specific `view_file` checks.
- extension checks are not content-type or malware validation.
- local `FileField.path` assumptions are incompatible with private object storage in some view code.

Passports and legalization files must not use this generic path. Implement private storage with opaque keys and one authorized download service that logs every outcome. Existing document metadata can inform the new design, but the delivery boundary must be replaced.

Decision: replace media delivery for Hydra-private documents and wrap/extend metadata only where appropriate.

## Attendance

Horilla attendance already models daily attendance, activities, clock in/out, minimum/worked time, validation, overtime and late/early exceptions. It is employee-based, company-aware and audited.

Decision: reuse selected attendance data after employment, especially for brigadier absence/exception views. Do not put candidate arrival or pre-employment presence into attendance.

## Imports and reports

Employee import/export uses pandas, transactions in lower-level bulk helpers and spreadsheet templates. Holiday/base imports and browser-side report exports also exist. Reports cover employee, recruitment, attendance, leave, payroll, assets and PMS, protected primarily by broad model permissions and company filtering.

Hydra candidate import requires preview, deterministic duplicate detection, idempotency and one transaction; it should not reuse the existing employee-import view directly. Existing parsing and error-report ideas can be reused. Hydra reports should extend the report UI but must source data through explicit scope-aware selectors.

## Deployment and operational files

Upstream provides `Dockerfile`, `docker-compose.yaml`, `entrypoint.sh` and `docker.md`. Important findings:

- Docker targets Python 3.10 and PostgreSQL 16.
- Compose embeds development database credentials.
- the entrypoint runs `makemigrations` on every start;
- the entrypoint creates a fixed `admin/admin` account;
- only `horilla/` and `media/` are bind-mounted into the server container;
- Dockerfile default command uses Django `runserver`, while Compose replaces it with Gunicorn through the entrypoint;
- server health check, backup restore drill and secrets management are not provided;
- there is no GitHub Actions workflow in the audited branch.

The existing Compose file is suitable only as an upstream development reference. It is not the Phase 4 staging design.

## Migrations and tests

The repository's `.gitignore` excludes `**/migrations/**` except `__init__.py`. The audited clone contains no application migration files. A clean bootstrap generates baseline migrations for every app and even creates `auth/migrations/0013_user_is_new_employee.py` inside the virtual environment because Horilla adds a field to Django's `User` model dynamically.

Consequences:

- clean deployments derive schema from source and installed dependency versions;
- two environments can generate different migration graphs;
- `makemigrations --check` fails before baseline generation;
- the migration for the customized Django User is outside the repository;
- normal zero-downtime migration review is impossible until corrected.

The repository has 27 `tests.py` placeholders but no actual Django test methods/classes in the audited source. There is no CI workflow. The first standard `manage.py test` run also failed during discovery because `dynamic_fields/migrations/__init__.py` imported application signals although the optional app was not installed. Phase 0 moved that registration to `DynamicFieldsConfig.ready()`, which restores normal Django discovery without changing a business feature.

Phase 1 must commit all new Hydra migrations and add permission tests immediately. The upstream baseline-migration strategy needs a separate, reviewed remediation before staging.

## Local verification evidence

Verified on 2026-07-14:

- dependencies installed successfully from `requirements.txt` on CPython 3.11.9;
- a private PostgreSQL 17.2 cluster started on `127.0.0.1:55432`;
- `scripts/bootstrap-local.ps1` completed successfully when rerun against the verified cluster;
- baseline migrations were generated and all migrations applied to `hydra_phase0`;
- `python manage.py check` returned no issues;
- `python manage.py makemigrations --check --dry-run` returned “No changes detected” after baseline generation;
- `python manage.py migrate --check` succeeded;
- `python manage.py test --verbosity 2` completed successfully after the discovery fix and reported zero executable tests;
- `scripts/run-local.ps1` cold-started a stopped PostgreSQL cluster, started Django without the reloader and returned HTTP 200 with `{"status":"ok"}` from `/health/`.

See `docs/LOCAL_DEVELOPMENT.md` for repeatable commands and known limitations.

## Reuse summary

- Reuse: authentication, Employee after hiring, Company/Department, selected attendance, notifications and current audit primitives.
- Extend: recruitment, onboarding, employee conversion, organization and reports.
- Wrap: existing permissions with explicit scope services/selectors; keep Szablonizator behind an export boundary.
- Replace: private document storage/delivery boundary.
- New: Person, legalization, arrivals, housing, location/team coordination, Hydra imports and scope-aware operational panels.

The detailed decision for every requested capability is in `docs/REUSE_MATRIX.md`.
