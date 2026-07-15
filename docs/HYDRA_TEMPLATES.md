# Hydra message templates and Szablonizator export

## Status

Task `042-template-module.md` is implemented as the `hydra_templates` Django app. The module owns company-scoped, plain-text message templates, one explicit placeholder registry, deterministic previews and an authorized XLSX export for the separate Szablonizator desktop application.

No supplied task brief existed for 042. The implemented scope follows `TARGET_ARCHITECTURE.md`, `IMPLEMENTATION_DECISIONS.md`, the reuse matrix and the audited boundary in `SZABLONIZATOR_INTEGRATION.md`.

## Reuse decision

The solution is **WRAP**:

- Horilla `HorillaMailTemplate` remains available and unchanged for legacy email workflows;
- Hydra owns a narrower template type with explicit company scope and plain-text semantics;
- the existing Python/openpyxl dependency produces the compatible XLSX response;
- Szablonizator stays an independently deployed WPF/.NET desktop tool.

Hydra does not execute `.exe`, WPF, .NET, Office COM or server-side DOCX generation.

## Message template contract

`MessageTemplate` stores an immutable UUID, required Company, stable uppercase code, operator-facing name, language, plain-text subject/body and normal Hydra active/authorship metadata. The `(company, code, language)` tuple is unique.

Create and update views require the corresponding Django model permission and intersect the selected Company with the actor's active Hydra scope. Direct update URLs for another Company return 404.

Preview uses deterministic sample values and never sends a message or reads a Person record. Output is rendered through Django's normal escaping. Horilla's global XSS validator remains active as an additional input control.

## Placeholder registry

The registry in `hydra_templates.placeholders` is the only source of accepted identifiers for validation, preview and the XLSX `Dane` headers:

| Identifier | Meaning |
|---|---|
| `HYDRA_ID` | immutable Hydra identifier |
| `PASSPORT_NAME` | name exactly as in passport |
| `FIRST_NAME` | first name |
| `LAST_NAME` | last name |
| `DATE_OF_BIRTH` | ISO date of birth |
| `CITIZENSHIP` | two-letter citizenship code |
| `PREFERRED_LANGUAGE` | preferred language code |
| `PHONE` | phone number |
| `WHATSAPP_VIBER` | WhatsApp / Viber number |
| `EMAIL` | email address |
| `LIFECYCLE_STATE` | Hydra lifecycle code |
| `COMPANY_NAME` | current legal Company |
| `LOCATION_NAME` | current Location |
| `SECTION_NAME` | current Section |
| `TEAM_NAME` | current Team |

Tokens use `{{NAME}}`. Spaces immediately inside the braces are accepted. The identifier must begin with an ASCII letter or underscore, then contain only ASCII letters, digits, underscore, dot or hyphen, with a maximum of 128 identifier characters. Unknown names and any remaining unmatched brace are rejected. Display labels are never inferred as identifiers.

## Authorized XLSX export

The POST-only download requires `hydra_templates.export_template_data` and `hydra_people.view_person`. The actor may optionally limit it to one Company already in their active scope. The source still comes from `people_for_user`, so permission, effective grants and current assignments intersect. A forged Company is rejected before generation and creates no audit row. Exports are bounded to 10,000 records.

The workbook contract is:

- first visible sheet `Dane` and second visible sheet `Instrukcja`;
- registry identifiers in the first row, in stable order;
- one visible Person per row;
- values only, with no formulas, macros, hidden sheets or external links;
- dates serialized as `YYYY-MM-DD` text;
- all exported cells, including formula-sensitive leading characters, explicitly typed as literal text;
- freeze row, filter and bounded column widths for desktop usability.

The response uses `no-store, private`, `no-cache` and `nosniff`. It is not written to public media.

## Audit

Every successful response first creates one append-only `TemplateDataExport` row containing actor, time, filename, row count, SHA-256, selected filter and effective Company IDs. The database does not retain workbook bytes or cell values.

Instance save/delete and queryset update/delete are rejected after creation. Users with `view_templatedataexport` see their own ten latest exports; superuser is the explicit all-actor view.

## Verification

Focused PostgreSQL coverage contains 12 tests for the parser contract, malformed and unknown placeholders, Company scope, direct URL denial, missing permissions, out-of-scope form values, escaped no-write preview, legacy Horilla compatibility, workbook schema, scope, values-only behavior, checksum and append-only audit.

The complete implemented regression passes:

```text
Ran 142 tests - OK
```

`manage.py check`, `makemigrations --check --dry-run hydra_templates` and migration `hydra_templates.0001_initial` pass on PostgreSQL.

The generated QA workbook was independently imported with `@oai/artifact-tool`: it contained exactly the visible `Dane` and `Instrukcja` sheets, a 15-column registry, no formula records and a literal `=2+2` test value. Both sheets were rendered and visually checked.

Browser verification used the real PostgreSQL schema and the `hydra-qa` operator. At 390 x 844 pixels the module and create form had no horizontal overflow: document width was 380 pixels, cards ended at 363.2 pixels, table cells switched to block layout and form controls/actions fit within 316.8 pixels. The Templates navigation state was active.

## Deliberate limits

- Templates are plain text; the module does not provide an HTML email editor.
- Preview is sample-only and does not send email, SMS or notifications.
- There is no bulk template engine, automation system or generic merge-rule designer.
- The XLSX is a manual point-in-time handoff; Hydra does not control the desktop process.
- Server-side DOCX generation, output ZIP handling and desktop project synchronization remain deferred.
- Translation catalogs for new strings are not populated yet.

Tasks 043 public Hydra links, 044 scoped operational reports, and 045 hardened staging are now implemented; see `HYDRA_PUBLIC_LINKS.md`, `HYDRA_REPORTS.md`, and `HYDRA_STAGING.md`.
