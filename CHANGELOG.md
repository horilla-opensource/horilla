# Changelog

All notable changes to Horilla HR are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file starts at **2.1.1**, the first release maintained in this format. Releases
before it are documented on the
[releases page](https://github.com/horilla/horilla-hr/releases) and are not reproduced
here — they predate this convention and back-filling them would misrepresent how they
were recorded at the time.

Each released version corresponds to a git tag of the same name (bare semver, no `v`
prefix) and to the Docker tag `horilla/horilla-hr:<version>`. `horilla/__version__.py`
is the single source of truth; the release workflow refuses to publish an image whose
tag disagrees with it.

## [Unreleased]

<!--
Add entries here as you merge, under the headings below. Drop any heading you
do not use. At release time, rename this section to the new version with its
date and open a fresh Unreleased above it.

### Breaking      — requires action from an existing installation before or on upgrade
### Added         — new features
### Changed       — changes to existing behaviour
### Deprecated    — soon-to-be-removed features
### Removed        — features removed in this release
### Fixed         — bug fixes
### Security      — vulnerabilities fixed; link the advisory and credit the reporter
-->

## [2.1.3] — 2026-09-07

Bug-fix and security release. **Upgrade if you are on 2.1.0, 2.1.1 or 2.1.2** —
three pages return a server error on all three, and the leave-allocation
authorization flaw below affects every 2.x release.

### Security

| Advisory | Severity | Issue |
|---|---|---|
| [GHSA-gc35-jfv9-r3cm](https://github.com/horilla/horilla-hr/security/advisories/GHSA-gc35-jfv9-r3cm) | Medium | Any employee who was the reporting manager of one person could approve their own leave allocation and credit an arbitrary number of days to their own balance |

With thanks to **@je-lv** for reporting it responsibly.

Approval now requires a second person who actually manages the requester, and
the approver may never be the requester — the two checks are independent, since
an employee can be recorded as their own reporting manager. The fix is at the
shared authorization gate, so the reject, read, edit and delete endpoints on the
same model are covered too: rejecting an approved allocation subtracts the days
again, and the edit endpoint accepts `requested_days`. Neither was in the report.

### Fixed

- **Attendance work records, the skill zone view and the attendance monthly
  summary returned a 500.** A documentation comment in the modern filter panel
  described where the filter body is included, and wrote that description using
  real template syntax. Django's lexer does not recognise CSS comments, so the
  `{% include %}` inside the comment was executed on every render; on the pages
  that include the panel directly — rather than through the generic nav, where
  the list views supply `filter_body_template` — the variable resolved empty and
  the include raised `TemplateDoesNotExist: No template names provided`.

  Reported by **@owino600** in
  [#1216](https://github.com/horilla/horilla-hr/issues/1216), with an accurate
  diagnosis of the cause.

- Two `{% url %}` tags in a disabled block of jQuery in the grace-time template
  were being resolved on every render for the same reason. They resolved, so
  nothing broke, but removing the routes they name would have 500ed the page
  from inside a comment. The block was already marked unused and has been
  removed.

### Added

- A test that fails the build if `{% include %}`, `{% extends %}`, `{% url %}` or
  `{% ssi %}` appears inside a CSS or JavaScript comment in any template. The
  defect above shipped in three consecutive releases without being noticed, so
  the class is now checked rather than the instance.

### Upgrading

No migration or configuration change is required.

```bash
docker pull horilla/horilla-hr:2.1.3
```

## [2.1.2] — 2026-09-07

Security patch release. **Upgrading is recommended for all installations.**

### Security

Three access-control issues, all exploitable by an ordinary low-privilege
account and none dependent on `DEBUG` or any operator setting.

| Advisory | Severity | Issue |
|---|---|---|
| [GHSA-39gq-9wwx-p8hx](https://github.com/horilla/horilla-hr/security/advisories/GHSA-39gq-9wwx-p8hx) | High | Any employee who managed one person could overwrite — or delete — any other employee's bank account details, redirecting salary payments |
| [GHSA-x72c-5gf7-97g3](https://github.com/horilla/horilla-hr/security/advisories/GHSA-x72c-5gf7-97g3) | Medium | Any authenticated employee could delete any other employee's documents, including contracts and identity documents |
| [GHSA-v963-hrfx-34mw](https://github.com/horilla/horilla-hr/security/advisories/GHSA-v963-hrfx-34mw) | Medium | Any candidate could write notes onto any other candidate's hiring record, across companies, and read that candidate's tracking page |

With thanks to **@je-lv** for reporting all three responsibly.

Each fix was made at the shared authorization gate rather than the reported
endpoint, so sibling endpoints on the same gate are covered too. The bank-detail
`DELETE` and the document `GET`/`PUT` were not in the reports and were reachable
the same way.

### Changed

- Editing a document through `PUT /api/employee/documents/<pk>/` now authorizes
  against `horilla_documents.change_document` rather than
  `horilla_documents.view_document`. Owners and reporting managers are
  unaffected; an integration that held only the view permission and relied on it
  to write will now be refused.
- `DELETE /api/employee/employee-bank-details/<pk>/` now also admits the record's
  owner, and restricts managers to their own reports rather than any manager of
  anyone.

### Upgrading

No migration or configuration change is required.

If you drive Horilla through the REST API, check the two permission changes
above before upgrading — an integration that wrote documents using only
`horilla_documents.view_document` will start receiving 403.

```bash
docker pull horilla/horilla-hr:2.1.2
```

## [2.1.1] — 2026-09-06

Security patch release. **Upgrading is recommended for all installations.**

### Security

| Advisory | Severity | Issue |
|---|---|---|
| [GHSA-rf47-2qgf-qq4j](https://github.com/horilla/horilla-hr/security/advisories/GHSA-rf47-2qgf-qq4j) | High | Stored XSS leading to credential theft — XSS validation was bypassed on every REST and direct write |
| [GHSA-cjr4-rrp6-g72j](https://github.com/horilla/horilla-hr/security/advisories/GHSA-cjr4-rrp6-g72j) | High | Local file read through PDF generation, via an XSS-filter bypass |
| [GHSA-56x4-6268-vg4f](https://github.com/horilla/horilla-hr/security/advisories/GHSA-56x4-6268-vg4f) | High | Reimbursement approval could rewrite the claimed payout amount |
| [GHSA-p745-9729-g8jw](https://github.com/horilla/horilla-hr/security/advisories/GHSA-p745-9729-g8jw) | Medium | A candidate could read any other candidate's uploaded documents |
| [GHSA-mpw3-7c6v-vfjp](https://github.com/horilla/horilla-hr/security/advisories/GHSA-mpw3-7c6v-vfjp) | Medium | An employee could read any other employee's leave requests |

With thanks to **@je-lv** and **@Pig-Tail** for reporting these responsibly.

### Changed

- Rich text (ticket descriptions and comments, recruitment descriptions, policy bodies,
  OKR comments) is sanitised on output with an allow-list rather than a blocklist. Images
  and inline colour are preserved; scripts, event handlers and `javascript:`/`data:` URLs
  are removed.
- "Default Export Access" is now an explicit per-company setting rather than
  permissive-by-absence.
- API rate limiting added; outstanding tokens are revoked when a password changes.

### Upgrading

No migration or configuration change is required by this release.

If you are upgrading from **2.0.x** and use the WhatsApp integration, note that
[2.1.0](https://github.com/horilla/horilla-hr/releases/tag/2.1.0) requires a Meta App
Secret — message delivery stops until it is set.

```bash
docker pull horilla/horilla-hr:2.1.1
```

[Unreleased]: https://github.com/horilla/horilla-hr/compare/2.1.3...HEAD
[2.1.3]: https://github.com/horilla/horilla-hr/compare/2.1.2...2.1.3
[2.1.2]: https://github.com/horilla/horilla-hr/compare/2.1.1...2.1.2
[2.1.1]: https://github.com/horilla/horilla-hr/releases/tag/2.1.1
