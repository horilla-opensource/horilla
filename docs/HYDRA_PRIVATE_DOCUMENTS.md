# Hydra private candidate documents — TASK-2 security boundary

## Status and reuse decision

Implemented on 2026-07-14 and hardened on 2026-07-15.

- **REUSE** Horilla `Candidate` and canonical `hydra_people.Person` ownership.
- **REPLACE** generic `/media/` delivery for Hydra-sensitive content.
- **EXTEND** the original private-document slice with isolated quarantine, fail-closed malware scanning, logical types, immutable replacement versions, retention, legal hold, secure deletion, and operational readiness checks.
- Keep Horilla's original document screens operational, but never route Hydra-private files through them.

The generic upstream media endpoint authenticates a request without applying Hydra's Candidate/Person object scope. `hydra_documents` is therefore the mandatory security boundary for passport, recruitment, and legalization attachments.

## Authorized workflow

At `/hydra/documents/candidates/<candidate-id>/`, a scoped internal operator can upload and list private files. Every upload follows this sequence:

1. re-evaluate document, Candidate, Person, and organization permissions;
2. enforce the configured size limit, inspect PDF/JPEG/PNG magic bytes, sanitize the display filename, and calculate SHA-256;
3. write an opaque `.upload` object to the dedicated quarantine root;
4. stream that object to `clamd` with the framed `INSTREAM` protocol;
5. promote only a `clean` result into private storage and create `PrivateDocument` metadata;
6. keep detected or failed scans inaccessible in quarantine and write an append-only audit event.

Scanner timeout, connection failure, malformed response, disabled scanner, or database promotion failure never produces a downloadable document. The user receives a generic error; the internal quarantine record keeps the operational result. The ClamAV TCP port is internal to the Compose network and is not published to the host.

The protocol implementation follows the official [ClamD protocol documentation](https://docs.clamav.net/manual/Usage/ClamdProtocol.html). Staging uses the official persistent-database Docker layout described by [ClamAV's Docker guide](https://docs.clamav.net/manual/Installing/Docker.html).

## Logical types and version chains

TASK-011 adds `PrivateDocumentType` as a fixed-field policy dictionary, not a
generic rule engine. Five active global types are seeded: Passport, Identity,
Recruitment, Legalization and Other. Authorized operators may create and update
company-specific types only inside their effective Company scope; global types
are editable only by a superuser. Direct cross-scope type URLs return 404.

Each type fixes the category, allowed verified MIME types, maximum size,
retention days, whether an expiry date is required, and whether only one current
document may exist. The global size ceiling still applies. Every successful
upload stores the exact rule snapshot, so changing a type affects future
versions without rewriting historical decisions.

Replacement is a dedicated `replace_privatedocument` action. The operator must
select the current predecessor and provide a reason of at least ten characters.
The promotion transaction locks Candidate, Person, type, predecessor and all
current rows. It then creates, but never overwrites, a new version with the same
lineage UUID and the next number. `OneToOneField(PROTECT)` permits at most one
successor per version, and `(lineage_uuid, version_number)` is unique. For a
single-current type, an existing current row makes an ordinary second upload
invalid.

Old versions remain within the same scoped download, retention and legal-hold
boundary. Version identity, predecessor, type/rule snapshot, dates, file
metadata and checksum reject model/queryset mutation; hard deletion is blocked
in favor of the existing retention-controlled tombstone. A canonical Person
merge may reassign the Person FK only through its separately locked/audited
service and does not alter version identity.

The configuration UI is at `/hydra/documents/types/`. The Candidate document
screen shows current/superseded state, version number, replacement reason,
issue/expiry dates and all historical versions without exposing storage keys.

## Storage boundaries

Three roots must be pairwise disjoint:

- `MEDIA_ROOT` — upstream public/application media;
- `HYDRA_PRIVATE_MEDIA_ROOT` — approved Hydra documents;
- `HYDRA_DOCUMENT_QUARANTINE_ROOT` — untrusted or rejected uploads.

System checks `hydra_documents.E001` and `hydra_documents.E002` reject overlap. Both private storage classes deliberately have no URL method. Object keys contain generated UUIDs and verified extensions, never a person name, passport number, title, or original filename.

Successful promotion deletes the quarantine blob while retaining its metadata record. Detected and failed files remain isolated until `purge_document_storage` removes the blob after `HYDRA_DOCUMENT_QUARANTINE_HOURS`; the row and scan result remain as evidence. Quarantine is intentionally excluded from backups so known-untrusted content is not copied into recovery sets.

## Download and audit boundary

Download requires authentication plus `view_privatedocument`, `download_privatedocument`, Candidate/Person permissions, and current organization scope on every request. Unknown and out-of-scope UUIDs return 404. Files with no completed clean scan and logically deleted files also return 404 and are audited.

Authorized content is streamed as an attachment with verified MIME type, `nosniff`, `private, no-store`, `Pragma: no-cache`, and a restrictive CSP. Templates never expose a storage key or `/media/` URL.

`DocumentAccessLog` now covers upload, download, scan, legal-hold, and deletion events. It stores actor, document UUID, outcome/reason, time, socket IP, a SHA-256 user-agent hash, and a bounded lifecycle detail. Model and queryset APIs are append-only; admin is read-only; protected foreign keys prevent related-object deletion from rewriting history. The deployment database role should additionally be denied direct `UPDATE` and `DELETE` on the table.

## Retention, legal hold, and deletion

New documents receive `retention_until` from `HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS`. Deletion requires `delete_privatedocument`, current Candidate scope, a reason, an expired retention period, and no legal hold.

Legal hold requires `manage_privatedocumenthold` and a reason. Applying and releasing a hold are separate append-only audit events. A hold prevents deletion regardless of the retention date.

Deletion is a tombstone rather than a row delete:

- access is revoked by `deleted_at` immediately;
- the physical private object is deleted;
- the file field is cleared and `file_purged_at` is recorded;
- title, ownership, hash, deletion actor/reason, and access history remain.

If physical cleanup fails after logical deletion, download remains blocked and an error is audited. `purge_document_storage` retries those objects safely.

## Legacy upgrade path

Migration `hydra_documents.0002_alter_privatedocument_options_and_more` adds lifecycle fields, quarantine metadata, new permissions, and audit actions. Existing rows intentionally receive no fake scanner timestamp and are download-blocked until scanned.

Migration `hydra_documents.0003_document_types_and_versions` adds type policy,
lineage, predecessor, version, rule snapshot and validity fields. It seeds the
five global types and backfills every existing document with an appropriate
logical type, lineage equal to its preserved UUID, version 1 and a deterministic
rule snapshot before making `document_type` non-null. Existing quarantine
evidence remains valid and may have no intended type because that fact did not
exist at upload time.

After deploying ClamAV and before reopening document access, run:

```text
python manage.py rescan_private_documents
python manage.py purge_document_storage
```

The rescan command marks clean files with scanner metadata. A detected legacy threat is tombstoned and its object is removed; a scanner/storage failure remains blocked and makes the command exit unsuccessfully. `--limit N` supports bounded operational batches.

The dedicated worker in `HYDRA_MAINTENANCE.md` runs bounded purge cycles. `purge_document_storage` remains available for an operator-triggered repair. Hydra deliberately does not restart legacy APScheduler jobs in web workers.

## Configuration and readiness

Development defaults to `HYDRA_DOCUMENT_SCANNER=disabled`, so uploads fail closed unless a scanner is explicitly configured. Staging/production readiness requires `clamd`, positive retention periods, three writable separated roots, and a live framed `PING`/`PONG` health check. Domain readiness also fails when a single-current application/type group has multiple current rows, a replacement changes its Candidate, Person, logical type, lineage or sequence, or a stored version lacks the complete immutable type-rule snapshot. The corresponding result names are `private_document_current_versions`, `private_document_version_chains`, and `private_document_rule_snapshots`.

```text
HYDRA_PRIVATE_MEDIA_ROOT=.private_media
HYDRA_PRIVATE_DOCUMENT_MAX_BYTES=10485760
HYDRA_DOCUMENT_QUARANTINE_ROOT=.document_quarantine
HYDRA_DOCUMENT_QUARANTINE_HOURS=72
HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS=365
HYDRA_DOCUMENT_SCANNER=clamd
HYDRA_CLAMD_HOST=clamav
HYDRA_CLAMD_PORT=3310
HYDRA_CLAMD_TIMEOUT_SECONDS=30
```

`docker-compose.staging.yaml` adds a private `clamav` service and persistent signature database volume. The default image is configurable through `HYDRA_CLAMAV_IMAGE`; review and pin the approved feature/patch image during release management. ClamAV's documented memory requirements must be included in target-host capacity planning.

## Automated and manual verification

Focused tests cover clean promotion, opaque separated storage, protocol framing, threat quarantine, scanner failure, legacy download denial, safe headers, object scope, append-only audit, retention, legal hold, tombstone deletion, quarantine purge, type rules, explicit single-current replacement, immutable version chains, dedicated permissions, cross-scope predecessor denial, Company-scoped configuration and staging configuration.

The TASK-011 PostgreSQL run passed 26/26 focused private-document tests and 390/390 full Django tests. Migration-manifest verification covers 64 reviewed sources. Browser QA on the real local stack verified type list/form and a two-version Candidate history at 1280 x 720 and 390 x 844 with no horizontal overflow, duplicate HTML ids, broken labels, storage-path disclosure or warning/error console log. `manage.py check`, migration-drift detection, `migrate --check`, dependency consistency, workflow YAML parsing, and `git diff --check` also passed.

Manual staging acceptance:

1. Confirm `hydra_readiness --json` reports scanner health, all three storage roots, and all three `private_document_*` integrity results as healthy.
2. Upload an approved inert PDF and verify a clean scan, private object, and `upload/allowed` event.
3. Use the standard EICAR test artifact only in an approved isolated staging exercise; confirm no `PrivateDocument` is created, no download route is available, and the quarantine event is denied.
4. Stop ClamAV and confirm uploads fail closed; restart it and confirm readiness recovers.
5. Test direct UUID access from another team and without download permission.
6. Confirm deletion is blocked before retention and during legal hold, then succeeds after both gates permit it while retaining the tombstone/audit history.
7. Run both management commands and verify expected exit status and purge counts.
8. Repeat the list/upload/lifecycle screen at a viewport no wider than 390 px.
9. Create a company type, upload version 1, replace it with a reason, and confirm
   that version 1 remains downloadable/auditable while version 2 alone is marked
   current. Change the type and confirm both version snapshots remain unchanged.

## Remaining deployment gates

- The target host must provide encrypted volumes or encrypted object storage, encrypted off-host backups, restricted service identities, monitoring, and an approved retention schedule. Application code cannot attest host-level encryption.
- The target environment must size ClamAV, verify signature updates, alert on stale/unhealthy definitions, and record an approved false-positive response procedure.
- Candidate self-service remains intentionally absent; this boundary is for authenticated internal operators.
- Database-level append-only grants and target-host maintenance health/alert evidence remain production controls.
