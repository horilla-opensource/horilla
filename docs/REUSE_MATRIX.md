# Hydra reuse matrix — Phase 0

Decision vocabulary:

- **REUSE** — use the existing component with configuration or small calling-code changes.
- **EXTEND** — retain the component and add Hydra-specific fields/relations/services around it.
- **WRAP** — keep the component behind a Hydra policy or integration boundary.
- **REPLACE** — do not use the existing behavior for this security/domain boundary.
- **NEW MODULE** — no sufficient Horilla component exists.

| Hydra need | Existing Horilla/source capability | Decision | Required change | Primary risk/control |
|---|---|---|---|---|
| User authentication | Django auth, sessions, password validation, optional 2FA/LDAP/Microsoft auth | **REUSE** | Keep `User`, Groups and permissions; configure deployment secrets and selected auth methods | Do not rewrite auth or use employee email as pre-employment identity |
| Employee | `employee.Employee` and `EmployeeWorkInformation` | **EXTEND** | Implemented: hired-only, idempotent Person-to-Employee service, inactive account provisioning and append-only source/decision snapshot | Unique email, conflicting links and unsafe password defaults are rejected/wrapped |
| Candidate identity | `recruitment.Candidate` application record | **NEW MODULE** | Create `hydra_people.Person`; link one Person to many applications and optionally one Employee | Prevent duplicate people without forcing email |
| Recruitment pipeline | Recruitment, Stage, Candidate, managers, interviews, ratings, surveys | **EXTEND** | Keep campaign/stage UX; link Candidate/application to Person; move Hydra transitions into services | Candidate currently owns duplicated identity fields |
| Organization | Company, Department, JobPosition/Role, shifts | **EXTEND** | Implemented: normalized Location/Section/Team, effective-dated assignments and transactional projection of the current employee assignment into Horilla work information | Do not overload Company or free-text work location; clear incompatible positions on department change |
| Scoped permissions | Django permissions, manager decorators, session company manager | **WRAP** | Add explicit user role/scope assignments, policy functions and mandatory scoped selectors; test direct URLs | Existing company filter can be bypassed or disabled with `all` |
| Onboarding | Onboarding stages, tasks, candidate task state and token portal | **EXTEND** | Link via Person/application; keep public training links separate during MVP | Existing onboarding conversion assumes email/User |
| Attendance | Attendance, activities, work records, validation, late/early | **REUSE** | Consume only for linked employees and scoped operational exception lists | Not suitable for arrival/pre-employment status |
| Notifications | Local Django notifications implementation and `notify` signal | **REUSE** | Emit after committed domain actions; avoid personal data in verb/JSON | Permission-aware redirects and retention need review |
| Audit/history | django-auditlog for all models plus simple-history on selected models | **EXTEND** | Adopt one history convention per Hydra model; add explicit transition history and document access log | Overlapping audit systems can create gaps/confusion |
| Private documents | Employee/candidate document metadata plus generic `/media/` delivery | **REPLACE** | Private storage, opaque keys, authorized streaming/download service, access log, content validation | Generic media endpoint checks login but not object scope |
| Legalization | No equivalent | **NEW MODULE** | Implemented in `hydra_legalization`: case, controlled status, owner, validity, deadlines and private document relations | Sensitive data and deadline correctness |
| Arrivals | No equivalent | **NEW MODULE** | Implemented in `hydra_arrivals`: scoped plans, transport/arrival facts, confirmation/no-show, immutable history and coordinator selectors | Kept separate from attendance and public instructions |
| Housing | No equivalent | **NEW MODULE** | Facility/room/bed inventory and effective assignments with conflict constraints | Prevent overlapping bed assignments transactionally |
| Brigadier panel | Employee/attendance data and reporting hierarchy only | **EXTEND + WRAP** | Implemented: mobile-first direct-Team roster and exception view composed from effective Hydra assignments and Horilla attendance | Company/location grants never widen the panel; another Team by URL returns 404 |
| Coordinator panel | Reports and recruitment/employee lists | **NEW + WRAP** | Implemented: direct-Location, read-only exception dashboard composing arrivals, effective assignments and legalization; housing remains deferred | Company/narrower grants never widen the panel; another Location by URL returns 404 |
| Templates | Horilla email templates; separate Szablonizator desktop generator | **WRAP** | Implemented in `hydra_templates`: company-scoped plain-text templates, one strict placeholder registry, deterministic preview and audited compatible XLSX export; desktop app remains external | Do not run `.exe`, WPF or .NET on server; values only, explicit scope and SHA-256 audit |
| Public Hydra links | Existing static portal and independently hosted arrival/training sites | **WRAP** | Implemented in `hydra_links`: controlled global arrival and per-Location training records, strict public URL builder and contextual scoped rendering | Keep public service worker outside authenticated routes; send only language and `from=hydra`, never identity or tokens |
| Imports | Employee spreadsheet import and pandas/openpyxl utilities | **NEW MODULE** | Implemented in `hydra_imports`: candidate/Person preview, validation, duplicate matching, idempotency and one transaction | Existing employee import is not a safe candidate import |
| Reports | Horilla pivot reports and browser Excel export | **EXTEND + WRAP** | Implemented in `hydra_reports`: selector-backed operational report, scoped filters, server-generated CSV and append-only export audit | Existing broad managers and client-side exports are not authorization boundaries; exact permissions, scope snapshots, formula neutralization and no-store headers are enforced |

## Module-level direction

### Reused without a parallel Hydra clone

- Django authentication and permission records;
- Horilla Employee/WorkInformation after hiring;
- Company and Department;
- recruitment stage/campaign UI;
- onboarding task concepts;
- employee attendance;
- database notifications;
- auditlog/simple-history primitives.

### Newly owned by Hydra

- canonical Person and lifecycle;
- physical/operational hierarchy and historical assignments;
- role scope grants and scope selectors;
- legalization, arrival and housing domains;
- private document authorization/access logs;
- candidate imports and operational panels.

### Explicitly outside MVP runtime

- Priva;
- native mobile app;
- React SPA or microservices;
- generic workflow/rule/plugin engines;
- server execution of Szablonizator/WPF;
- complete migration of all public training pages.

## Gate for each subsequent task

Before adding a component, the task must cite this matrix, inspect the current Horilla equivalent again, and state the reuse decision. Completion requires migrations, server-side scope tests, Django checks, documentation and mobile verification where applicable.
