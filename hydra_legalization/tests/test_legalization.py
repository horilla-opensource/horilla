from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from hydra_documents.models import PrivateDocument, PrivateDocumentType
from hydra_legalization.models import (
    LegalizationAuthority,
    LegalizationAuthorityEvent,
    LegalizationCase,
    LegalizationCaseDocument,
    LegalizationConfigurationEvent,
    LegalizationProcedureRequirement,
    LegalizationProcedureType,
    LegalizationRenewalLink,
    LegalizationStatusHistory,
)
from hydra_legalization.services import (
    adopt_legacy_legalization_case_policy,
    attach_private_document,
    create_legalization_case,
    create_legalization_renewal,
    link_existing_legalization_renewal,
    record_legalization_authority_event,
    save_legalization_authority,
    save_legalization_requirement,
    transition_legalization_case,
    update_legalization_case,
)
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from hydra_ops.readiness import domain_integrity_results


class HydraLegalizationTestCase(HydraRecruitmentTestCase):
    def grant_legalization_read(self):
        self.grant_read()
        self.grant(
            ("hydra_legalization", "view_legalizationcase"),
            ("hydra_legalization", "view_legalizationproceduretype"),
            ("hydra_legalization", "view_legalizationauthority"),
        )

    def grant_legalization_write(self):
        self.grant_legalization_read()
        self.grant(
            ("hydra_legalization", "add_legalizationcase"),
            ("hydra_legalization", "change_legalizationcase"),
            ("hydra_legalization", "assign_legalizationcase"),
            ("hydra_legalization", "transition_legalizationcase"),
            ("hydra_legalization", "link_privatedocument"),
            ("hydra_legalization", "view_legalizationauthorityevent"),
            ("hydra_legalization", "record_legalizationauthorityevent"),
            ("hydra_legalization", "view_legalizationrenewallink"),
            ("hydra_legalization", "create_legalizationrenewallink"),
            ("hydra_documents", "view_privatedocument"),
            ("hydra_documents", "download_privatedocument"),
        )

    def create_case(self, *, person=None, **overrides):
        person = person or self.person_a
        case_type = overrides.pop(
            "case_type", LegalizationCase.CaseType.WORK_PERMIT
        )
        company = overrides.pop(
            "company", self.company_b if person.pk == self.person_b.pk else self.company_a
        )
        values = {
            "person": person,
            "company": company,
            "procedure_type": self.legalization_case_configuration(
                company=company, case_type=case_type
            )["procedure_type"],
            "responsible": self.user,
            "reference_number": "DUW-2026-001",
            "deadline": date.today() + timedelta(days=14),
        }
        values.update(overrides)
        return create_legalization_case(
            case=LegalizationCase(**values), actor=self.user
        )

    def make_document(
        self,
        *,
        person=None,
        candidate=None,
        title="Passport",
        type_code="identity-document",
    ):
        document_type = PrivateDocumentType.objects.get(
            code=type_code, company__isnull=True
        )
        return PrivateDocument.objects.create(
            person=person or self.person_a,
            candidate=candidate or self.candidate_a,
            document_type=document_type,
            title=title,
            category=document_type.category,
            file=f"candidate-documents/test/{title.lower()}.pdf",
            original_filename=f"{title.lower()}.pdf",
            verified_content_type="application/pdf",
            size=10,
            sha256="a" * 64,
            scanner="clamd",
            scanned_at=timezone.now(),
            created_by=self.admin,
            modified_by=self.admin,
        )

    def record_event(self, *, case, event_type, document=None, **overrides):
        document = document or self.make_document(title=f"Evidence {uuid4().hex[:8]}")
        values = {
            "case_uuid": case.uuid,
            "event_type": event_type,
            "occurred_on": date.today(),
            "authority_uuid": self.legalization_authority.uuid,
            "channel": LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
            "reference_number": "",
            "response_deadline": None,
            "valid_from": None,
            "valid_until": None,
            "evidence_document_uuid": document.uuid,
            "details": "Recorded correspondence",
            "idempotency_key": uuid4(),
            "actor": self.user,
        }
        values.update(overrides)
        return record_legalization_authority_event(**values)

    def approve_case(self, *, person=None, case_type=None, responsible=None):
        case = self.create_case(
            person=person,
            case_type=case_type or LegalizationCase.CaseType.WORK_PERMIT,
            responsible=responsible or self.user,
        )
        case.status = LegalizationCase.Status.APPROVED
        case.valid_from = date.today() - timedelta(days=300)
        case.valid_until = date.today() + timedelta(days=65)
        case.full_clean()
        case.save(update_fields=("status", "valid_from", "valid_until"))
        return case

    def clear_permissions(self):
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def grant_legalization_configuration_write(self):
        self.grant_legalization_read()
        self.grant(
            ("hydra_legalization", "view_legalizationprocedurerequirement"),
            ("hydra_legalization", "add_legalizationproceduretype"),
            ("hydra_legalization", "change_legalizationproceduretype"),
            ("hydra_legalization", "add_legalizationauthority"),
            ("hydra_legalization", "change_legalizationauthority"),
            ("hydra_legalization", "add_legalizationprocedurerequirement"),
            ("hydra_legalization", "change_legalizationprocedurerequirement"),
            ("hydra_documents", "view_privatedocumenttype"),
        )


class LegalizationConfigurationTests(HydraLegalizationTestCase):
    def test_legacy_authority_policy_adoption_is_one_time_scoped_and_audited(self):
        self.grant_legalization_write()
        case = self.create_case()
        pending_snapshot = dict(case.procedure_snapshot)
        pending_snapshot["authorities"] = []
        pending_snapshot["requires_authority"] = True
        pending_snapshot["legacy_authority_policy_pending"] = True
        LegalizationCase._base_manager.filter(pk=case.pk).update(
            procedure_snapshot=pending_snapshot
        )

        with self.assertRaises(PermissionDenied):
            adopt_legacy_legalization_case_policy(
                case_uuid=case.uuid,
                authority_uuids=[self.legalization_authority.uuid],
                reason="Attempted by operator",
                actor=self.user,
            )

        adopted, event = adopt_legacy_legalization_case_policy(
            case_uuid=case.uuid,
            authority_uuids=[self.legalization_authority.uuid],
            reason="Verified against the legacy case register",
            actor=self.admin,
        )
        self.assertFalse(
            adopted.procedure_snapshot["legacy_authority_policy_pending"]
        )
        self.assertEqual(
            adopted.procedure_snapshot["authorities"][0]["uuid"],
            str(self.legalization_authority.uuid),
        )
        self.assertEqual(
            event.entity_type,
            LegalizationConfigurationEvent.EntityType.CASE_POLICY,
        )
        self.assertEqual(event.action, LegalizationConfigurationEvent.Action.ADOPTED)
        self.assertEqual(
            event.reason, "Verified against the legacy case register"
        )
        with self.assertRaises(ValidationError):
            adopt_legacy_legalization_case_policy(
                case_uuid=case.uuid,
                authority_uuids=[self.legalization_authority.uuid],
                reason="Second attempt",
                actor=self.admin,
            )

        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Adopted policy verified",
            actor=self.user,
        )
        _authority_event, created = self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
        )
        self.assertTrue(created)

    def test_company_configuration_ui_is_scoped_and_audited(self):
        self.grant_legalization_configuration_write()
        outside = LegalizationAuthority.objects.create(
            company=self.company_b,
            code="outside-office",
            name="Outside company office",
            jurisdiction="Outside scope",
            allowed_channels=[LegalizationAuthorityEvent.Channel.EMAIL],
            created_by=self.admin,
            modified_by=self.admin,
        )
        self.login()

        response = self.client.post(
            reverse("hydra-legalization-authority-create"),
            {
                "company": self.company_a.pk,
                "code": "local-office",
                "name": "Local legalization office",
                "jurisdiction": "Company A",
                "allowed_channels": [
                    LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
                    LegalizationAuthorityEvent.Channel.EMAIL,
                ],
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("hydra-legalization-configuration"))
        authority = LegalizationAuthority.objects.get(
            company=self.company_a, code="local-office"
        )

        response = self.client.post(
            reverse("hydra-legalization-procedure-create"),
            {
                "company": self.company_a.pk,
                "code": "company-work-permit",
                "name": "Company work permit",
                "case_type": LegalizationCase.CaseType.WORK_PERMIT,
                "description": "Company-approved procedure",
                "default_deadline_days": "30",
                "renewal_lead_days": "90",
                "requires_authority": "on",
                "authorities": [authority.pk],
                "enabled_statuses": list(LegalizationCase.Status.values),
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("hydra-legalization-configuration"))
        procedure = LegalizationProcedureType.objects.get(
            company=self.company_a, code="company-work-permit"
        )

        document_type = PrivateDocumentType.objects.get(
            company__isnull=True, code="identity-document"
        )
        response = self.client.post(
            reverse(
                "hydra-legalization-requirement-create", args=(procedure.uuid,)
            ),
            {
                "procedure": procedure.pk,
                "code": "identity-before-submission",
                "name": "Identity before submission",
                "document_type": document_type.pk,
                "required_before_status": LegalizationCase.Status.SUBMITTED,
                "sort_order": "10",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("hydra-legalization-configuration"))

        listing = self.client.get(reverse("hydra-legalization-configuration"))
        denied = self.client.get(
            reverse("hydra-legalization-authority-update", args=(outside.uuid,))
        )
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "Company work permit")
        self.assertContains(listing, "Identity before submission")
        self.assertContains(listing, "Local legalization office")
        self.assertNotContains(listing, "Outside company office")
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(
            LegalizationConfigurationEvent.objects.filter(
                entity_uuid__in=(authority.uuid, procedure.uuid)
            ).count(),
            2,
        )
        requirement = LegalizationProcedureRequirement.objects.get(
            procedure=procedure, code="identity-before-submission"
        )
        self.assertTrue(
            LegalizationConfigurationEvent.objects.filter(
                entity_uuid=requirement.uuid,
                entity_type=LegalizationConfigurationEvent.EntityType.REQUIREMENT,
            ).exists()
        )
        with self.assertRaises(TypeError):
            authority.delete()
        with self.assertRaises(TypeError):
            LegalizationProcedureRequirement.objects.filter(
                pk=requirement.pk
            ).delete()

    def test_case_keeps_authority_policy_snapshot_after_configuration_change(self):
        self.grant_legalization_write()
        old_name = self.legalization_authority.name
        old_case = self.create_case()
        transition_legalization_case(
            case_uuid=old_case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Ready under original policy",
            actor=self.user,
        )
        self.legalization_authority.refresh_from_db()
        save_legalization_authority(
            actor=self.admin,
            authority=self.legalization_authority,
            cleaned_data={
                "company": None,
                "code": self.legalization_authority.code,
                "name": "Renamed competent authority",
                "jurisdiction": self.legalization_authority.jurisdiction,
                "allowed_channels": [LegalizationAuthorityEvent.Channel.EMAIL],
                "is_active": True,
            },
        )

        event, created = self.record_event(
            case=old_case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            channel=LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
        )
        self.assertTrue(created)
        self.assertEqual(event.authority, old_name)
        self.assertIn(
            LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
            event.authority_snapshot["allowed_channels"],
        )

        new_case = self.create_case(case_type=LegalizationCase.CaseType.VISA)
        transition_legalization_case(
            case_uuid=new_case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Ready under revised policy",
            actor=self.user,
        )
        with self.assertRaises(ValidationError):
            self.record_event(
                case=new_case,
                event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
                channel=LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
            )
        new_case.refresh_from_db()
        self.assertEqual(
            new_case.status, LegalizationCase.Status.COLLECTING_DOCUMENTS
        )
        self.assertFalse(new_case.authority_events.exists())

    def test_snapshotted_document_requirement_blocks_submission(self):
        self.grant_legalization_write()
        procedure = self.legalization_case_configuration(
            company=self.company_a
        )["procedure_type"]
        identity_type = PrivateDocumentType.objects.get(
            company__isnull=True, code="identity-document"
        )
        save_legalization_requirement(
            actor=self.admin,
            requirement=LegalizationProcedureRequirement(),
            cleaned_data={
                "procedure": procedure,
                "code": "identity-before-submission",
                "name": "Identity document",
                "document_type": identity_type,
                "required_before_status": LegalizationCase.Status.SUBMITTED,
                "sort_order": 10,
                "is_active": True,
            },
        )
        case = self.create_case()
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Collecting",
            actor=self.user,
        )
        wrong_evidence = self.make_document(
            title="Wrong requirement evidence", type_code="legalization-document"
        )

        with self.assertRaises(ValidationError):
            self.record_event(
                case=case,
                event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
                document=wrong_evidence,
            )
        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.COLLECTING_DOCUMENTS)
        self.assertFalse(case.authority_events.exists())

        identity_evidence = self.make_document(title="Required identity evidence")
        _event, created = self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            document=identity_evidence,
        )
        self.assertTrue(created)
        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.SUBMITTED)


class LegalizationPermissionAndScopeTests(HydraLegalizationTestCase):
    def test_missing_model_permission_returns_403(self):
        self.login()
        response = self.client.get(reverse("hydra-legalization-list"))
        self.assertEqual(response.status_code, 403)

    def test_list_search_and_direct_detail_apply_current_person_scope(self):
        case_a = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            responsible=self.admin,
            reference_number="VISIBLE-REF",
        )
        case_b = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.VISA,
            **self.legalization_case_configuration(
                company=self.company_b, case_type=LegalizationCase.CaseType.VISA
            ),
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
                "company": self.company_a.pk,
                "procedure_type": self.legalization_case_configuration(
                    company=self.company_a,
                    case_type=LegalizationCase.CaseType.TEMPORARY_RESIDENCE,
                )["procedure_type"].pk,
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

    def test_create_rejects_duplicate_active_person_and_case_type(self):
        self.grant_legalization_write()
        self.create_case()

        with self.assertRaises(ValidationError):
            self.create_case(reference_number="SECOND-ACTIVE")

        self.assertEqual(LegalizationCase.objects.count(), 1)

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
                "company": self.company_a.pk,
                "procedure_type": self.legalization_case_configuration(
                    company=self.company_a,
                    case_type=LegalizationCase.CaseType.VISA,
                )["procedure_type"].pk,
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

    def test_read_only_admin_applies_the_same_person_scope(self):
        visible = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            responsible=self.admin,
            reference_number="VISIBLE-ADMIN-REF",
        )
        hidden = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.VISA,
            **self.legalization_case_configuration(
                company=self.company_b, case_type=LegalizationCase.CaseType.VISA
            ),
            responsible=self.admin,
            reference_number="HIDDEN-ADMIN-REF",
        )
        self.grant_legalization_read()
        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))
        self.login()

        listing = self.client.get(
            reverse("admin:hydra_legalization_legalizationcase_changelist")
        )
        denied = self.client.get(
            reverse(
                "admin:hydra_legalization_legalizationcase_change",
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

    def test_renewal_admin_applies_scope_to_both_cases(self):
        visible_predecessor = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            status=LegalizationCase.Status.APPROVED,
            responsible=self.admin,
            valid_from=date.today() - timedelta(days=300),
            valid_until=date.today() + timedelta(days=65),
        )
        visible_successor = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            responsible=self.admin,
        )
        hidden_predecessor = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_b),
            status=LegalizationCase.Status.APPROVED,
            responsible=self.admin,
            valid_from=date.today() - timedelta(days=300),
            valid_until=date.today() + timedelta(days=65),
        )
        hidden_successor = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_b),
            responsible=self.admin,
        )
        visible = LegalizationRenewalLink.objects.create(
            predecessor=visible_predecessor,
            successor=visible_successor,
            source=LegalizationRenewalLink.Source.CREATED,
            actor=self.admin,
        )
        hidden = LegalizationRenewalLink.objects.create(
            predecessor=hidden_predecessor,
            successor=hidden_successor,
            source=LegalizationRenewalLink.Source.CREATED,
            actor=self.admin,
        )
        self.grant_legalization_write()
        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))
        self.login()

        listing = self.client.get(
            reverse("admin:hydra_legalization_legalizationrenewallink_changelist")
        )
        denied = self.client.get(
            reverse(
                "admin:hydra_legalization_legalizationrenewallink_change",
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
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            reference_number="DUW-SUBMITTED-001",
        )
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.APPROVED,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=365),
            details="Decision received",
        )
        case.refresh_from_db()

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
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
        )
        with self.assertRaises(ValidationError):
            self.record_event(
                case=case,
                event_type=LegalizationAuthorityEvent.EventType.APPROVED,
                details="Decision",
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
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
        )

        with self.assertRaises(ValidationError):
            self.record_event(
                case=case,
                event_type=LegalizationAuthorityEvent.EventType.REJECTED,
                details="",
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


class LegalizationRenewalTests(HydraLegalizationTestCase):
    def test_create_renewal_is_atomic_idempotent_and_append_only(self):
        self.grant_legalization_write()
        predecessor = self.approve_case()
        deadline = date.today() + timedelta(days=30)

        first, created = create_legalization_renewal(
            predecessor_uuid=predecessor.uuid,
            deadline=deadline,
            notes="Prepare updated application",
            actor=self.user,
        )
        second, duplicate_created = create_legalization_renewal(
            predecessor_uuid=predecessor.uuid,
            deadline=deadline,
            notes="Prepare updated application",
            actor=self.user,
        )

        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.person_id, predecessor.person_id)
        self.assertEqual(first.case_type, predecessor.case_type)
        self.assertEqual(first.status, LegalizationCase.Status.DRAFT)
        self.assertEqual(first.responsible_id, self.user.pk)
        self.assertEqual(first.deadline, deadline)
        self.assertEqual(first.reference_number, "")
        self.assertIsNone(first.valid_from)
        self.assertIsNone(first.valid_until)
        history = first.status_history.get()
        self.assertEqual(history.reason, "renewal_created")
        link = LegalizationRenewalLink.objects.get()
        self.assertEqual(link.predecessor_id, predecessor.pk)
        self.assertEqual(link.successor_id, first.pk)
        self.assertEqual(link.source, LegalizationRenewalLink.Source.CREATED)
        self.assertEqual(link.actor_id, self.user.pk)
        with self.assertRaises(TypeError):
            link.save()
        with self.assertRaises(TypeError):
            link.delete()
        with self.assertRaises(TypeError):
            LegalizationRenewalLink.objects.filter(pk=link.pk).update(
                reason="changed"
            )

    def test_renewal_rejects_unapproved_nonowner_and_active_duplicate(self):
        self.grant_legalization_write()
        draft = self.create_case(case_type=LegalizationCase.CaseType.VISA)
        with self.assertRaises(ValidationError):
            create_legalization_renewal(
                predecessor_uuid=draft.uuid,
                deadline=None,
                notes="",
                actor=self.user,
            )

        nonowned = self.approve_case(responsible=self.admin)
        with self.assertRaises(PermissionDenied):
            create_legalization_renewal(
                predecessor_uuid=nonowned.uuid,
                deadline=None,
                notes="",
                actor=self.user,
            )

        predecessor = self.approve_case(
            case_type=LegalizationCase.CaseType.TEMPORARY_RESIDENCE
        )
        LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.TEMPORARY_RESIDENCE,
            **self.legalization_case_configuration(
                company=self.company_a,
                case_type=LegalizationCase.CaseType.TEMPORARY_RESIDENCE,
            ),
            status=LegalizationCase.Status.DRAFT,
            responsible=self.user,
        )
        with self.assertRaises(ValidationError):
            create_legalization_renewal(
                predecessor_uuid=predecessor.uuid,
                deadline=None,
                notes="",
                actor=self.user,
            )
        self.assertFalse(
            LegalizationRenewalLink.objects.filter(predecessor=predecessor).exists()
        )
        self.assertTrue(domain_integrity_results()[0].ok)

    def test_database_rejects_duplicate_active_procedure(self):
        configuration = self.legalization_case_configuration(company=self.company_a)
        LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            status=LegalizationCase.Status.DRAFT,
            responsible=self.admin,
            **configuration,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            LegalizationCase.objects.create(
                person=self.person_a,
                case_type=LegalizationCase.CaseType.WORK_PERMIT,
                status=LegalizationCase.Status.SUBMITTED,
                responsible=self.admin,
                **configuration,
            )

    def test_manual_historical_link_is_scoped_validated_and_idempotent(self):
        self.grant_legalization_write()
        predecessor = self.approve_case()
        successor = self.create_case()

        first, created = link_existing_legalization_renewal(
            predecessor_uuid=predecessor.uuid,
            successor_uuid=successor.uuid,
            reason="  Verified against archived register  ",
            actor=self.user,
        )
        second, duplicate_created = link_existing_legalization_renewal(
            predecessor_uuid=predecessor.uuid,
            successor_uuid=successor.uuid,
            reason="Verified against archived register",
            actor=self.user,
        )

        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.source, LegalizationRenewalLink.Source.MANUAL)
        self.assertEqual(first.reason, "Verified against archived register")
        self.login()
        detail = self.client.get(successor.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, predecessor.get_absolute_url())
        self.assertContains(detail, first.reason)

    def test_manual_link_rejects_wrong_person_type_order_and_database_self_link(self):
        self.grant_legalization_write()
        predecessor = self.approve_case()
        wrong_type = self.create_case(case_type=LegalizationCase.CaseType.VISA)
        with self.assertRaises(ValidationError):
            link_existing_legalization_renewal(
                predecessor_uuid=predecessor.uuid,
                successor_uuid=wrong_type.uuid,
                reason="Wrong type",
                actor=self.user,
            )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LegalizationRenewalLink.objects.create(
                    predecessor=predecessor,
                    successor=predecessor,
                    source=LegalizationRenewalLink.Source.MANUAL,
                    reason="Invalid self link",
                    actor=self.user,
                )

    def test_out_of_scope_predecessor_and_missing_permission_are_denied(self):
        self.grant_legalization_write()
        predecessor = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_b),
            status=LegalizationCase.Status.APPROVED,
            responsible=self.admin,
            valid_from=date.today() - timedelta(days=300),
            valid_until=date.today() + timedelta(days=65),
        )
        successor = self.create_case()
        with self.assertRaises(Http404):
            link_existing_legalization_renewal(
                predecessor_uuid=predecessor.uuid,
                successor_uuid=successor.uuid,
                reason="Out of scope",
                actor=self.user,
            )

        permission = Permission.objects.get(
            content_type__app_label="hydra_legalization",
            codename="create_legalizationrenewallink",
        )
        self.user.user_permissions.remove(permission)
        self.clear_permissions()
        self.login()
        response = self.client.post(
            reverse("hydra-legalization-start-renewal", args=(successor.uuid,)),
            {"deadline": "", "notes": ""},
        )
        self.assertEqual(response.status_code, 403)

    def test_start_renewal_get_and_post_complete_the_ui_flow(self):
        self.grant_legalization_write()
        predecessor = self.approve_case()
        self.login()
        url = reverse("hydra-legalization-start-renewal", args=(predecessor.uuid,))

        page = self.client.get(url)
        response = self.client.post(
            url,
            {
                "deadline": (date.today() + timedelta(days=45)).isoformat(),
                "notes": "Collect renewal documents",
            },
        )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Start legalization renewal")
        successor = LegalizationRenewalLink.objects.get(
            predecessor=predecessor
        ).successor
        self.assertRedirects(response, successor.get_absolute_url())
        detail = self.client.get(predecessor.get_absolute_url())
        self.assertContains(detail, successor.get_absolute_url())
        self.assertFalse(detail.context["can_start_renewal"])
        self.assertNotContains(detail, "Start renewal")


class LegalizationAuthorityEventTests(HydraLegalizationTestCase):
    def prepare_collecting_case(self):
        case = self.create_case()
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Documents complete",
            actor=self.user,
        )
        return case

    def test_submission_is_atomic_idempotent_and_append_only(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        evidence = self.make_document(title="Submission receipt")
        key = uuid4()

        first, created = self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            document=evidence,
            reference_number="  WRO   2026/99  ",
            idempotency_key=key,
        )
        second, duplicate_created = self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            document=evidence,
            reference_number="WRO 2026/99",
            idempotency_key=key,
        )

        case.refresh_from_db()
        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(case.status, LegalizationCase.Status.SUBMITTED)
        self.assertEqual(case.reference_number, "WRO 2026/99")
        self.assertEqual(case.status_history.count(), 3)
        self.assertEqual(case.authority_events.count(), 1)
        self.assertEqual(first.evidence_sha256, evidence.sha256)
        link = case.document_links.get(document=evidence)
        self.assertEqual(link.role, LegalizationCaseDocument.Role.APPLICATION)
        with self.assertRaises(TypeError):
            first.save()
        with self.assertRaises(TypeError):
            first.delete()
        with self.assertRaises(TypeError):
            LegalizationAuthorityEvent.objects.filter(pk=first.pk).update(
                authority="Changed"
            )

    def test_external_status_cannot_bypass_evidence_through_generic_transition(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()

        with self.assertRaises(ValidationError):
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=LegalizationCase.Status.SUBMITTED,
                reason="No evidence",
                actor=self.user,
            )

        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.COLLECTING_DOCUMENTS)
        self.assertFalse(case.authority_events.exists())

    def test_scoped_post_records_event_and_redirects_to_case(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        evidence = self.make_document(title="Web submission receipt")
        self.login()

        response = self.client.post(
            reverse("hydra-legalization-record-authority-event", args=(case.uuid,)),
            {
                "event_type": LegalizationAuthorityEvent.EventType.SUBMITTED,
                "occurred_on": date.today().isoformat(),
                "authority_config": str(self.legalization_authority.uuid),
                "channel": LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
                "reference_number": "WEB-REF-001",
                "response_deadline": "",
                "valid_from": "",
                "valid_until": "",
                "evidence_document": evidence.pk,
                "details": "Submitted through operator form",
                "idempotency_key": str(uuid4()),
            },
        )

        self.assertRedirects(response, case.get_absolute_url())
        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.SUBMITTED)
        self.assertEqual(case.authority_events.count(), 1)

    def test_request_response_and_approval_follow_closed_graph(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
        )
        response_deadline = date.today() + timedelta(days=14)
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED,
            response_deadline=response_deadline,
        )
        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.ADDITIONAL_INFORMATION)
        self.assertEqual(case.deadline, response_deadline)

        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.INFORMATION_RESPONDED,
        )
        valid_from = date.today()
        valid_until = valid_from + timedelta(days=365)
        decision, _created = self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.APPROVED,
            valid_from=valid_from,
            valid_until=valid_until,
            details="Positive decision",
        )

        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.APPROVED)
        self.assertIsNone(case.deadline)
        self.assertEqual((case.valid_from, case.valid_until), (valid_from, valid_until))
        self.assertEqual(decision.valid_until, valid_until)
        self.assertEqual(case.status_history.count(), 6)

    def test_invalid_event_and_payload_mismatch_roll_back(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        evidence = self.make_document(title="Submission proof")
        key = uuid4()
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            document=evidence,
            idempotency_key=key,
        )

        with self.assertRaises(ValidationError):
            self.record_event(
                case=case,
                event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
                document=evidence,
                idempotency_key=key,
                reference_number="DIFFERENT",
            )
        with self.assertRaises(ValidationError):
            self.record_event(
                case=case,
                event_type=LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED,
                response_deadline=None,
            )

        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.SUBMITTED)
        self.assertEqual(case.authority_events.count(), 1)

    def test_database_rejects_invalid_authority_event_shape(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        evidence = self.make_document(title="Constraint evidence")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LegalizationAuthorityEvent.objects.create(
                    case=case,
                    event_type=LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED,
                    occurred_on=date.today(),
                    authority_config=self.legalization_authority,
                    authority="Lower Silesian Office",
                    authority_snapshot=self.legalization_authority.snapshot(),
                    channel=LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
                    response_deadline=None,
                    evidence_document=evidence,
                    evidence_sha256=evidence.sha256,
                    actor=self.user,
                )

        self.assertFalse(case.authority_events.exists())

    def test_external_facts_cannot_be_silently_edited_after_submission(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            reference_number="LOCKED-REF",
        )
        case.refresh_from_db()
        case.reference_number = "MUTATED-REF"

        with self.assertRaises(ValidationError):
            update_legalization_case(case=case, actor=self.user)

        case.refresh_from_db()
        self.assertEqual(case.reference_number, "LOCKED-REF")

    def test_scope_and_record_permission_are_rechecked_by_service_and_view(self):
        self.grant_legalization_write()
        outside = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_b),
            status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            responsible=self.admin,
        )
        outside_document = self.make_document(
            person=self.person_b,
            candidate=self.candidate_b,
            title="Outside evidence",
        )
        with self.assertRaises(Http404):
            self.record_event(
                case=outside,
                event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
                document=outside_document,
            )

        case = self.prepare_collecting_case()
        permission = Permission.objects.get(
            content_type__app_label="hydra_legalization",
            codename="record_legalizationauthorityevent",
        )
        self.user.user_permissions.remove(permission)
        self.clear_permissions()
        self.login()
        response = self.client.post(
            reverse("hydra-legalization-record-authority-event", args=(case.uuid,)),
            {},
        )
        self.assertEqual(response.status_code, 403)

    def test_only_current_responsible_operator_can_record_authority_event(self):
        self.grant_legalization_write()
        case = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            responsible=self.admin,
        )
        evidence = self.make_document(title="Owner-only evidence")

        with self.assertRaises(PermissionDenied):
            self.record_event(
                case=case,
                event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
                document=evidence,
            )

        self.login()
        response = self.client.get(case.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Record authority event")
        self.assertFalse(case.authority_events.exists())

    def test_deleted_or_unscanned_evidence_is_rejected(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        deleted = self.make_document(title="Deleted evidence")
        deleted.deleted_at = timezone.now()
        deleted.save(update_fields=("deleted_at",))
        unscanned = self.make_document(title="Unscanned evidence")
        unscanned.scanned_at = None
        unscanned.save(update_fields=("scanned_at",))

        for document in (deleted, unscanned):
            with self.subTest(document=document.title):
                with self.assertRaises(ValidationError):
                    self.record_event(
                        case=case,
                        event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
                        document=document,
                    )
        self.assertFalse(case.authority_events.exists())

    def test_authority_fact_remains_visible_when_evidence_becomes_unavailable(self):
        self.grant_legalization_write()
        case = self.prepare_collecting_case()
        evidence = self.make_document(title="Retained audit evidence")
        self.record_event(
            case=case,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            document=evidence,
            details="Submission audit fact",
        )
        evidence.deleted_at = timezone.now()
        evidence.save(update_fields=("deleted_at",))
        self.login()

        response = self.client.get(case.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submission audit fact")
        self.assertContains(response, "Evidence unavailable")
        self.assertNotContains(
            response,
            reverse("hydra-private-document-download", args=(evidence.uuid,)),
        )


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
