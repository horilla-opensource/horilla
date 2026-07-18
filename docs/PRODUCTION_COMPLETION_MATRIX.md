# Hydra production completion matrix

## Purpose

This matrix compares the current repository with the 36 tasks and cross-cutting
rules in the Full Engineering Package. It is a release-control document, not a
claim that an existing screen or model completes a production workflow.

Status meanings:

- **Implemented** -- current code and automated evidence cover the stated task;
- **Partial** -- useful behavior exists, but one or more explicit production
  requirements are absent or not verified;
- **Missing** -- no equivalent complete production workflow exists;
- **External gate** -- repository support exists, but target-environment or
  accountable-owner evidence is still required.

## Task-by-task state

| Task | Current state | Evidence and remaining production work |
|---|---|---|
| 001 legacy HR platform audit | Implemented | `UPSTREAM_AUDIT.md`, `REPOSITORY_MAP.md`, `REUSE_MATRIX.md` and the pinned upstream revision document reuse and upgrade risks. |
| 002 local Docker stack | Partial | A hardened staging Compose stack exists. The verified local path is Windows/PostgreSQL; the package's Redis/Celery development topology was deliberately replaced for implemented recurring work by one PostgreSQL-advisory-lock maintenance process. The production decision and Linux execution still require evidence. |
| 003 app skeleton/settings/health | Partial | Explicit Hydra apps, URLs, liveness/readiness and environment configuration exist. Settings are environment-driven rather than split into the package's proposed module layout; target-host checks remain external. |
| 004 branding/navigation | Implemented | `hydra_shell` provides role-aware, server-rendered responsive navigation and preserves the public portal boundary. |
| 005 organization hierarchy | Implemented | legacy HR platform Company/Department are reused; Location, Section, Team and effective assignments/scopes are implemented in `hydra_coordination`. |
| 006 scoped RBAC | Implemented | Role permissions are intersected with effective Company/Location/Department/Section/Team scope; direct-object denial tests cover the implemented domains. Partner-agency ownership is not yet a general scope dimension and remains tracked below. |
| 007 Person identity | Implemented by EXTEND/WRAP | `hydra_people.Person` is canonical and links many legacy HR platform Candidate applications and at most one Employee. Separate duplicate CandidateProfile/EmployeeProfile tables were intentionally not created. |
| 008 immutable audit/timeline | Implemented by REUSE/WRAP | Django auditlog and append-only domain histories remain authoritative. `hydra_people.timeline` now provides one scope- and source-permission-aware Person projection without copying PII or dual-writing facts. |
| 009 vacancies/applications | Implemented by EXTEND | legacy HR platform Recruitment/Stage/Candidate are reused and wrapped by scoped PersonApplication services and selectors. |
| 010 recruitment workflow | Implemented by REUSE/EXTEND/WRAP | legacy HR platform keeps Recruitment/Stage/Candidate and its pipeline UI. Linked applications now use one locked, scoped transition service, configurable directed requirements, authorized reasoned override and append-only history; direct save/bulk bypasses and the main legacy pipeline mutation routes are closed. |
| 011 private documents | Implemented by REPLACE/EXTEND/WRAP | Private quarantine, fail-closed ClamAV, scoped delivery, access/lifecycle evidence, retention/legal hold, Company-scoped fixed-field types, snapshotted per-type rules and immutable explicit replacement chains are implemented. |
| 012 duplicate detection | Implemented by EXTEND/WRAP | Deterministic privacy-minimising suggestions never auto-merge. Scoped comparison, explicit field decisions, signed/stale-safe conflict preview, atomic canonical merge, immutable source alias, preserved identifiers and append-only reference/evidence history are implemented. |
| 013 candidate conversion | Implemented | One idempotent locked service creates/links legacy HR platform Employee without creating a second Person and preserves conversion decisions. |
| 014 legalization configuration | Implemented by EXTEND/WRAP | Company/global fixed-field procedures, normalized status rows, document requirements and approved authorities are configurable through scoped server-rendered screens. Cases keep immutable policy snapshots; authority facts keep the exact case-policy authority snapshot; changes are audited and affect future cases only. Unknowable legacy authority mappings fail readiness until a superuser performs the one-time reasoned, append-only adoption. |
| 015 legalization cases | Implemented | Scoped cases, transitions, append-only status/work/authority/renewal facts, evidence and readiness invariants are implemented. |
| 016 expiry reminders | Implemented with an approved alternative | Idempotent reminders and expiry run in the single-owner maintenance process rather than Celery beat; durable events and retry/exhaustion health are present. |
| 017 universal tasks | Implemented by NEW + REUSE/WRAP | `hydra_tasks` provides one scoped, idempotent and version-locked task linked to Person and an approved domain target, with append-only events, durable privacy-safe assignment notifications, Person timeline/UI and overdue coordinator integration. legacy HR platform notifications are wrapped; its incompatible project/onboarding/helpdesk task ownership is not duplicated. |
| 018 notifications | Implemented by REUSE/WRAP | `hydra_notifications` wraps legacy HR platform in-app rows with current-recipient target scope, fixed PII-free kinds, a paginated responsive center, versioned append-only read/archive state, opt-in generic email with durable leases/retry/dead-letter evidence, opt-in browser sound and an explicit no-native-push policy. Legacy rows are backfilled/wrapped and their mutation endpoints are POST-only and recipient-scoped. |
| 019 arrivals | Implemented | Scoped planning, confirmation/no-show, durable reminders, escalation, history and coordinator ownership are implemented. |
| 020 housing hierarchy | Implemented | Location-scoped Facility/Building/Floor/Room/Bed hierarchy, deterministic legacy floor backfill, scoped responsive management UI, validation, audit fields and readiness integrity are implemented. Keys and maintenance issues were not included in the TASK-020 contract and remain outside this slice. |
| 021 reservations | Implemented | Conflict-safe future periods now support optional expiring temporary holds, forward-only reasoned renewal, confirmation, cancellation, automatic locked system expiry, append-only evidence and maintenance/readiness integration. |
| 022 assignments/moves | Implemented | Person/bed overlap prevention, deterministic locking, atomic move, cancellation/end and paired append-only evidence are implemented. |
| 023 public onboarding portal | Partial | Stable external multilingual portal links are preserved and legacy HR platform's token portal is wrapped. The package's later Django-hosted multilingual public location content is not implemented. |
| 024 onboarding content model | Implemented by EXTEND/WRAP + NEW MODULE | legacy HR platform stages/tasks, token portal and controlled handoff remain authoritative. `hydra_onboarding` adds Company/language-scoped immutable published CourseVersion/Lesson/Quiz content, SHA-256 payload fingerprints, exact assignment snapshots, append-only attempts/confirmations/events, scoped UI, Person timeline and readiness integrity. |
| 025 onboarding rules | Implemented | Explicit Company/course rules match Location, Department, Team, preferred language and worker type with deterministic priority/specificity, published-language fallback, idempotent Person/course assignment and confirmed-arrival handoff integration. No generic rule engine was added. |
| 026 import center | Partial | Candidate XLSX preview, normalization, duplicate blocking, transactional apply, idempotency, retention and audit exist. CSV, mapping UI, reusable import types, downloadable error file, 5,000-row/background execution and broader references remain absent. |
| 027 employee assignments | Implemented | Effective-dated Team/Department history, locked reassignment, legacy HR platform work-information projection and onboarding reconciliation are implemented. |
| 028 daily presence | Missing | The brigadier panel reads legacy HR platform attendance/leave exceptions, but Hydra has no expected roster, exception write workflow or reasoned daily confirmation fact. |
| 029 brigadier dashboard | Partial | Direct-Team mobile roster and exception interpretation are scope-safe. Daily confirmation, operational issue/task actions and the full production dashboard contract remain absent. |
| 030 coordinator dashboard | Implemented for current domains | Location-scoped arrival, assignment, attendance, housing and universal overdue-task exceptions are provided. Data-quality findings will need integration when TASK-033 exists. |
| 031 Szablonizator/templates | Partial | Company-scoped safe placeholders, preview and audited compatible XLSX export exist. Versioned multilingual/channel templates and server DOCX/ZIP generation are not implemented; the WPF runtime remains correctly separate. |
| 032 reports/saved filters | Partial | A scoped, formula-safe, audited CSV operational report exists. Saved filters, XLSX/PDF reports, background exports and a broader report catalog are missing. |
| 033 data-quality dashboard | Missing | Readiness detects selected integrity failures, but there is no scoped finding lifecycle/dashboard for duplicates, missing data, expired documents and assignment problems. Findings must never auto-correct. |
| 034 backup/restore | Implemented locally; external evidence pending | Cold-writer backup, hashes, hostile-archive validation and isolated restore verification are implemented. Scheduled encrypted off-host retention and a restore from the actual target stack remain external gates. |
| 035 staging | External gate | Hardened image/Compose/CI/scripts/readiness exist. Linux image/Compose, TLS, secrets, SMTP, ClamAV, monitoring and target-host smoke evidence have not been executed on this workstation. |
| 036 acceptance suite | Partial/external gate | The PostgreSQL regression currently passes 448/448 with one environment-dependent skip, plus focused browser journeys and a local restore drill. Production-scale import/performance, target recovery, all role journeys, legal review and owner sign-off remain required. |

## Priority order

The next dependency-safe order is:

1. TASK-026 import center and TASK-028 daily presence;
2. TASK-029/030 integration, TASK-031/032 reporting/templates and TASK-033 data quality;
3. target TASK-034/035/036 recovery, environment and acceptance gates.

No item marked Partial, Missing or External gate is a production **GO**.
