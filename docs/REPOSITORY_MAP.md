# Repository map — Phase 0

## Source snapshots

| System | Repository and audited revision | Role in Hydra | Phase 0 handling |
|---|---|---|---|
| Horilla HRMS | `horilla/horilla-hr`, branch `1.0`, commit `11c4e3a2596c58f2381bda4c6bbc319a4430b097` | Django foundation and future Hydra codebase | Cloned as this repository; audited and bootstrapped |
| Current Hydra portal | `OleksandrKiris/citronex-hydra-project`, branch `main`, commit `2262497c6c53281b3bd55bee5b9eebc03064b582` | Public multilingual start/training-link portal | Audited read-only; remains deployed separately |
| Szablonizator | `OleksandrKiris/Szablonizator`, branch `main`, commit `fbd0fbdbeea02153f8f72d5ead72305d4bbb0150` | Local Windows XLSX-to-DOCX generator | Audited read-only; remains a separate application |

The two reference repositories are not vendored or added as submodules. Their runtimes must not be coupled to Django during the MVP.

## Horilla map

| Path | Responsibility | Hydra decision |
|---|---|---|
| `horilla/` | Django settings, middleware, root URLs and dynamic app configuration | Extend minimally; register Hydra apps explicitly |
| `base/` | Company, department, job/shift/work types, common views and company middleware | Reuse organization core; do not treat session filtering as authorization |
| `employee/` | Employee, work information, employee documents, permissions/imports | Reuse after hiring and link from Person |
| `recruitment/` | Recruitment campaigns, stages, candidates, surveys, interviews and candidate documents | Extend application records to point to Person |
| `onboarding/` | Candidate onboarding stages/tasks, locked creation service and token portal | Reused through the scoped Hydra arrival handoff; legacy Hydra-task mutation routes are blocked |
| `attendance/` | Attendance, work records and late/early exceptions | Reuse for employees and operational exception views |
| `notifications/` | Database notifications and localized verbs | Reuse as the compatibility transport behind Hydra recipient/scope/state policy |
| `horilla_audit/` | Simple-history customization and diff UI | Reuse selectively |
| `horilla_documents/` | Employee document request metadata | Extend metadata where useful; replace private delivery |
| `report/` | Pivot reports and browser Excel exports | Extend with scope-aware Hydra selectors |
| `Dockerfile`, `entrypoint.sh`, `docker-compose.staging.yaml` | Hardened application image, fail-closed boot, and isolated staging stack | Task 045 staging boundary; image construction also verifies the exact reviewed migration source manifest; upstream `docker-compose.yaml` remains development-only |
| `scripts/` | Local bootstrap plus migration-manifest verification, staging deploy, smoke, backup, archive validation, restore verification, and rollback helpers | Operational tooling with exact normalized migration hashes, an empty-schema initial-deploy proof, cold-writer stop, hostile-member rejection and explicit rollback gates |
| `deployment/` | Pinned Django auth compatibility source and exact first-party migration SHA-256 manifest | Reviewed schema-source boundary shared by CI and image construction |
| `docs/` | Audit and architecture decisions | Phase 0 deliverables |
| `hydra_documents/` | Private candidate-document quarantine/scanning, storage, lifecycle policy, scoped delivery and access events | Shared security boundary; never served by generic `/media/`; fail-closed without ClamAV |
| `hydra_housing/` | Location-scoped facilities, optional buildings/floors, rooms, beds, expiring/confirmed reservations, stays, atomic moves and append-only lifecycle facts | New workforce-accommodation boundary; deterministic Person/bed locking, maintenance expiry and readiness prevent overlap, silent hold promotion or partial moves |
| `hydra_tasks/` | Person/Company-scoped universal tasks, approved domain-target resolution, append-only lifecycle and durable delivery evidence | New focused task boundary wrapping Horilla notifications; not a generic workflow engine or replacement for domain-owned task concepts |
| `hydra_notifications/` | Scoped notification envelopes, reviewed PII-free kinds, append-only state, preferences, center and durable generic-email outbox | Reuse/wrap Horilla rows; current target visibility and recipient ownership remain mandatory at list, mutation, open and email send |
| `hydra_onboarding/` | Company-scoped immutable published courses/lessons/quizzes, deterministic fixed-field assignment rules and append-only attempt/confirmation evidence | New internal-learning boundary extending the reused Horilla onboarding/handoff; exact version fingerprints, Person scope and idempotent assignment prevent drift or parallel onboarding workflows |
| `hydra_ops/` | Deployment readiness, public ready probe, single-owner maintenance worker, portal-email dispatch and lifecycle recovery | New staging/production operations boundary |

## Current Hydra portal map

| Path | Responsibility | Migration treatment |
|---|---|---|
| `index.html` | Single-page UI, nine translations, intro/audio flow and location links | Preserve behavior and links during MVP |
| `assets/audio/intro-*.mp3` | Local intro audio for nine languages | Keep public and versioned in current portal |
| `assets/brand/` | Portal branding | Reuse only after asset/brand approval |
| `manifest.webmanifest` | Installable PWA metadata | Keep on current GitHub Pages deployment |
| `sw.js` | Same-origin network-first cache with offline fallback | Keep; avoid caching authenticated Hydra data |
| `docs/TLUMACZENIA_NATIVE_CHECK.md` | Native-speaker review checklist | Preserve as content QA requirement |

The public location URLs are catalogued in `docs/HYDRA_PORTAL_MIGRATION.md`.

## Szablonizator map

| Path | Responsibility | Integration treatment |
|---|---|---|
| `src/Szablonizator.Core/` | Models, mapping contracts and placeholder rules | Reuse behavior/specification, not .NET code |
| `src/Szablonizator.Infrastructure/SpreadsheetService.cs` | XLSX creation/read and formula rejection | Source for future compatibility tests |
| `WordTemplateService.cs` | Safe DOCX inspection and replacement | Source for future behavior/security tests |
| `OfficePackageSafety.cs` | OOXML/ZIP validation | Treat as minimum future server-side requirements |
| `DocumentGenerationService.cs` | Preflight, fingerprints, resumable transactional batches and ZIP | Preserve invariants in any future web implementation |
| `ProjectStore.cs` | Atomic `.szablon` project JSON | No Django runtime integration |
| `src/Szablonizator.App/` | WPF UI | Keep entirely separate |
| `tests/Szablonizator.Tests/` | Unit/integration/security tests | Re-express behavior tests in Python only if web generation is approved later |

## Planned Hydra additions after Phase 0 approval

The exact app split remains subject to task-by-task implementation, but the audit supports this minimal direction:

```text
hydra_people/          canonical Person plus scoped Horilla recruitment extension (TASK-1/TASK-2 implemented)
hydra_coordination/    Location, Section/Stage, Team, scope and assignments (TASK-1 implemented)
hydra_shell/           shared branding, responsive navigation and public portal boundary (TASK-1 implemented)
hydra_documents/       private candidate documents and access logging (TASK-2 implemented)
hydra_legalization/    cases, scoped workload/deputies, audited responsibility, validity, reminders, authority evidence and renewal lineage (TASK-2 extended)
hydra_arrivals/        arrivals, controlled Horilla onboarding handoff and durable portal-email outbox
hydra_housing/         scoped Facility/Building/Floor/Room/Bed and effective/temporary assignments (TASK-020/021/022 implemented)
hydra_imports/         previewed transactional imports with bounded audited source-data redaction
hydra_templates/       message templates and Szablonizator-compatible exports
hydra_links/           controlled public arrival and Location training links
hydra_reports/         scoped operational reports and audited CSV exports
hydra_tasks/           scoped Person/domain tasks, lifecycle events and durable notification delivery
hydra_notifications/   scoped in-app center, state history, preferences and generic email delivery
hydra_onboarding/      immutable learning content, deterministic assignment rules and completion evidence
```

No universal workflow/plugin/rule framework is planned. Apps should contain models, services, selectors, thin views/templates and focused tests.

## Input package note

Several supplied Markdown filenames did not match their internal headings (for example, files named as later tasks contained Phase 0 instructions). Phase 0 treated document content and headings as authoritative. No later business task was executed ahead of audit acceptance.
