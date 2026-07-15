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
| `onboarding/` | Candidate onboarding stages/tasks and token portal | Extend after Person/private-document work |
| `attendance/` | Attendance, work records and late/early exceptions | Reuse for employees and operational exception views |
| `notifications/` | Database notifications and localized verbs | Reuse through domain services |
| `horilla_audit/` | Simple-history customization and diff UI | Reuse selectively |
| `horilla_documents/` | Employee document request metadata | Extend metadata where useful; replace private delivery |
| `report/` | Pivot reports and browser Excel exports | Extend with scope-aware Hydra selectors |
| `Dockerfile`, `entrypoint.sh`, `docker-compose.staging.yaml` | Hardened application image, fail-closed boot, and isolated staging stack | Task 045 staging boundary; upstream `docker-compose.yaml` remains development-only |
| `scripts/` | Local bootstrap plus staging deploy, smoke, backup, restore verification, and rollback helpers | Operational tooling with explicit safety gates |
| `docs/` | Audit and architecture decisions | Phase 0 deliverables |
| `hydra_documents/` | Private candidate-document storage, metadata, download authorization and access events | New shared security boundary; never served by generic `/media/` |
| `hydra_ops/` | Deployment readiness, public ready probe, and web-initializer containment | New staging operations boundary |

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
hydra_legalization/    legalization cases/status/responsibility/validity (TASK-2 implemented)
hydra_arrivals/        arrival plans and confirmations
hydra_housing/         facilities, rooms, beds and assignments
hydra_imports/         previewed, transactional imports
hydra_templates/       message templates and Szablonizator-compatible exports
hydra_links/           controlled public arrival and Location training links
hydra_reports/         scoped operational reports and audited CSV exports
```

No universal workflow/plugin/rule framework is planned. Apps should contain models, services, selectors, thin views/templates and focused tests.

## Input package note

Several supplied Markdown filenames did not match their internal headings (for example, files named as later tasks contained Phase 0 instructions). Phase 0 treated document content and headings as authoritative. No later business task was executed ahead of audit acceptance.
