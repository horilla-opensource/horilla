from datetime import date, timedelta

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from hydra_documents.models import PrivateDocument
from hydra_legalization.models import (
    LegalizationCase,
    LegalizationCaseDocument,
    LegalizationStatusHistory,
)
from hydra_legalization.services import (
    attach_private_document,
    create_legalization_case,
    transition_legalization_case,
    update_legalization_case,
)
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


class HydraLegalizationTestCase(HydraRecruitmentTestCase):
    def grant_legalization_read(self):
        self.grant_read()
        self.grant(("hydra_legalization", "view_legalizationcase"))

    def grant_legalization_write(self):
        self.grant_legalization_read()
        self.grant(
            ("hydra_legalization", "add_legalizationcase"),
            ("hydra_legalization", "change_legalizationcase"),
            ("hydra_legalization", "assign_legalizationcase"),
            ("hydra_legalization", "transition_legalizationcase"),
            ("hydra_legalization", "link_privatedocument"),
            ("hydra_documents", "view_privatedocument"),
            ("hydra_documents", "download_privatedocument"),
        )

    def create_case(self, *, person=None, **overrides):
        values = {
            "person": person or self.person_a,
            "case_type": LegalizationCase.CaseType.WORK_PERMIT,
            "responsible": self.user,
            "reference_number": "DUW-2026-001",
            "deadline": date.today() + timedelta(days=14),
        }
        values.update(overrides)
        return create_legalization_case(
            case=LegalizationCase(**values), actor=self.user
        )

    def make_document(self, *, person=None, candidate=None, title="Passport"):
        return PrivateDocument.objects.create(
            person=person or self.person_a,
            candidate=candidate or self.candidate_a,
            title=title,
            category=PrivateDocument.Category.IDENTITY,
            file=f"candidate-documents/test/{title.lower()}.pdf",
            original_filename=f"{title.lower()}.pdf",
            verified_content_type="application/pdf",
            size=10,
            sha256="a" * 64,
            created_by=self.admin,
            modified_by=self.admin,
        )

    def clear_permissions(self):
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)


class LegalizationPermissionAndScopeTests(HydraLegalizationTestCase):
    def test_missing_model_permission_returns_403(self):
        self.login()
        response = self.client.get(reverse("hydra-legalization-list"))
        self.assertEqual(response.status_code, 403)

    def test_list_search_and_direct_detail_apply_current_person_scope(self):
        case_a = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            responsible=self.admin,
            reference_number="VISIBLE-REF",
        )
        case_b = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.VISA,
            responsible=self.admin,
            reference_number="HIDDEN-REF",
        )
        self.grant_legalization_read()
        self.login()

        response = self.client.get(reverse("hydra-legalization-list"), {"q": "REF"})
        denied = self.client.get(case_b.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, case_a.reference_number)
        self.assertNotContains(response, case_b.reference_number)
        self.assertEqual(denied.status_code, 404)

    def test_create_records_draft_and_initial_history(self):
        self.grant_legalization_write()
        self.login()

        response = self.client.post(
            reverse("hydra-legalization-create", args=(self.person_a.uuid,)),
            {
                "case_type": LegalizationCase.CaseType.TEMPORARY_RESIDENCE,
                "responsible": self.user.pk,
                "reference_number": "  WRO   123  ",
                "deadline": "2026-08-15",
                "valid_from": "",
                "valid_until": "",
                "notes": " Reviewed intake ",
            },
        )

        self.assertEqual(response.status_code, 302)
        case = LegalizationCase.objects.get()
        self.assertEqual(case.status, LegalizationCase.Status.DRAFT)
        self.assertEqual(case.reference_number, "WRO 123")
        self.assertEqual(case.created_by, self.user)
        event = case.status_history.get()
        self.assertEqual(event.from_status, "")
        self.assertEqual(event.to_status, LegalizationCase.Status.DRAFT)
        self.assertEqual(event.actor, self.user)

    def test_responsible_user_must_have_permission_and_person_scope(self):
        self.grant_legalization_write()
        outside = User.objects.create_user(
            username="outside-legalization",
            password="test-password",
            is_new_employee=False,
        )
        outside.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="hydra_legalization",
                codename="view_legalizationcase",
            ),
            Permission.objects.get(
                content_type__app_label="hydra_people", codename="view_person"
            ),
        )
        self.login()

        response = self.client.post(
            reverse("hydra-legalization-create", args=(self.person_a.uuid,)),
            {
                "case_type": LegalizationCase.CaseType.VISA,
                "responsible": outside.pk,
                "reference_number": "",
                "deadline": "",
                "valid_from": "",
                "valid_until": "",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot access this person")
        self.assertFalse(LegalizationCase.objects.exists())


class LegalizationTransitionTests(HydraLegalizationTestCase):
    def test_valid_workflow_and_approval_validity_are_audited(self):
        self.grant_legalization_write()
        case = self.create_case()

        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Documents requested",
            actor=self.user,
        )
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.SUBMITTED,
            reason="Submitted to office",
            actor=self.user,
        )
        case.refresh_from_db()
        case.valid_from = date.today()
        case.valid_until = date.today() + timedelta(days=365)
        case = update_legalization_case(case=case, actor=self.user)
        case = transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.APPROVED,
            reason="Decision received",
            actor=self.user,
        )

        self.assertEqual(case.status, LegalizationCase.Status.APPROVED)
        self.assertEqual(case.status_history.count(), 4)
        latest = case.status_history.first()
        self.assertEqual(latest.from_status, LegalizationCase.Status.SUBMITTED)
        self.assertEqual(latest.to_status, LegalizationCase.Status.APPROVED)

    def test_invalid_transition_and_missing_approval_validity_roll_back(self):
        self.grant_legalization_write()
        case = self.create_case()

        with self.assertRaises(ValidationError):
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=LegalizationCase.Status.APPROVED,
                reason="Skipped workflow",
                actor=self.user,
            )
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Ready",
            actor=self.user,
        )
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.SUBMITTED,
            reason="Sent",
            actor=self.user,
        )
        with self.assertRaises(ValidationError):
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=LegalizationCase.Status.APPROVED,
                reason="Decision",
                actor=self.user,
            )

        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.SUBMITTED)
        self.assertEqual(case.status_history.count(), 3)

    def test_rejection_and_closure_require_reason(self):
        self.grant_legalization_write()
        case = self.create_case()
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Ready",
            actor=self.user,
        )
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.SUBMITTED,
            reason="Sent",
            actor=self.user,
        )

        with self.assertRaises(ValidationError):
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=LegalizationCase.Status.REJECTED,
                reason="",
                actor=self.user,
            )

    def test_history_is_append_only(self):
        self.grant_legalization_write()
        case = self.create_case()
        event = case.status_history.get()
        event.reason = "changed"

        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            event.delete()
        with self.assertRaises(TypeError):
            LegalizationStatusHistory.objects.filter(pk=event.pk).update(
                reason="changed"
            )
        with self.assertRaises(TypeError):
            LegalizationStatusHistory.objects.filter(pk=event.pk).delete()

    def test_responsible_change_requires_assignment_permission(self):
        self.grant_legalization_write()
        case = self.create_case()
        permission = Permission.objects.get(
            content_type__app_label="hydra_legalization",
            codename="assign_legalizationcase",
        )
        self.user.user_permissions.remove(permission)
        self.clear_permissions()
        case.responsible = self.admin

        with self.assertRaises(PermissionDenied):
            update_legalization_case(case=case, actor=self.user)


class LegalizationDocumentAndRegressionTests(HydraLegalizationTestCase):
    def test_private_document_link_is_scoped_same_person_and_idempotent(self):
        self.grant_legalization_write()
        case = self.create_case()
        document_a = self.make_document()
        document_b = self.make_document(
            person=self.person_b, candidate=self.candidate_b, title="Other passport"
        )

        first = attach_private_document(
            case_uuid=case.uuid,
            document_uuid=document_a.uuid,
            role=LegalizationCaseDocument.Role.IDENTITY,
            actor=self.user,
        )
        second = attach_private_document(
            case_uuid=case.uuid,
            document_uuid=document_a.uuid,
            role=LegalizationCaseDocument.Role.IDENTITY,
            actor=self.user,
        )
        with self.assertRaises(ValidationError):
            attach_private_document(
                case_uuid=case.uuid,
                document_uuid=document_b.uuid,
                role=LegalizationCaseDocument.Role.IDENTITY,
                actor=self.user,
            )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(case.document_links.count(), 1)

    def test_detail_exposes_authorized_download_route_not_storage_path(self):
        self.grant_legalization_write()
        case = self.create_case()
        document = self.make_document()
        attach_private_document(
            case_uuid=case.uuid,
            document_uuid=document.uuid,
            role=LegalizationCaseDocument.Role.IDENTITY,
            actor=self.user,
        )
        self.login()

        response = self.client.get(case.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse("hydra-private-document-download", args=(document.uuid,))
        )
        self.assertNotContains(response, document.file.name)
        self.assertNotContains(response, "/media/")

    def test_existing_horilla_document_request_view_remains_operational(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("document-request-view"))
        self.assertEqual(response.status_code, 200)
