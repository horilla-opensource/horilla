from datetime import date, timedelta
from io import BytesIO, StringIO
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from employee.models import Employee
from hydra_coordination.models import ScopeGrant
from hydra_imports.models import (
    CandidateImportLifecycleEvent,
    CandidateImportRow,
    CandidateImportSession,
)
from hydra_imports.services import (
    HEADERS,
    apply_candidate_import,
    preview_candidate_import,
    purge_expired_candidate_import_data,
)
from hydra_people.models import Person, PersonApplication
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from recruitment.models import Candidate


class CandidateImportTestCase(HydraRecruitmentTestCase):
    def grant_import(self):
        self.grant_write()
        self.grant(
            ("hydra_people", "add_person"),
            ("hydra_imports", "view_candidateimportsession"),
            ("hydra_imports", "import_candidate"),
            ("hydra_imports", "purge_candidateimportsession"),
        )

    def candidate_row(self, **overrides):
        values = {
            "passport_name": "ZORIANA NOVAK",
            "first_name": "Zoriana",
            "last_name": "Novak",
            "date_of_birth": date(1995, 6, 7),
            "gender": "female",
            "citizenship": "UA",
            "preferred_language": "uk",
            "email": "zoriana.novak@example.test",
            "phone": "+48123123123",
            "whatsapp_viber": "+48123123123",
            "candidate_mobile": "+48123123123",
        }
        values.update(overrides)
        return values

    def workbook_upload(
        self,
        rows,
        *,
        headers=HEADERS,
        formula_cell=None,
        extra_cell=None,
    ):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Candidates"
        worksheet.append(list(headers))
        for row in rows:
            worksheet.append([row.get(header) for header in HEADERS])
        if formula_cell:
            worksheet[formula_cell] = "=1+1"
        if extra_cell:
            worksheet[extra_cell] = "unexpected"
        output = BytesIO()
        workbook.save(output)
        return SimpleUploadedFile(
            "candidates.xlsx",
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def preview(self, rows, **upload_kwargs):
        response = self.client.post(
            reverse("hydra-candidate-import"),
            {
                "recruitment": self.recruitment_a.pk,
                "job_position": self.job_a.pk,
                "workbook": self.workbook_upload(rows, **upload_kwargs),
            },
        )
        return response


class CandidateImportPermissionAndPreviewTests(CandidateImportTestCase):
    def test_missing_import_permission_returns_403(self):
        self.grant_write()
        self.grant(("hydra_people", "add_person"))
        self.login()

        response = self.client.get(reverse("hydra-candidate-import"))

        self.assertEqual(response.status_code, 403)

    def test_out_of_scope_recruitment_is_rejected_by_form(self):
        self.grant_import()
        self.login()

        response = self.client.post(
            reverse("hydra-candidate-import"),
            {
                "recruitment": self.recruitment_b.pk,
                "job_position": self.job_b.pk,
                "workbook": self.workbook_upload([self.candidate_row()]),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(CandidateImportSession.objects.exists())

    def test_preview_normalizes_rows_and_records_stable_fingerprint(self):
        self.grant_import()
        self.login()

        response = self.preview(
            [
                self.candidate_row(
                    passport_name="  ZORIANA   NOVAK ",
                    citizenship="ua",
                    email="ZORIANA.NOVAK@EXAMPLE.TEST",
                )
            ]
        )

        self.assertEqual(response.status_code, 302)
        session = CandidateImportSession.objects.get()
        row = session.rows.get()
        self.assertEqual(session.status, CandidateImportSession.Status.READY)
        self.assertEqual((session.row_count, session.valid_count), (1, 1))
        self.assertEqual(len(session.file_sha256), 64)
        self.assertEqual(len(session.fingerprint), 64)
        self.assertEqual(row.passport_name, "ZORIANA NOVAK")
        self.assertEqual(row.citizenship, "UA")
        self.assertEqual(row.email, "zoriana.novak@example.test")

    def test_intra_workbook_identity_and_email_duplicates_block_every_copy(self):
        self.grant_import()
        self.login()
        duplicate = self.candidate_row()

        response = self.preview([duplicate, duplicate])

        self.assertEqual(response.status_code, 302)
        session = CandidateImportSession.objects.get()
        self.assertEqual(session.status, CandidateImportSession.Status.BLOCKED)
        self.assertEqual(session.duplicate_count, 2)
        self.assertEqual(session.valid_count, 0)
        self.assertEqual(
            set(session.rows.values_list("outcome", flat=True)),
            {CandidateImportRow.Outcome.DUPLICATE},
        )

    def test_existing_person_identity_and_recruitment_email_are_duplicates(self):
        self.grant_import()
        self.login()
        existing_identity = self.candidate_row(
            passport_name=self.person_a.passport_name,
            first_name=self.person_a.first_name,
            last_name=self.person_a.last_name,
            date_of_birth=self.person_a.date_of_birth,
            gender=self.person_a.gender,
            citizenship=self.person_a.citizenship,
            preferred_language=self.person_a.preferred_language,
            email="new-for-existing-person@example.test",
        )
        existing_email = self.candidate_row(
            passport_name="TARAS UNIQUE",
            first_name="Taras",
            last_name="Unique",
            date_of_birth=date(1990, 1, 2),
            email=self.candidate_a.email,
        )

        response = self.preview([existing_identity, existing_email])

        self.assertEqual(response.status_code, 302)
        session = CandidateImportSession.objects.get()
        reasons = " ".join(session.rows.values_list("duplicate_reason", flat=True))
        self.assertEqual(session.duplicate_count, 2)
        self.assertIn("Hydra Person", reasons)
        self.assertIn("already has an application", reasons)

    def test_formula_and_wrong_headers_are_rejected_without_preview_write(self):
        self.grant_import()
        self.login()

        formula_response = self.preview([self.candidate_row()], formula_cell="A2")
        wrong_header_response = self.preview(
            [self.candidate_row()],
            headers=("wrong_header",) + HEADERS[1:],
        )
        oversized_area_response = self.preview(
            [self.candidate_row()],
            extra_cell="A503",
        )

        self.assertEqual(formula_response.status_code, 400)
        self.assertContains(formula_response, "Formulas are not accepted", status_code=400)
        self.assertEqual(wrong_header_response.status_code, 400)
        self.assertContains(wrong_header_response, "headers must exactly match", status_code=400)
        self.assertEqual(oversized_area_response.status_code, 400)
        self.assertContains(
            oversized_area_response,
            "exceeds the 500-row data area",
            status_code=400,
        )
        self.assertFalse(CandidateImportSession.objects.exists())

    def test_another_importer_cannot_open_an_owned_preview(self):
        self.grant_import()
        self.login()
        self.preview([self.candidate_row()])
        session = CandidateImportSession.objects.get()

        outsider = User.objects.create_user(
            username="second-importer",
            password="test-password",
            is_new_employee=False,
        )
        Employee.objects.create(
            employee_user_id=outsider,
            employee_first_name="Second",
            employee_last_name="Importer",
            email="second-importer@example.test",
            phone="+48199999999",
        )
        outsider.user_permissions.set(self.user.user_permissions.all())
        ScopeGrant.objects.create(user=outsider, team=self.team_a)
        self.client.force_login(outsider)

        response = self.client.get(session.get_absolute_url())

        self.assertEqual(response.status_code, 404)

    def test_read_only_admin_applies_owner_and_recruitment_scope(self):
        self.grant_import()
        self.login()
        self.preview([self.candidate_row()])
        visible = CandidateImportSession.objects.get()
        hidden = CandidateImportSession.objects.create(
            recruitment=self.recruitment_b,
            job_position=self.job_b,
            source_filename="hidden.xlsx",
            file_sha256="a" * 64,
            fingerprint="b" * 64,
            status=CandidateImportSession.Status.BLOCKED,
            sensitive_data_purge_after=timezone.now() + timedelta(hours=72),
            created_by=self.admin,
            modified_by=self.admin,
        )
        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))

        listing = self.client.get(
            reverse("admin:hydra_imports_candidateimportsession_changelist")
        )
        denied = self.client.get(
            reverse(
                "admin:hydra_imports_candidateimportsession_change",
                args=(hidden.pk,),
            )
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            set(listing.context["cl"].queryset.values_list("pk", flat=True)),
            {visible.pk},
        )
        self.assertEqual(denied.status_code, 302)
        self.assertEqual(denied.url, reverse("admin:index"))


class CandidateImportApplyTests(CandidateImportTestCase):
    def setUp(self):
        super().setUp()
        self.grant_import()
        self.login()

    def test_apply_creates_person_candidate_link_and_is_idempotent(self):
        response = self.preview([self.candidate_row()])
        session = CandidateImportSession.objects.get()
        person_count = Person.objects.count()
        candidate_count = Candidate._base_manager.count()

        first = self.client.post(
            reverse("hydra-candidate-import-apply", args=(session.uuid,))
        )
        second = self.client.post(
            reverse("hydra-candidate-import-apply", args=(session.uuid,))
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Person.objects.count(), person_count + 1)
        self.assertEqual(Candidate._base_manager.count(), candidate_count + 1)
        session.refresh_from_db()
        row = session.rows.get()
        self.assertEqual(session.status, CandidateImportSession.Status.APPLIED)
        self.assertEqual(session.applied_by, self.user)
        self.assertIsNotNone(session.applied_at)
        self.assertEqual(row.created_person.lifecycle_state, Person.LifecycleState.CANDIDATE)
        self.assertEqual(
            PersonApplication.objects.get(candidate=row.created_candidate).person,
            row.created_person,
        )

    def test_blocked_preview_cannot_apply(self):
        self.preview([self.candidate_row(), self.candidate_row()])
        session = CandidateImportSession.objects.get()

        response = self.client.post(
            reverse("hydra-candidate-import-apply", args=(session.uuid,))
        )

        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, CandidateImportSession.Status.BLOCKED)
        self.assertFalse(session.rows.exclude(created_person=None).exists())

    def test_second_row_failure_rolls_back_entire_apply(self):
        second_row = self.candidate_row(
            passport_name="MYKOLA SECOND",
            first_name="Mykola",
            last_name="Second",
            email="mykola.second@example.test",
        )
        self.preview([self.candidate_row(), second_row])
        session = CandidateImportSession.objects.get()
        person_count = Person.objects.count()
        candidate_count = Candidate._base_manager.count()

        from hydra_imports import services

        original = services.create_candidate_application
        calls = 0

        def fail_second(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValidationError("simulated second-row failure")
            return original(**kwargs)

        with mock.patch(
            "hydra_imports.services.create_candidate_application",
            side_effect=fail_second,
        ):
            with self.assertRaisesMessage(ValidationError, "simulated second-row failure"):
                apply_candidate_import(session_uuid=session.uuid, actor=self.user)

        self.assertEqual(Person.objects.count(), person_count)
        self.assertEqual(Candidate._base_manager.count(), candidate_count)
        session.refresh_from_db()
        self.assertEqual(session.status, CandidateImportSession.Status.READY)
        self.assertFalse(session.rows.exclude(created_person=None).exists())


class CandidateImportCompatibilityTests(CandidateImportTestCase):
    def test_template_download_and_original_employee_import_remain_operational(self):
        self.grant_import()
        self.login()

        template_response = self.client.get(
            reverse("hydra-candidate-import-template")
        )
        self.client.force_login(self.admin)
        legacy_response = self.client.get(reverse("employee-import"))

        self.assertEqual(template_response.status_code, 200)
        self.assertEqual(
            template_response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(legacy_response.status_code, 200)


@override_settings(
    HYDRA_IMPORT_PREVIEW_RETENTION_HOURS=72,
    HYDRA_IMPORT_APPLIED_RETENTION_HOURS=24,
)
class CandidateImportRetentionTests(CandidateImportTestCase):
    def setUp(self):
        super().setUp()
        self.grant_import()
        self.login()

    def service_preview(self, *, row=None, content=None, filename="candidates.xlsx"):
        if content is None:
            upload = self.workbook_upload([row or self.candidate_row()])
            content = upload.read()
        session = preview_candidate_import(
            workbook=SimpleUploadedFile(
                filename,
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            recruitment=self.recruitment_a,
            job_position=self.job_a,
            actor=self.user,
        )
        return session, content

    def test_preview_and_apply_snapshot_bounded_retention_deadlines(self):
        before_preview = timezone.now()
        session, _content = self.service_preview()

        self.assertGreaterEqual(
            session.sensitive_data_purge_after,
            before_preview + timedelta(hours=71, minutes=59),
        )
        before_apply = timezone.now()
        applied = apply_candidate_import(session_uuid=session.uuid, actor=self.user)

        self.assertEqual(applied.status, CandidateImportSession.Status.APPLIED)
        self.assertGreaterEqual(
            applied.sensitive_data_purge_after,
            before_apply + timedelta(hours=23, minutes=59),
        )
        self.assertLess(
            applied.sensitive_data_purge_after,
            before_apply + timedelta(hours=24, minutes=1),
        )

    def test_expired_apply_redacts_source_data_and_commits_audit_event(self):
        session, _content = self.service_preview()
        person_count = Person.objects.count()
        session.sensitive_data_purge_after = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=("sensitive_data_purge_after",))

        detail_while_waiting_for_purge = self.client.get(session.get_absolute_url())

        with self.assertRaisesMessage(ValidationError, "preview expired"):
            apply_candidate_import(session_uuid=session.uuid, actor=self.user)

        session.refresh_from_db()
        row = session.rows.get()
        event = session.lifecycle_events.get()
        self.assertEqual(session.status, CandidateImportSession.Status.EXPIRED)
        self.assertNotContains(
            detail_while_waiting_for_purge,
            "zoriana.novak@example.test",
        )
        self.assertNotContains(detail_while_waiting_for_purge, "ZORIANA NOVAK")
        self.assertNotContains(detail_while_waiting_for_purge, "candidates.xlsx")
        self.assertContains(detail_while_waiting_for_purge, "Retained import audit")
        self.assertNotIn("candidates.xlsx", str(session))
        self.assertIn("Retained import audit", str(session))
        self.assertEqual(session.source_filename, "purged-candidate-import.xlsx")
        self.assertIsNotNone(session.sensitive_data_purged_at)
        self.assertEqual(row.passport_name, "")
        self.assertEqual(row.email, "")
        self.assertIsNone(row.date_of_birth)
        self.assertEqual(Person.objects.count(), person_count)
        self.assertEqual(event.source, CandidateImportLifecycleEvent.Source.SYSTEM)
        self.assertEqual(
            event.reason,
            CandidateImportLifecycleEvent.Reason.RETENTION_EXPIRED,
        )
        self.assertIsNone(event.actor)

    def test_owner_can_discard_source_data_idempotently_through_post(self):
        session, _content = self.service_preview()
        detail_before = self.client.get(session.get_absolute_url())

        first = self.client.post(
            reverse("hydra-candidate-import-discard", args=(session.uuid,))
        )
        second = self.client.post(
            reverse("hydra-candidate-import-discard", args=(session.uuid,))
        )

        self.assertContains(detail_before, "zoriana.novak@example.test")
        self.assertRedirects(first, session.get_absolute_url())
        self.assertRedirects(second, session.get_absolute_url())
        session.refresh_from_db()
        event = session.lifecycle_events.get()
        self.assertEqual(session.status, CandidateImportSession.Status.EXPIRED)
        self.assertEqual(event.source, CandidateImportLifecycleEvent.Source.USER)
        self.assertEqual(event.actor_id, self.user.pk)
        self.assertEqual(session.lifecycle_events.count(), 1)
        detail_after = self.client.get(session.get_absolute_url())
        self.assertNotContains(detail_after, "zoriana.novak@example.test")
        self.assertNotContains(detail_after, "ZORIANA NOVAK")
        self.assertContains(detail_after, "Source data redacted")

    def test_discard_requires_the_dedicated_permission(self):
        session, _content = self.service_preview()
        permission = Permission.objects.get(
            content_type__app_label="hydra_imports",
            codename="purge_candidateimportsession",
        )
        self.user.user_permissions.remove(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

        response = self.client.post(
            reverse("hydra-candidate-import-discard", args=(session.uuid,))
        )

        self.assertEqual(response.status_code, 403)
        session.refresh_from_db()
        self.assertIsNone(session.sensitive_data_purged_at)

    def test_applied_redaction_preserves_links_hashes_and_idempotency(self):
        session, content = self.service_preview()
        apply_candidate_import(session_uuid=session.uuid, actor=self.user)
        session.refresh_from_db()
        original_fingerprint = session.fingerprint
        original_file_sha256 = session.file_sha256
        original_row_hash = session.rows.get().source_row_hash
        session.sensitive_data_purge_after = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=("sensitive_data_purge_after",))

        purged = purge_expired_candidate_import_data(limit=10)
        repeated, _content = self.service_preview(content=content)

        session.refresh_from_db()
        row = session.rows.get()
        self.assertEqual(purged, 1)
        self.assertEqual(session.status, CandidateImportSession.Status.APPLIED)
        self.assertEqual(repeated.pk, session.pk)
        self.assertEqual(session.fingerprint, original_fingerprint)
        self.assertEqual(session.file_sha256, original_file_sha256)
        self.assertEqual(row.source_row_hash, original_row_hash)
        self.assertIsNotNone(row.created_person_id)
        self.assertIsNotNone(row.created_candidate_id)
        self.assertEqual(row.passport_name, "")
        event = session.lifecycle_events.get()
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            event.delete()
        with self.assertRaises(TypeError):
            CandidateImportLifecycleEvent.objects.filter(pk=event.pk).update(
                rows_redacted=0
            )

    def test_expired_unapplied_fingerprint_can_be_previewed_again(self):
        expired, content = self.service_preview()
        expired.sensitive_data_purge_after = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=("sensitive_data_purge_after",))

        replacement, _content = self.service_preview(content=content)

        expired.refresh_from_db()
        self.assertNotEqual(replacement.pk, expired.pk)
        self.assertEqual(expired.status, CandidateImportSession.Status.EXPIRED)
        self.assertEqual(replacement.status, CandidateImportSession.Status.READY)
        self.assertEqual(replacement.fingerprint, expired.fingerprint)
        self.assertEqual(CandidateImportSession.objects.count(), 2)

    def test_purge_command_is_bounded(self):
        first, _content = self.service_preview()
        second, _content = self.service_preview(
            row=self.candidate_row(
                passport_name="SECOND IMPORT",
                first_name="Second",
                last_name="Import",
                email="second.import@example.test",
            ),
            filename="second.xlsx",
        )
        due = timezone.now() - timedelta(seconds=1)
        CandidateImportSession.objects.filter(pk__in=(first.pk, second.pk)).update(
            sensitive_data_purge_after=due
        )
        output = StringIO()

        call_command("purge_candidate_import_data", "--limit", "1", stdout=output)

        self.assertEqual(
            CandidateImportSession.objects.filter(
                sensitive_data_purged_at__isnull=False
            ).count(),
            1,
        )
        self.assertIn("candidate imports redacted: 1", output.getvalue())
