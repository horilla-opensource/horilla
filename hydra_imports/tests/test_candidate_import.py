from datetime import date
from io import BytesIO
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook

from employee.models import Employee
from hydra_coordination.models import ScopeGrant
from hydra_imports.models import CandidateImportRow, CandidateImportSession
from hydra_imports.services import HEADERS, apply_candidate_import
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
