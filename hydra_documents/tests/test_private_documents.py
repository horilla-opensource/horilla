import hashlib
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from hydra_documents.apps import private_storage_check
from hydra_documents.audit import AccessContext
from hydra_documents.models import (
    DocumentAccessLog,
    PrivateDocument,
    PrivateDocumentType,
    QuarantinedUpload,
)
from hydra_documents.scanning import ScanResult, ScannerUnavailable
from hydra_documents.services import purge_expired_quarantine, upload_private_document
from hydra_ops.readiness import domain_integrity_results
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


PDF_CONTENT = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


class PrivateDocumentTests(HydraRecruitmentTestCase):
    def setUp(self):
        super().setUp()
        self.private_root = tempfile.mkdtemp(prefix="hydra-private-test-")
        self.quarantine_root = tempfile.mkdtemp(prefix="hydra-quarantine-test-")
        self.settings_override = override_settings(
            HYDRA_PRIVATE_MEDIA_ROOT=self.private_root,
            HYDRA_DOCUMENT_QUARANTINE_ROOT=self.quarantine_root,
            HYDRA_PRIVATE_DOCUMENT_MAX_BYTES=1024 * 1024,
            HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS=30,
            HYDRA_DOCUMENT_QUARANTINE_HOURS=24,
        )
        self.settings_override.enable()
        self.document_type = PrivateDocumentType.objects.get(
            code="identity-document", company__isnull=True
        )
        PrivateDocumentType.objects.filter(pk=self.document_type.pk).update(
            max_size_bytes=1024 * 1024,
            retention_days=30,
        )
        self.document_type.refresh_from_db()
        self.scanner_patcher = patch(
            "hydra_documents.services.scan_file",
            return_value=ScanResult(clean=True, scanner="test-scanner", result="clean"),
        )
        self.scan_file = self.scanner_patcher.start()

    def tearDown(self):
        self.scanner_patcher.stop()
        self.settings_override.disable()
        shutil.rmtree(self.private_root, ignore_errors=True)
        shutil.rmtree(self.quarantine_root, ignore_errors=True)
        super().tearDown()

    def grant_document_read(self):
        self.grant_read()
        self.grant(
            ("hydra_documents", "view_privatedocument"),
            ("hydra_documents", "download_privatedocument"),
        )

    def grant_document_write(self):
        self.grant_document_read()
        self.grant(
            ("hydra_documents", "add_privatedocument"),
            ("hydra_documents", "view_privatedocumenttype"),
        )

    def grant_document_lifecycle(self):
        self.grant_document_write()
        self.grant(
            ("hydra_documents", "delete_privatedocument"),
            ("hydra_documents", "manage_privatedocumenthold"),
        )

    def grant_document_replace(self):
        self.grant_document_write()
        self.grant(("hydra_documents", "replace_privatedocument"))

    def upload(
        self,
        *,
        filename="passport.pdf",
        content=PDF_CONTENT,
        document_type=None,
        replaces=None,
        replacement_reason="",
        issued_on="",
        expires_on="",
    ):
        return self.client.post(
            reverse("hydra-candidate-documents", args=(self.candidate_a.pk,)),
            {
                "title": "Passport scan",
                "document_type": str((document_type or self.document_type).uuid),
                "issued_on": issued_on,
                "expires_on": expires_on,
                "replaces": str(replaces.uuid) if replaces else "",
                "replacement_reason": replacement_reason,
                "file": SimpleUploadedFile(
                    filename,
                    content,
                    content_type="application/octet-stream",
                ),
            },
        )

    def test_upload_inspects_content_and_stores_opaque_file_outside_media(self):
        self.grant_document_write()
        self.login()

        response = self.upload(filename="../../Passport Скан.pdf")

        self.assertEqual(response.status_code, 302)
        document = PrivateDocument.objects.get()
        self.assertEqual(document.person, self.person_a)
        self.assertEqual(document.candidate, self.candidate_a)
        self.assertEqual(document.original_filename, "Passport ____.pdf")
        self.assertEqual(document.verified_content_type, "application/pdf")
        self.assertEqual(document.size, len(PDF_CONTENT))
        self.assertEqual(document.sha256, hashlib.sha256(PDF_CONTENT).hexdigest())
        self.assertEqual(document.scanner, "test-scanner")
        self.assertIsNotNone(document.scanned_at)
        self.assertEqual(
            document.retention_until, timezone.localdate() + timedelta(days=30)
        )
        self.assertNotIn("passport", document.file.name.lower())
        self.assertTrue(Path(self.private_root, document.file.name).is_file())
        with self.assertRaises(ValueError):
            _ = document.file.url
        log = DocumentAccessLog.objects.get()
        self.assertEqual(log.action, DocumentAccessLog.Action.UPLOAD)
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.ALLOWED)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.reason, "scanned_clean")
        quarantine = QuarantinedUpload.objects.get()
        self.assertEqual(quarantine.status, QuarantinedUpload.Status.PROMOTED)
        self.assertEqual(quarantine.document, document)
        self.assertFalse(quarantine.file.name)
        self.assertIsNotNone(quarantine.purged_at)

    def test_detected_threat_remains_quarantined_and_is_never_downloadable(self):
        self.scan_file.return_value = ScanResult(
            clean=False, scanner="test-scanner", result="Test.Signature"
        )
        self.grant_document_write()
        self.login()

        response = self.upload()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rejected by the security scanner")
        self.assertFalse(PrivateDocument.objects.exists())
        quarantine = QuarantinedUpload.objects.get()
        self.assertEqual(quarantine.status, QuarantinedUpload.Status.INFECTED)
        self.assertTrue(Path(self.quarantine_root, quarantine.file.name).is_file())
        log = DocumentAccessLog.objects.get()
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.DENIED)
        self.assertEqual(log.reason, "threat_detected")
        QuarantinedUpload.objects.filter(pk=quarantine.pk).update(
            purge_after=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(purge_expired_quarantine(), 1)
        quarantine.refresh_from_db()
        self.assertFalse(quarantine.file.name)
        self.assertIsNotNone(quarantine.purged_at)

    def test_scanner_failure_fails_closed_and_records_quarantine_error(self):
        self.scan_file.side_effect = ScannerUnavailable("offline")
        self.grant_document_write()
        self.login()

        response = self.upload()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not be security-scanned")
        self.assertFalse(PrivateDocument.objects.exists())
        quarantine = QuarantinedUpload.objects.get()
        self.assertEqual(quarantine.status, QuarantinedUpload.Status.ERROR)
        self.assertTrue(Path(self.quarantine_root, quarantine.file.name).is_file())
        log = DocumentAccessLog.objects.get()
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.ERROR)
        self.assertEqual(log.reason, "scanner_unavailable")

    def test_extension_and_client_content_type_cannot_bypass_magic_check(self):
        self.grant_document_write()
        self.login()

        response = self.upload(filename="passport.pdf", content=b"<script>alert(1)</script>")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only verified PDF, JPEG and PNG")
        self.assertFalse(PrivateDocument.objects.exists())
        self.assertFalse(any(Path(self.private_root).rglob("*.*")))

    def test_authorized_download_is_attachment_with_no_store_headers_and_log(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()

        response = self.client.get(
            reverse("hydra-private-document-download", args=(document.uuid,)),
            HTTP_USER_AGENT="Hydra test browser",
            REMOTE_ADDR="192.0.2.10",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF_CONTENT)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("passport.pdf", response["Content-Disposition"].lower())
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(response["Pragma"], "no-cache")
        log = DocumentAccessLog.objects.filter(action="download").get()
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.ALLOWED)
        self.assertEqual(log.ip_address, "192.0.2.10")
        self.assertEqual(
            log.user_agent_sha256,
            hashlib.sha256(b"Hydra test browser").hexdigest(),
        )

    def test_missing_download_permission_returns_403_and_is_logged(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()
        self.user.user_permissions.remove(
            self.user.user_permissions.get(codename="download_privatedocument")
        )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

        response = self.client.get(
            reverse("hydra-private-document-download", args=(document.uuid,))
        )

        self.assertEqual(response.status_code, 403)
        log = DocumentAccessLog.objects.filter(action="download").get()
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.DENIED)
        self.assertEqual(log.reason, "permission_denied")

    def test_cross_scope_direct_uuid_returns_404_and_is_logged(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("hydra-candidate-documents", args=(self.candidate_b.pk,)),
            {
                "title": "Out of scope",
                "document_type": str(self.document_type.uuid),
                "file": SimpleUploadedFile("other.pdf", PDF_CONTENT),
            },
        )
        self.assertEqual(response.status_code, 302)
        document = PrivateDocument.objects.get(candidate=self.candidate_b)
        self.grant_document_read()
        self.login()

        response = self.client.get(
            reverse("hydra-private-document-download", args=(document.uuid,))
        )

        self.assertEqual(response.status_code, 404)
        log = DocumentAccessLog.objects.filter(
            action="download", actor=self.user
        ).get()
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.DENIED)
        self.assertEqual(log.reason, "outside_scope")

    def test_unknown_uuid_returns_404_and_is_logged(self):
        self.grant_document_read()
        self.login()
        unknown_uuid = uuid4()

        response = self.client.get(
            reverse("hydra-private-document-download", args=(unknown_uuid,))
        )

        self.assertEqual(response.status_code, 404)
        log = DocumentAccessLog.objects.get()
        self.assertEqual(log.document_uuid, unknown_uuid)
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.NOT_FOUND)

    def test_candidate_document_page_enforces_scope_and_has_no_public_file_url(self):
        self.grant_document_write()
        self.login()
        self.upload()

        response = self.client.get(
            reverse("hydra-candidate-documents", args=(self.candidate_a.pk,))
        )
        outside = self.client.get(
            reverse("hydra-candidate-documents", args=(self.candidate_b.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passport scan")
        self.assertNotContains(response, "/media/")
        self.assertNotContains(response, "candidate-documents/")
        self.assertEqual(outside.status_code, 404)

    def test_unscanned_legacy_document_is_download_blocked_and_logged(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()
        PrivateDocument.objects.filter(pk=document.pk).update(scanned_at=None, scanner="")

        response = self.client.get(
            reverse("hydra-private-document-download", args=(document.uuid,))
        )

        self.assertEqual(response.status_code, 404)
        log = DocumentAccessLog.objects.filter(action="download").get()
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.DENIED)
        self.assertEqual(log.reason, "not_scanned")

    def test_retention_and_legal_hold_both_block_deletion_then_tombstone_is_kept(self):
        self.grant_document_lifecycle()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()
        stored_path = Path(self.private_root, document.file.name)

        response = self.client.post(
            reverse("hydra-private-document-delete", args=(document.uuid,)),
            {"reason": "Duplicate upload"},
            follow=True,
        )
        self.assertContains(response, "must be retained until")
        document.refresh_from_db()
        self.assertIsNone(document.deleted_at)
        self.assertTrue(stored_path.is_file())

        PrivateDocument.objects.filter(pk=document.pk).update(
            retention_until=timezone.localdate() - timedelta(days=1)
        )
        self.client.post(
            reverse("hydra-private-document-legal-hold", args=(document.uuid,)),
            {"action": "apply", "reason": "Active legal case"},
        )
        document.refresh_from_db()
        self.assertTrue(document.legal_hold)
        self.assertEqual(document.legal_hold_reason, "Active legal case")

        response = self.client.post(
            reverse("hydra-private-document-delete", args=(document.uuid,)),
            {"reason": "Expired record"},
            follow=True,
        )
        self.assertContains(response, "protected by a legal hold")
        document.refresh_from_db()
        self.assertIsNone(document.deleted_at)

        self.client.post(
            reverse("hydra-private-document-legal-hold", args=(document.uuid,)),
            {"action": "release", "reason": "Case closed"},
        )
        response = self.client.post(
            reverse("hydra-private-document-delete", args=(document.uuid,)),
            {"reason": "Retention expired"},
            follow=True,
        )
        self.assertContains(response, "Document securely deleted")
        document.refresh_from_db()
        self.assertIsNotNone(document.deleted_at)
        self.assertEqual(document.deletion_reason, "Retention expired")
        self.assertFalse(document.file.name)
        self.assertIsNotNone(document.file_purged_at)
        self.assertFalse(stored_path.exists())
        self.assertEqual(
            list(
                DocumentAccessLog.objects.filter(
                    action=DocumentAccessLog.Action.LEGAL_HOLD
                ).values_list("reason", "detail")
            ),
            [("hold_released", "Case closed"), ("hold_applied", "Active legal case")],
        )
        delete_log = DocumentAccessLog.objects.get(
            action=DocumentAccessLog.Action.DELETE
        )
        self.assertEqual(delete_log.outcome, DocumentAccessLog.Outcome.ALLOWED)
        self.assertEqual(delete_log.detail, "Retention expired")

        response = self.client.get(
            reverse("hydra-private-document-download", args=(document.uuid,))
        )
        self.assertEqual(response.status_code, 404)

    def test_lifecycle_actions_require_explicit_permissions(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()

        hold = self.client.post(
            reverse("hydra-private-document-legal-hold", args=(document.uuid,)),
            {"action": "apply", "reason": "Legal case"},
        )
        delete = self.client.post(
            reverse("hydra-private-document-delete", args=(document.uuid,)),
            {"reason": "Delete"},
        )

        self.assertEqual(hold.status_code, 403)
        self.assertEqual(delete.status_code, 403)
        document.refresh_from_db()
        self.assertFalse(document.legal_hold)
        self.assertIsNone(document.deleted_at)

    def test_lifecycle_uuid_is_hidden_outside_current_scope(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("hydra-candidate-documents", args=(self.candidate_b.pk,)),
            {
                "title": "Out of scope lifecycle",
                "document_type": str(self.document_type.uuid),
                "file": SimpleUploadedFile("other.pdf", PDF_CONTENT),
            },
        )
        self.assertEqual(response.status_code, 302)
        document = PrivateDocument.objects.get(candidate=self.candidate_b)
        PrivateDocument.objects.filter(pk=document.pk).update(
            retention_until=timezone.localdate() - timedelta(days=1)
        )
        self.grant_document_lifecycle()
        self.login()

        hold = self.client.post(
            reverse("hydra-private-document-legal-hold", args=(document.uuid,)),
            {"action": "apply", "reason": "Probe"},
        )
        delete = self.client.post(
            reverse("hydra-private-document-delete", args=(document.uuid,)),
            {"reason": "Probe"},
        )

        self.assertEqual(hold.status_code, 404)
        self.assertEqual(delete.status_code, 404)
        document.refresh_from_db()
        self.assertFalse(document.legal_hold)
        self.assertIsNone(document.deleted_at)

    def test_legacy_rescan_command_unlocks_only_a_clean_result(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()
        PrivateDocument.objects.filter(pk=document.pk).update(scanned_at=None, scanner="")

        with patch(
            "hydra_documents.management.commands.rescan_private_documents.scan_file",
            return_value=ScanResult(
                clean=True, scanner="migration-scanner", result="clean"
            ),
        ):
            call_command("rescan_private_documents", stdout=StringIO())

        document.refresh_from_db()
        self.assertEqual(document.scanner, "migration-scanner")
        self.assertIsNotNone(document.scanned_at)
        scan_log = DocumentAccessLog.objects.get(action=DocumentAccessLog.Action.SCAN)
        self.assertEqual(scan_log.outcome, DocumentAccessLog.Outcome.ALLOWED)
        self.assertEqual(scan_log.reason, "legacy_scan_clean")

    def test_legacy_rescan_command_fails_when_scanner_is_unavailable(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()
        PrivateDocument.objects.filter(pk=document.pk).update(scanned_at=None, scanner="")

        with patch(
            "hydra_documents.management.commands.rescan_private_documents.scan_file",
            side_effect=ScannerUnavailable("offline"),
        ):
            with self.assertRaises(CommandError):
                call_command("rescan_private_documents", stdout=StringIO())

        document.refresh_from_db()
        self.assertIsNone(document.scanned_at)
        scan_log = DocumentAccessLog.objects.get(action=DocumentAccessLog.Action.SCAN)
        self.assertEqual(scan_log.outcome, DocumentAccessLog.Outcome.ERROR)

    def test_access_log_is_append_only_through_model_and_queryset(self):
        self.grant_document_write()
        self.login()
        self.upload()
        log = DocumentAccessLog.objects.get()

        log.reason = "changed"
        with self.assertRaises(TypeError):
            log.save()
        with self.assertRaises(TypeError):
            log.delete()
        with self.assertRaises(TypeError):
            DocumentAccessLog.objects.filter(pk=log.pk).update(reason="changed")
        with self.assertRaises(TypeError):
            DocumentAccessLog.objects.filter(pk=log.pk).delete()
        log.refresh_from_db()
        self.assertEqual(log.reason, "scanned_clean")

    def test_storage_check_rejects_overlapping_public_and_private_roots(self):
        with override_settings(HYDRA_PRIVATE_MEDIA_ROOT=Path(self.private_root, "media")):
            with override_settings(MEDIA_ROOT=self.private_root):
                errors = private_storage_check(None)
        self.assertEqual([error.id for error in errors], ["hydra_documents.E001"])

    def test_existing_hydra_candidate_view_remains_operational(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("candidate-view"))
        self.assertEqual(response.status_code, 200)

    def test_single_current_type_requires_explicit_replacement(self):
        self.grant_document_write()
        self.login()
        self.upload()

        response = self.upload(filename="second.pdf")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has a current version")
        self.assertEqual(PrivateDocument.objects.count(), 1)
        self.assertEqual(QuarantinedUpload.objects.count(), 1)

    def test_replacement_creates_immutable_version_chain_and_preserves_old_file(self):
        self.grant_document_replace()
        self.login()
        self.upload()
        first = PrivateDocument.objects.get()
        first_path = Path(self.private_root, first.file.name)
        original_snapshot = dict(first.type_rules_snapshot)

        response = self.upload(
            filename="passport-renewed.pdf",
            replaces=first,
            replacement_reason="Renewed passport received",
        )

        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        second = PrivateDocument.objects.exclude(pk=first.pk).get()
        self.assertEqual(second.replaces, first)
        self.assertEqual(second.lineage_uuid, first.lineage_uuid)
        self.assertEqual(second.version_number, 2)
        self.assertFalse(first.is_current_version)
        self.assertTrue(second.is_current_version)
        self.assertTrue(first_path.is_file())
        self.assertEqual(
            DocumentAccessLog.objects.filter(document=second).get().reason,
            "replacement_scanned_clean",
        )

        PrivateDocumentType.objects.filter(pk=self.document_type.pk).update(
            name="Changed future policy",
            retention_days=45,
        )
        first.refresh_from_db()
        self.assertEqual(first.type_rules_snapshot, original_snapshot)
        old_download = self.client.get(
            reverse("hydra-private-document-download", args=(first.uuid,))
        )
        self.assertEqual(old_download.status_code, 200)
        self.assertEqual(b"".join(old_download.streaming_content), PDF_CONTENT)

    def test_replacement_requires_dedicated_permission_at_service_boundary(self):
        self.grant_document_write()
        self.login()
        self.upload()
        first = PrivateDocument.objects.get()

        with self.assertRaises(PermissionDenied):
            upload_private_document(
                actor=self.user,
                candidate_id=self.candidate_a.pk,
                document_type_uuid=self.document_type.uuid,
                title="Unauthorized replacement",
                issued_on=None,
                expires_on=None,
                replaces_uuid=first.uuid,
                replacement_reason="Attempt without permission",
                upload=SimpleUploadedFile("replacement.pdf", PDF_CONTENT),
                audit_context=AccessContext(None, ""),
            )
        self.assertEqual(PrivateDocument.objects.count(), 1)

    def test_cross_scope_or_cross_application_predecessor_is_hidden(self):
        other = upload_private_document(
            actor=self.admin,
            candidate_id=self.candidate_b.pk,
            document_type_uuid=self.document_type.uuid,
            title="Other application document",
            issued_on=None,
            expires_on=None,
            replaces_uuid=None,
            replacement_reason="",
            upload=SimpleUploadedFile("other.pdf", PDF_CONTENT),
            audit_context=AccessContext(None, ""),
        )
        self.grant_document_replace()

        with self.assertRaises(Http404):
            upload_private_document(
                actor=self.user,
                candidate_id=self.candidate_a.pk,
                document_type_uuid=self.document_type.uuid,
                title="Cross application probe",
                issued_on=None,
                expires_on=None,
                replaces_uuid=other.uuid,
                replacement_reason="Cross application attempt",
                upload=SimpleUploadedFile("probe.pdf", PDF_CONTENT),
                audit_context=AccessContext(None, ""),
            )

    def test_expiry_and_size_rules_fail_before_private_promotion(self):
        passport_type = PrivateDocumentType.objects.get(
            code="passport", company__isnull=True
        )
        PrivateDocumentType.objects.filter(pk=passport_type.pk).update(
            max_size_bytes=32
        )
        passport_type.refresh_from_db()
        self.grant_document_write()
        self.login()

        missing_expiry = self.upload(document_type=passport_type)
        self.assertContains(missing_expiry, "Expiry date is required")
        self.assertFalse(PrivateDocument.objects.exists())
        self.assertFalse(QuarantinedUpload.objects.exists())

        too_large = self.upload(
            document_type=passport_type,
            expires_on=(timezone.localdate() + timedelta(days=365)).isoformat(),
        )
        self.assertEqual(too_large.status_code, 200)
        self.assertFalse(PrivateDocument.objects.exists())
        self.assertFalse(QuarantinedUpload.objects.exists())

    def test_version_identity_and_rows_reject_direct_mutation_or_delete(self):
        self.grant_document_write()
        self.login()
        self.upload()
        document = PrivateDocument.objects.get()

        document.version_number = 9
        with self.assertRaises(TypeError):
            document.save()
        with self.assertRaises(TypeError):
            PrivateDocument.objects.filter(pk=document.pk).update(version_number=9)
        with self.assertRaises(TypeError):
            document.delete()
        with self.assertRaises(TypeError):
            PrivateDocument.objects.filter(pk=document.pk).delete()

    def test_readiness_detects_document_version_and_snapshot_corruption(self):
        self.grant_document_replace()
        self.login()
        PrivateDocumentType.objects.filter(pk=self.document_type.pk).update(
            single_current=False
        )

        self.assertEqual(self.upload(filename="first.pdf").status_code, 302)
        first = PrivateDocument.objects.get(original_filename="first.pdf")
        self.assertEqual(self.upload(filename="parallel.pdf").status_code, 302)
        parallel = PrivateDocument.objects.get(original_filename="parallel.pdf")
        self.assertEqual(
            self.upload(
                filename="replacement.pdf",
                replaces=first,
                replacement_reason="Replacement used for readiness validation",
            ).status_code,
            302,
        )
        replacement = PrivateDocument.objects.get(
            original_filename="replacement.pdf"
        )

        PrivateDocumentType.objects.filter(pk=self.document_type.pk).update(
            single_current=True
        )
        PrivateDocument._base_manager.filter(pk=replacement.pk).update(
            lineage_uuid=uuid4()
        )
        PrivateDocument._base_manager.filter(pk=parallel.pk).update(
            type_rules_snapshot={}
        )

        results = {result.name: result for result in domain_integrity_results()}
        self.assertFalse(results["private_document_current_versions"].ok)
        self.assertFalse(results["private_document_version_chains"].ok)
        self.assertFalse(results["private_document_rule_snapshots"].ok)

    def test_company_document_type_configuration_is_scoped(self):
        self.grant(
            ("hydra_documents", "view_privatedocumenttype"),
            ("hydra_documents", "add_privatedocumenttype"),
            ("hydra_documents", "change_privatedocumenttype"),
        )
        outside_type = PrivateDocumentType.objects.create(
            company=self.company_b,
            code="outside-policy",
            name="Outside policy",
            category=PrivateDocument.Category.OTHER,
            allowed_content_types=["application/pdf"],
            max_size_bytes=1024 * 1024,
            retention_days=30,
        )
        self.login()

        listing = self.client.get(reverse("hydra-private-document-type-list"))
        outside_edit = self.client.get(
            reverse("hydra-private-document-type-update", args=(outside_type.uuid,))
        )
        created = self.client.post(
            reverse("hydra-private-document-type-create"),
            {
                "company": self.company_a.pk,
                "code": "company-passport-copy",
                "name": "Company passport copy",
                "category": PrivateDocument.Category.IDENTITY,
                "allowed_content_types": ["application/pdf"],
                "max_size_mb": 1,
                "retention_days": 90,
                "requires_expiry_date": "on",
                "single_current": "on",
                "is_active": "on",
            },
        )

        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, "Outside policy")
        self.assertEqual(outside_edit.status_code, 404)
        self.assertEqual(created.status_code, 302)
        configured = PrivateDocumentType.objects.get(
            company=self.company_a, code="company-passport-copy"
        )
        self.assertEqual(configured.retention_days, 90)
        self.assertEqual(configured.allowed_content_types, ["application/pdf"])
        self.assertEqual(configured.created_by, self.user)
