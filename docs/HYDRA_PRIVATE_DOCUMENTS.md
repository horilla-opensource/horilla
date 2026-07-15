# Hydra private candidate documents — TASK-2

## Status and audit decision

Implemented on 2026-07-14 as the smallest complete candidate-document vertical slice.

The mandatory Horilla audit was repeated before implementation:

- **REUSE** Horilla `Candidate` as the application and `hydra_people.Person` as the canonical owner identity;
- **REPLACE** generic media storage/delivery for Hydra-sensitive files;
- **NEW MODULE** `hydra_documents` for the focused shared private-document boundary;
- leave Horilla `CandidateDocument`, `horilla_documents.Document` and `/media/` operational for existing upstream screens, but never route Hydra-private files through them.

The replacement is necessary because the generic `/media/<path>` endpoint authenticates a session/JWT but does not authorize the related Candidate/Person object or record reads. Horilla's candidate preview also reads a requested document without reliably proving it belongs to the candidate session and embeds content in a data URL.

## Complete vertical slice

At `/hydra/documents/candidates/<candidate-id>/`, an authorized internal operator can:

1. open a linked Candidate that is currently visible through Hydra organization scope;
2. upload a PDF, JPEG or PNG;
3. see only documents for that scoped application;
4. download through an authenticated, permission- and object-scoped endpoint;
5. produce an append-only access event for upload and every authenticated download attempt.

The recruitment detail page links to this screen when the actor has `hydra_documents.view_privatedocument`. Existing Horilla Candidate pages continue to work unchanged.

## Storage and validation boundary

`HYDRA_PRIVATE_MEDIA_ROOT` defaults to `.private_media` and is separate from `MEDIA_ROOT`. Django system check `hydra_documents.E001` rejects equal or nested public/private roots. `.private_media/` is ignored by Git.

`PrivateDocumentStorage` exposes no public URL. Stored keys contain a generated UUID and verified extension, not a Candidate name, passport number, title or original filename. Templates contain only the authorized download route.

Upload validation:

- caps size with `HYDRA_PRIVATE_DOCUMENT_MAX_BYTES` (10 MiB by default);
- recognizes PDF, JPEG and PNG by server-inspected magic bytes instead of trusting the browser MIME type or extension;
- calculates SHA-256 while reading the upload;
- stores a sanitized display filename separately;
- removes a newly written object if the database transaction fails.

This signature validation is an MVP containment control, not malware scanning. Scanner/quarantine integration is required before accepting untrusted external uploads in a pilot.

## Authorization policy

The list/upload endpoint requires authentication and `view_privatedocument`; upload additionally requires `add_privatedocument`. The service independently repeats upload permissions and obtains the Candidate through `linked_candidate_for_user()`, whose result intersects:

1. `recruitment.view_candidate`;
2. `hydra_people.view_person`;
3. current Person assignment and Hydra scope grants;
4. Candidate recruitment company scope.

The download endpoint re-evaluates `view_privatedocument`, `download_privatedocument`, Candidate permission and current organization scope on every request. A missing action permission returns HTTP 403. An unknown or out-of-scope UUID returns HTTP 404 so the endpoint does not confirm object visibility.

The selected-company session value is not an authorization input. Superuser access remains Django's explicit administrative bypass.

## Download and audit behavior

Authorized content is streamed as an attachment. No inline/base64 preview or storage redirect is emitted. The response includes:

- verified `Content-Type`;
- `Content-Disposition: attachment` with the sanitized original filename;
- `X-Content-Type-Options: nosniff`;
- `Cache-Control: private, no-store, max-age=0` and `Pragma: no-cache`;
- restrictive `Content-Security-Policy`.

`DocumentAccessLog` records document UUID, nullable document relation for unknown UUIDs, actor, action, outcome, reason, time, socket IP and a SHA-256 hash of the user agent. It never stores the raw user-agent string. Uploads record `allowed`; downloads record `allowed`, `denied`, `not_found` or `error`.

Logs are append-only through model/queryset APIs, read-only in Django admin, and use protected actor/document foreign keys so related-object deletion cannot mutate prior events. Production database credentials should additionally be denied direct `UPDATE`/`DELETE` on this table.

## Migration and configuration

`hydra_documents/migrations/0001_initial.py` creates `PrivateDocument`, `DocumentAccessLog`, custom permissions and query indexes. No upstream Horilla model or migration is changed.

Environment variables:

```text
HYDRA_PRIVATE_MEDIA_ROOT=.private_media
HYDRA_PRIVATE_DOCUMENT_MAX_BYTES=10485760
```

In staging, the private root must be a non-public encrypted volume/bucket accessible only to the application identity. Backups must capture the database and private object set as one recovery point. Restore verification must confirm every metadata row has an object and matching SHA-256 before the service is reopened.

## Automated verification

Focused tests prove:

- opaque storage outside public media and absence of a storage URL;
- server-side signature, size and hash metadata;
- rejection and cleanup of disguised active content;
- authorized streaming with safe headers and audit event;
- HTTP 403 plus denied event without download permission;
- HTTP 404 plus denied event for a cross-team direct UUID;
- HTTP 404 plus not-found event for an unknown UUID;
- scoped UI with no storage/media path;
- model/queryset/admin append-only behavior;
- rejection of overlapping media roots;
- continued operation of the original Horilla Candidate view.

The final PostgreSQL 17 acceptance run applied `hydra_documents.0001_initial` and passed 50/50 combined Hydra tests. `manage.py check`, `makemigrations --check --dry-run`, `migrate --check`, Python compilation, `pip check` and `git diff --check` also passed.

Browser QA used the real local Django/PostgreSQL stack and the existing scoped `hydra-qa` role. At 1280 px the upload form and stored-document table rendered with one active Recruitment navigation item, no public-media links and no horizontal overflow. A QA PDF created through the same production upload service appeared without its storage key, the authorized link emitted a real browser download event, and the database recorded both `upload/allowed` and `download/allowed` events. The browser controller cannot drive the native operating-system file chooser, so the UI chooser itself was inspected but the actual file selection is covered by the HTTP integration test.

At 390 × 844 px the page measured 376 px, the document card 350.4 px, the form collapsed to one 316.8 px column, the download remained available and there was no horizontal overflow. The responsive screenshot surface added external white canvas around the emulated viewport; DOM geometry was used to distinguish that tool artifact from application layout.

## Manual verification

1. Grant an operator Person/Candidate read permissions plus `view_privatedocument`, `add_privatedocument` and `download_privatedocument`, and a current Hydra team/company scope.
2. Open a linked application and select **Private documents**.
3. Upload a small real PDF and confirm only its display metadata appears; no `/media/` or private object key should be present in page HTML.
4. Download it and confirm the browser treats it as a file attachment.
5. Remove download permission and retry the UUID: expect HTTP 403 and a denied event.
6. With permission restored, try a document belonging to another team: expect HTTP 404 and a denied event.
7. Repeat the list/upload flow at a viewport no wider than 390 px.

## Known limitations and next task

- Malware scanning/quarantine and encrypted object-store deployment are not part of this local MVP slice.
- Retention periods and legal-hold deletion are not yet modeled. There is intentionally no document deletion endpoint; define the policy before pilot data.
- Candidate self-service is not exposed. This slice is for authenticated internal operators.
- Access-log append-only behavior is enforced in application APIs and relations; staging must also restrict the database role.
- `022-legalization-mvp.md` is implemented and references `PrivateDocument` rather than creating another file-delivery mechanism. The next numbered task is `023-excel-import.md`.
