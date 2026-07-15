import hashlib
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from hydra_documents.apps import private_storage_check
from hydra_documents.models import DocumentAccessLog, PrivateDocument
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


PDF_CONTENT = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


class PrivateDocumentTests(HydraRecruitmentTestCase):
    def setUp(self):
        super().setUp()
        self.private_root = tempfile.mkdtemp(prefix="hydra-private-test-")
        self.settings_override = override_settings(
            HYDRA_PRIVATE_MEDIA_ROOT=self.private_root,
            HYDRA_PRIVATE_DOCUMENT_MAX_BYTES=1024 * 1024,
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.private_root, ignore_errors=True)
        super().tearDown()

    def grant_document_read(self):
        self.grant_read()
        self.grant(
            ("hydra_documents", "view_privatedocument"),
            ("hydra_documents", "download_privatedocument"),
        )

    def grant_document_write(self):
        self.grant_document_read()
        self.grant(("hydra_documents", "add_privatedocument"))

    def upload(self, *, filename="passport.pdf", content=PDF_CONTENT):
        return self.client.post(
            reverse("hydra-candidate-documents", args=(self.candidate_a.pk,)),
            {
                "title": "Passport scan",
                "category": PrivateDocument.Category.IDENTITY,
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
        self.assertNotIn("passport", document.file.name.lower())
        self.assertTrue(Path(self.private_root, document.file.name).is_file())
        with self.assertRaises(ValueError):
            _ = document.file.url
        log = DocumentAccessLog.objects.get()
        self.assertEqual(log.action, DocumentAccessLog.Action.UPLOAD)
        self.assertEqual(log.outcome, DocumentAccessLog.Outcome.ALLOWED)
        self.assertEqual(log.actor, self.user)

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
                "category": "identity",
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
        self.assertEqual(log.reason, "uploaded")

    def test_storage_check_rejects_overlapping_public_and_private_roots(self):
        with override_settings(HYDRA_PRIVATE_MEDIA_ROOT=Path(self.private_root, "media")):
            with override_settings(MEDIA_ROOT=self.private_root):
                errors = private_storage_check(None)
        self.assertEqual([error.id for error in errors], ["hydra_documents.E001"])

    def test_existing_horilla_candidate_view_remains_operational(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("candidate-view"))
        self.assertEqual(response.status_code, 200)
