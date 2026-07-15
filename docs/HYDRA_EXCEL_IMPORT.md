# Hydra candidate Excel import — TASK-2

## Status and audit decision

Implemented on 2026-07-14 as the smallest complete candidate-import vertical slice.

The required Horilla inspection found two employee spreadsheet paths. `employee_import()` reads a workbook with pandas and creates users/employees row by row while collecting broad exceptions. `work_info_import()` validates an employee-specific header set, then invokes multiple independent `bulk_create_*` functions and starts password work in a thread. Neither path stores a preview, applies Hydra Person scope, produces a stable import fingerprint or guarantees a single transaction across Person and Candidate creation.

The implementation decision is:

- **NEW MODULE** for `hydra_imports`, its preview session and row decisions;
- **REUSE** the XLSX container and openpyxl value parser already present in Horilla's dependencies;
- **WRAP** `hydra_people.save_person()` and `create_candidate_application()` inside one outer transaction;
- preserve the existing Horilla employee imports unchanged and operational;
- do not add a generic ETL framework, SPA, microservice or desktop runtime.

## Complete vertical slice

The server-rendered workflow at `/hydra/imports/candidates/` provides:

1. a downloadable, versioned `Hydra_Candidate_Import_Template.xlsx`;
2. a scoped open Recruitment and Job Position selector;
3. secure `.xlsx` container checks and complete row validation;
4. a persisted preview with valid, duplicate and error counts;
5. deterministic duplicate reasons per row;
6. an apply action enabled only for a clean preview;
7. one atomic Person + Horilla Candidate + canonical link transaction;
8. idempotent preview fingerprints and apply behavior;
9. desktop and mobile views integrated with Hydra Recruitment navigation.

The source workbook is never stored. Hydra retains only the safe filename, SHA-256, stable fingerprint, normalized preview values and row hashes required for a reviewed apply and audit trail.

## Workbook contract

Only `.xlsx` is accepted. The workbook must contain a worksheet named `Candidates` whose headers exactly match this order:

```text
passport_name, first_name, last_name, date_of_birth, gender, citizenship,
preferred_language, email, phone, whatsapp_viber, candidate_mobile
```

The first eight fields are required; the three phone fields are optional. Dates must be real Excel dates or ISO `YYYY-MM-DD`. Gender and preferred-language codes use the same choices as `hydra_people.Person`; citizenship is a two-letter ISO code. A workbook is limited to 500 non-empty candidate rows and 5 MB.

The ZIP container is checked before parsing: encrypted/path-like entries, more than 200 entries and more than 20 MB uncompressed data are rejected. Active workbook links are not loaded. A formula in any candidate data cell rejects the whole workbook; preview accepts values only.

The Recruitment and Job Position are selected in the server form rather than repeated in every row. This prevents ambiguous text matching and ensures every row is applied to one reviewed, currently scoped intake.

## Validation and duplicate policy

All rows are normalized before preview. Names collapse repeated whitespace, emails are lowercased, citizenship is uppercased and domain validators run for email and phone fields.

A clean row is marked Duplicate when any deterministic rule matches:

- the same normalized `(passport_name, date_of_birth, citizenship)` appears more than once in the workbook;
- the same normalized email appears more than once in the workbook;
- an existing Hydra Person has that exact normalized passport identity;
- an existing Candidate in the selected Recruitment has that email case-insensitively.

Every copy of an intra-workbook duplicate is marked, not just the later row. Hydra does not auto-merge or silently attach an existing Person in this MVP. If any row is invalid or duplicate, the complete session is Blocked. The operator corrects the source and creates a new preview.

## Authorization and scope

The workflow requires the custom `hydra_imports.import_candidate` permission and `view_candidateimportsession`, plus the existing permissions needed by the wrapped services:

- `hydra_people.add_person`, `view_person`, `change_person`, `link_candidate`;
- `recruitment.add_candidate`, `view_candidate`, `view_recruitment`.

The selected Recruitment must be open, active and returned by `recruitments_for_user()`. Its Job Position must belong to its current open positions. Services repeat these checks during preview and apply, so a stale browser form cannot bypass scope.

Non-superusers see only preview sessions they created and only while the Recruitment remains in their current scope. Direct UUID access by another importer returns HTTP 404. The selected-company session value is not an authorization input.

## Transaction and idempotency

The preview fingerprint is SHA-256 over file SHA-256, actor, Recruitment and Job Position. Uploading the same workbook to the same target by the same actor returns the existing session.

Apply locks the session and every row. It rechecks permissions, current Recruitment scope/state, target position and preview integrity. Each valid row calls the existing `save_person()` and `create_candidate_application()` services inside one outer `transaction.atomic()` block. A failure in any row rolls back all Persons, Candidates, PersonApplication links, row result links and session state.

After success the session records Applied timestamp and actor. A second apply returns the already-applied session without creating another record.

## Migration and files

`hydra_imports/migrations/0001_initial.py` creates:

- `CandidateImportSession`, its stable fingerprint, target, counts, status and apply audit fields;
- `CandidateImportRow`, normalized data, decision/reason, source row hash and created-object links;
- unique `(session, row_number)` plus owner/status, recruitment/status and row/outcome indexes;
- the `import_candidate` action permission.

Both models are read-only in Django admin. Normal writes must go through the import services.

## Automated verification

Focused tests cover:

- HTTP 403 without the custom import permission;
- form and service enforcement of Recruitment/position scope;
- normalization, persisted counts and stable hashes;
- duplicate identity/email inside one workbook, marking every copy;
- existing Person identity and existing Recruitment email duplicates;
- rejection of formulas and changed headers without a preview write;
- owner-only preview UUIDs;
- successful Person/Candidate/PersonApplication creation;
- apply idempotency and blocked-preview denial;
- forced second-row failure with complete rollback;
- template download and continued operation of Horilla's employee importer.

The final PostgreSQL 17 acceptance run applied `hydra_imports.0001_initial` and passed the combined 73/73 Hydra tests. `manage.py check`, `makemigrations --check --dry-run`, `migrate --check`, Python compilation, `pip check` and `git diff --check` also passed.

The XLSX template was generated with `@oai/artifact-tool`, inspected at key ranges and rendered on all three worksheets. The formula scan returned no formulas on Candidates, Instructions or Example. The generated browser-QA workbook was then parsed by the production parser as one valid row with the expected date and normalized email.

Browser QA used the real local Django/PostgreSQL stack and scoped `hydra-qa` account. A one-row preview reported Ready, 1 valid, 0 duplicates and 0 errors. Applying it created Person `QA IMPORT PERSON 2026`, a standard Horilla Candidate and their canonical link; the UI changed to Applied and exposed both scoped detail links. Recruitment remained the single active Hydra navigation item and browser logs contained no errors or warnings.

At 1280 × 720 the upload form used a 998 px content card without horizontal overflow. At 390 × 844 both upload and applied-preview pages measured 380 px document width, the form collapsed to one column, preview/recent rows switched to mobile cards, scoped Person/Candidate links remained visible and there was no horizontal overflow. The temporary viewport override was reset after verification.

## Manual verification

1. Grant an importer the permissions listed above and a current Hydra scope grant for the target Recruitment company.
2. Open `/hydra/recruitment/`, choose **Import candidates**, and download the template.
3. Enter at least one new identity in `Candidates`; keep headers and worksheet name unchanged.
4. Select an open Recruitment and one of its positions, upload the file and confirm the preview values/counts.
5. Apply a clean preview and confirm links open both the new Hydra Person and standard Horilla Candidate application.
6. Upload the same file/target again and confirm the existing applied session is returned without duplicates.
7. Add a repeated email or an existing passport identity and confirm both preview reason and disabled apply action.
8. Try another importer's preview UUID or an out-of-scope Recruitment and confirm 404/form denial.
9. Repeat upload and preview at a viewport no wider than 390 px and confirm no horizontal overflow.

## Known limitations and next task

- Duplicate matches are exact normalized identity/email rules; transliteration, fuzzy names and passport-number matching are not attempted.
- Duplicate resolution is source-file correction; reviewed merge/link decisions are deliberately deferred.
- One workbook targets one Recruitment and Job Position.
- Preview rows contain normalized personal data and currently require operational retention/cleanup policy before production rollout.
- Password-protected workbooks, formulas, `.xls`, CSV and macro-enabled files are intentionally unsupported.
- Async imports and files above 500 rows are out of MVP scope.
- The next numbered task is `030-arrivals.md`.
