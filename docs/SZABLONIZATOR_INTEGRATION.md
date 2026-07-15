# Szablonizator integration strategy

## Audited snapshot

- Repository: `OleksandrKiris/Szablonizator`
- Branch: `main`
- Commit: `fbd0fbdbeea02153f8f72d5ead72305d4bbb0150`
- Commit date: 2026-07-13
- Declared application version: 0.5.0

## Architecture

Szablonizator is a portable Windows x64 WPF application targeting .NET 10:

- `Szablonizator.Core` — domain models, contracts and placeholder/mapping rules;
- `Szablonizator.Infrastructure` — XLSX/DOCX processing, project storage, preflight, generation and ZIP;
- `Szablonizator.App` — WPF interface;
- `Szablonizator.Tests` — unit, integration and security tests.

It works locally without a server, login, telemetry, automatic updates or intended network calls. The application is not a Django module.

## Inputs and outputs

### Inputs

- `.xlsx` data workbook;
- `.docx` Word template without macros;
- optional `.szablon` JSON project file containing variables, paths and mapping profiles.

The preferred workbook uses `Dane` as the data sheet. Row 1 contains unique column names; each later non-empty row creates one document. Formulas are rejected and must be replaced by values.

### Outputs

- one DOCX for each non-empty spreadsheet row;
- `raport-generowania.csv` in a successful batch;
- `raport-bledow-<fingerprint>.csv` when validation or generation fails;
- optional atomically published ZIP;
- a separate timestamped batch directory.

## Placeholder and mapping contract

Valid placeholders match:

```text
{{NAME}}
{{EMPLOYEE.NAME}}
{{START-DATE}}
```

The identifier must begin with ASCII letter or underscore, then contain only ASCII letters, digits, `_`, `.`, or `-`, with a maximum of 128 characters. Spaces immediately inside braces are accepted. Malformed remaining braces cause template rejection.

Variables can be sourced from:

- one spreadsheet column;
- a constant;
- an explicitly empty value;
- two columns joined with a configured separator.

Optional formatting attempts Polish/invariant date or number parsing. Output filename patterns can reference mapped values, raw columns and special `{{LP}}`. Invalid filename characters are replaced, `.docx` is enforced, names are bounded, Windows reserved names and case-insensitive duplicates are rejected.

Word replacement covers document paragraphs, tables, headers, footers, footnotes, endnotes and comments because all relevant OOXML parts/paragraph runs are compiled. The engine can replace a placeholder split across Word text runs.

## Security controls worth preserving

The source implements controls that should become minimum acceptance tests for any later web implementation:

- `.xlsx`/`.docx` extension and 50 MB input limit;
- at most 5,000 package entries and 250 MB total uncompressed content;
- 100 MB single-entry and 20 MB XML limits;
- compression-ratio checks for zip bombs;
- duplicate and traversal-like ZIP entry rejection;
- prohibited DTD and null XML resolver;
- rejection of macro declarations/VBA, ActiveX, OLE/embedded objects, custom UI, web extensions and alternative chunks;
- rejection of all external OOXML relationships, including external links;
- rejection of spreadsheet connections, query tables and external links;
- rejection of spreadsheet formulas;
- at most 500 columns and 100,000 records;
- no Word/Excel COM automation and no expression/script evaluation;
- locked NuGet dependency files and documented audit/signing process.

The strict external-relationship rule also rejects harmless hyperlinks. This is an intentional security trade-off in the desktop tool and must be explicitly decided, not accidentally weakened, in a future server implementation.

## Transactional generation behavior

The generator performs a complete preflight before rendering:

1. validate record count and output folder;
2. require exactly one mapping for each Word variable;
3. validate referenced columns and constants;
4. plan and sanitize every filename;
5. reject reserved or duplicate filenames;
6. calculate a SHA-256 batch fingerprint over template, pattern, columns, mappings and all ordered values.

Rendering then:

- compiles the Word template once;
- renders up to four documents concurrently;
- writes each result through a temporary file;
- stores a SHA-256 completion marker per document;
- keeps partial output under hidden `.szablonizator-work`;
- publishes the completed directory with one directory move;
- verifies hashes before resuming an interrupted batch;
- writes reports atomically;
- creates ZIP through a temporary file and atomic move.

The technical resume manifest contains fingerprints, counts, target folder and time, not cell values. The work directory still contains generated documents and therefore contains personal data; Hydra procedures must account for its retention and machine access.

## MVP decision

Keep Szablonizator separate. Specifically:

- do not copy WPF UI into Hydra;
- do not invoke `Szablonizator.exe` from a browser or Django worker;
- do not add .NET runtime or COM/Office to the web server;
- do not translate the C# code mechanically into Python;
- do not upload desktop project files automatically.

Hydra's MVP integration boundary is a manually downloaded XLSX export with a documented schema and consistent placeholder names. Hydra may record who generated an export, when, which scoped records it contained and its SHA-256 checksum. The export must exclude data the user cannot access.

## Proposed MVP export contract

The exact columns belong to the later template/export task, but the contract should follow these rules:

- first sheet named `Dane`;
- first row contains unique stable uppercase identifiers compatible with the placeholder regex;
- values only, never formulas, macros, external links or hidden personal-data sheets;
- dates serialized in one documented format, preferably ISO `YYYY-MM-DD` unless an existing template requires another value;
- one record per row and one immutable Hydra record identifier for reconciliation;
- workbook contains a human-readable instruction sheet;
- server validates user scope before building the dataset;
- export action and record count are audited;
- generated file is delivered through an authorized, short-lived response and is not left in public media.

Placeholder names should be maintained in one Hydra registry/document, not inferred from Polish display labels. Compatibility tests should open exported XLSX with the current `SpreadsheetService` expectations.

## Implemented Hydra boundary

Task 042 implements this contract in `hydra_templates`. The stable ordered registry is:

`HYDRA_ID`, `PASSPORT_NAME`, `FIRST_NAME`, `LAST_NAME`, `DATE_OF_BIRTH`, `CITIZENSHIP`, `PREFERRED_LANGUAGE`, `PHONE`, `WHATSAPP_VIBER`, `EMAIL`, `LIFECYCLE_STATE`, `COMPANY_NAME`, `LOCATION_NAME`, `SECTION_NAME`, `TEAM_NAME`.

The POST-only export requires `export_template_data` plus `view_person`, starts from the standard scoped Person selector, optionally narrows to one authorized Company and caps output at 10,000 rows. `Dane` and `Instrukcja` are the only sheets and both are visible. Every cell, including formula-sensitive leading characters, is explicitly typed as text; dates are ISO text. The response is private/no-store and no workbook is persisted in media.

Each successful response creates an append-only audit row with actor, time, filter, effective Company IDs, row count, filename and SHA-256. Workbook bytes and personal cell values are not retained in the audit table. See `HYDRA_TEMPLATES.md` for the complete permission, UI and verification record.

## Deferred web document generation

A server-side `hydra_document_generation` module may be considered only after the HR core, scope policy, private documents and operations modules work. Its requirements must be ported as black-box behavior and tests:

- safe template upload and OOXML inspection;
- placeholder discovery and mapping;
- full preflight;
- deterministic filename plan;
- transactional/background batch generation;
- cancellation/resume or an explicitly approved simpler retry model;
- access-controlled output/ZIP;
- audit, retention and cleanup;
- resource quotas and antivirus/content scanning;
- parity fixtures against independently generated expected documents.

The web module must select maintained Python libraries independently and undergo its own security review. Desktop runtime integration remains prohibited.

## Verification status

The source and tests were audited. .NET SDK is not installed on the Phase 0 workstation, so `dotnet test` was not executed locally. The repository declares .NET SDK 10.0.301, locked NuGet packages and xUnit tests covering placeholder rules, spreadsheet behavior, OOXML safety, project storage and generation/recovery.
