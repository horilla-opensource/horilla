from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from employee.models import Employee
from hydra_coordination.models import ScopeGrant
from hydra_legalization.models import (
    LegalizationCase,
    LegalizationCaseDelegation,
    LegalizationAuthorityEvent,
    LegalizationWorkEvent,
)
from hydra_legalization.services import (
    record_legalization_authority_event,
    transition_legalization_case,
)
from hydra_legalization.tests.test_legalization import HydraLegalizationTestCase
from hydra_legalization.workload import (
    create_legalization_delegation,
    dispatch_legalization_work_event,
    reassign_legalization_case,
    revoke_legalization_delegation,
)
from hydra_ops.readiness import domain_integrity_results


OPERATIONAL_PERMISSIONS = (
    ("hydra_legalization", "view_legalizationcase"),
    ("hydra_legalization", "add_legalizationcase"),
    ("hydra_legalization", "change_legalizationcase"),
    ("hydra_legalization", "assign_legalizationcase"),
    ("hydra_legalization", "transition_legalizationcase"),
    ("hydra_legalization", "link_privatedocument"),
    ("hydra_legalization", "view_legalizationauthorityevent"),
    ("hydra_legalization", "record_legalizationauthorityevent"),
    ("hydra_legalization", "view_legalizationproceduretype"),
    ("hydra_legalization", "view_legalizationauthority"),
    ("hydra_legalization", "view_legalizationrenewallink"),
    ("hydra_legalization", "create_legalizationrenewallink"),
    ("hydra_legalization", "view_legalizationcasedelegation"),
    ("hydra_legalization", "view_legalizationworkevent"),
    ("hydra_people", "view_person"),
    ("hydra_documents", "view_privatedocument"),
    ("recruitment", "view_candidate"),
)


class LegalizationWorkloadTests(HydraLegalizationTestCase):
    def grant_continuity(self):
        self.grant_legalization_write()
        self.grant(
            ("hydra_legalization", "view_legalizationworkload"),
            ("hydra_legalization", "view_legalizationcasedelegation"),
            ("hydra_legalization", "manage_legalizationdelegation"),
            ("hydra_legalization", "view_legalizationworkevent"),
        )

    def make_operator(self, username="legalization-deputy", *, scoped=True):
        operator = User.objects.create_user(
            username=username,
            password="test-password",
            is_new_employee=False,
        )
        employee = Employee.objects.create(
            employee_user_id=operator,
            employee_first_name="Legalization",
            employee_last_name=username,
            email=f"{username}@example.test",
            phone="",
        )
        employee.employee_work_info.company_id = self.company_a
        employee.employee_work_info.save(update_fields=("company_id",))
        operator.user_permissions.add(
            *[
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
                for app_label, codename in OPERATIONAL_PERMISSIONS
            ]
        )
        if scoped:
            ScopeGrant.objects.create(user=operator, team=self.team_a)
        return operator

    def create_delegation(self, *, case, deputy, **overrides):
        values = {
            "case_uuid": case.uuid,
            "deputy": deputy,
            "valid_from": timezone.localdate(),
            "valid_until": timezone.localdate() + timedelta(days=13),
            "reason": "Planned owner absence",
            "actor": self.user,
        }
        values.update(overrides)
        return create_legalization_delegation(**values)

    def test_case_creation_records_append_only_responsibility_baseline(self):
        self.grant_continuity()
        case = self.create_case()

        event = case.work_events.get()
        self.assertEqual(
            event.action,
            LegalizationWorkEvent.Action.RESPONSIBILITY_ASSIGNED,
        )
        self.assertEqual(event.to_user_id, self.user.pk)
        self.assertEqual(event.actor_id, self.user.pk)
        self.assertEqual(
            event.notification_status,
            LegalizationWorkEvent.NotificationStatus.NOT_APPLICABLE,
        )
        event.reason = "rewritten"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            LegalizationWorkEvent.objects.filter(pk=event.pk).update(
                reason="rewritten"
            )
        with self.assertRaises(TypeError):
            event.delete()

    def test_scoped_deputy_can_operate_only_during_explicit_window(self):
        self.grant_continuity()
        case = self.create_case()
        deputy = self.make_operator()
        delegation, created = self.create_delegation(case=case, deputy=deputy)

        self.assertTrue(created)
        self.assertTrue(delegation.is_current())
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Deputy continued the case",
            actor=deputy,
        )
        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.COLLECTING_DOCUMENTS)
        self.assertEqual(case.status_history.first().actor_id, deputy.pk)

        revoke_legalization_delegation(
            delegation_uuid=delegation.uuid,
            reason="Owner returned",
            actor=self.user,
        )
        with self.assertRaises(PermissionDenied):
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=LegalizationCase.Status.CLOSED,
                reason="No longer authorized",
                actor=deputy,
            )

    def test_current_deputy_can_record_evidence_backed_authority_fact(self):
        self.grant_continuity()
        case = self.create_case()
        deputy = self.make_operator()
        self.create_delegation(case=case, deputy=deputy)
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="Documents complete",
            actor=deputy,
        )
        evidence = self.make_document(title="Deputy submission evidence")

        event, created = record_legalization_authority_event(
            case_uuid=case.uuid,
            event_type=LegalizationAuthorityEvent.EventType.SUBMITTED,
            occurred_on=timezone.localdate(),
            authority_uuid=self.legalization_authority.uuid,
            channel=LegalizationAuthorityEvent.Channel.ONLINE_PORTAL,
            reference_number="DEPUTY-SUBMISSION-1",
            response_deadline=None,
            valid_from=None,
            valid_until=None,
            evidence_document_uuid=evidence.uuid,
            details="Submitted during planned cover",
            idempotency_key=uuid4(),
            actor=deputy,
        )

        self.assertTrue(created)
        self.assertEqual(event.actor_id, deputy.pk)
        case.refresh_from_db()
        self.assertEqual(case.status, LegalizationCase.Status.SUBMITTED)

    def test_deputy_requires_full_operator_permissions_and_person_scope(self):
        self.grant_continuity()
        case = self.create_case()
        outside = self.make_operator(username="outside-deputy", scoped=False)
        incomplete = User.objects.create_user(
            username="incomplete-deputy",
            password="test-password",
            is_new_employee=False,
        )
        incomplete.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="hydra_legalization",
                codename="view_legalizationcase",
            ),
            Permission.objects.get(
                content_type__app_label="hydra_people",
                codename="view_person",
            ),
        )
        ScopeGrant.objects.create(user=incomplete, team=self.team_a)

        with self.assertRaises(ValidationError):
            self.create_delegation(case=case, deputy=outside)
        with self.assertRaises(ValidationError):
            self.create_delegation(case=case, deputy=incomplete)
        self.assertFalse(case.delegations.exists())

    def test_overlap_and_unbounded_windows_are_rejected_and_retry_is_idempotent(self):
        self.grant_continuity()
        case = self.create_case()
        first_deputy = self.make_operator("first-deputy")
        second_deputy = self.make_operator("second-deputy")
        first, created = self.create_delegation(case=case, deputy=first_deputy)
        retry, retry_created = self.create_delegation(case=case, deputy=first_deputy)

        self.assertTrue(created)
        self.assertFalse(retry_created)
        self.assertEqual(first.pk, retry.pk)
        with self.assertRaises(ValidationError):
            self.create_delegation(
                case=case,
                deputy=second_deputy,
                valid_from=timezone.localdate() + timedelta(days=10),
                valid_until=timezone.localdate() + timedelta(days=20),
            )
        with self.assertRaises(ValidationError):
            self.create_delegation(
                case=case,
                deputy=second_deputy,
                valid_from=timezone.localdate() + timedelta(days=20),
                valid_until=timezone.localdate() + timedelta(days=110),
            )
        self.assertEqual(case.delegations.count(), 1)

    def test_database_constraints_reject_invalid_delegation_shape(self):
        self.grant_continuity()
        case = self.create_case()
        deputy = self.make_operator()

        with self.assertRaises(IntegrityError), transaction.atomic():
            LegalizationCaseDelegation.objects.create(
                case=case,
                principal=self.user,
                deputy=deputy,
                valid_from=timezone.localdate(),
                valid_until=timezone.localdate() + timedelta(days=90),
                reason="Too long",
                created_by=self.user,
                modified_by=self.user,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            LegalizationCaseDelegation.objects.create(
                case=case,
                principal=self.user,
                deputy=self.user,
                valid_from=timezone.localdate(),
                valid_until=timezone.localdate() + timedelta(days=1),
                reason="Same user",
                created_by=self.user,
                modified_by=self.user,
            )

    def test_readiness_detects_overlap_stale_principal_and_missing_baseline(self):
        self.grant_continuity()
        case = self.create_case()
        first_deputy = self.make_operator("readiness-first")
        second_deputy = self.make_operator("readiness-second")
        self.create_delegation(case=case, deputy=first_deputy)
        LegalizationCaseDelegation.objects.create(
            case=case,
            principal=self.user,
            deputy=second_deputy,
            valid_from=timezone.localdate() + timedelta(days=5),
            valid_until=timezone.localdate() + timedelta(days=15),
            reason="Injected legacy overlap",
            created_by=self.admin,
            modified_by=self.admin,
        )
        LegalizationCase.objects.filter(pk=case.pk).update(responsible=self.admin)
        LegalizationCase.objects.create(
            person=self.person_c,
            case_type=LegalizationCase.CaseType.OTHER,
            **self.legalization_case_configuration(
                company=self.company_a, case_type=LegalizationCase.CaseType.OTHER
            ),
            responsible=self.admin,
        )

        results = {result.name: result for result in domain_integrity_results()}

        self.assertFalse(results["legalization_delegation_windows"].ok)
        self.assertFalse(results["legalization_delegation_principals"].ok)
        self.assertFalse(results["legalization_responsibility_baseline"].ok)

    def test_transfer_revokes_delegation_and_old_owner_loses_write_authority(self):
        self.grant_continuity()
        case = self.create_case()
        replacement = self.make_operator("replacement-owner")
        delegation, _ = self.create_delegation(case=case, deputy=replacement)

        transferred, changed = reassign_legalization_case(
            case_uuid=case.uuid,
            new_responsible=replacement,
            reason="Permanent workload transfer",
            actor=self.user,
        )

        self.assertTrue(changed)
        self.assertEqual(transferred.responsible_id, replacement.pk)
        delegation.refresh_from_db()
        self.assertFalse(delegation.is_active)
        self.assertIn("Responsibility transferred", delegation.revocation_reason)
        self.assertEqual(
            case.work_events.filter(
                action=LegalizationWorkEvent.Action.RESPONSIBILITY_TRANSFERRED
            ).count(),
            1,
        )
        with self.assertRaises(PermissionDenied):
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
                reason="Old owner attempt",
                actor=self.user,
            )
        transition_legalization_case(
            case_uuid=case.uuid,
            target_status=LegalizationCase.Status.COLLECTING_DOCUMENTS,
            reason="New owner continued work",
            actor=replacement,
        )

    def test_notification_delivery_is_durable_minimal_and_rechecks_authority(self):
        self.grant_continuity()
        case = self.create_case()
        deputy = self.make_operator()
        delegation, _ = self.create_delegation(case=case, deputy=deputy)
        event = delegation.work_events.get(
            action=LegalizationWorkEvent.Action.DELEGATION_CREATED
        )

        with patch(
            "hydra_legalization.workload.send_hydra_notification",
            side_effect=RuntimeError("sensitive backend details"),
        ):
            self.assertFalse(dispatch_legalization_work_event(event.pk))
        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            LegalizationWorkEvent.NotificationStatus.FAILED,
        )
        self.assertEqual(event.notification_error_code, "RuntimeError")
        self.assertNotIn("sensitive", event.notification_error_code)

        revoke_legalization_delegation(
            delegation_uuid=delegation.uuid,
            reason="Plan changed",
            actor=self.user,
        )
        self.assertTrue(dispatch_legalization_work_event(event.pk))
        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            LegalizationWorkEvent.NotificationStatus.NOT_APPLICABLE,
        )
        self.assertIsNone(event.notification_id)

    def test_workload_queue_is_permissioned_scoped_and_filterable(self):
        self.grant_continuity()
        due_case = self.create_case(deadline=timezone.localdate() + timedelta(days=5))
        other = self.create_case(
            person=self.person_c,
            case_type=LegalizationCase.CaseType.VISA,
            deadline=None,
        )
        hidden = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.OTHER,
            **self.legalization_case_configuration(
                company=self.company_b, case_type=LegalizationCase.CaseType.OTHER
            ),
            responsible=self.admin,
            deadline=timezone.localdate() - timedelta(days=2),
        )
        self.login()

        response = self.client.get(
            reverse("hydra-legalization-workload"),
            {"attention": "due_14"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, due_case.person.passport_name)
        self.assertNotContains(response, other.person.passport_name)
        self.assertNotContains(response, hidden.person.passport_name)
        self.assertContains(response, "Legalization workload")

    def test_continuity_endpoints_reject_nonowner_and_cross_case_identifier(self):
        self.grant_continuity()
        case = self.create_case()
        deputy = self.make_operator()
        delegation, _ = self.create_delegation(case=case, deputy=deputy)
        other_case = self.create_case(
            person=self.person_c,
            case_type=LegalizationCase.CaseType.VISA,
        )
        self.login()

        cross_case = self.client.post(
            reverse(
                "hydra-legalization-revoke-delegation",
                args=(other_case.uuid, delegation.uuid),
            ),
            {"reason": "Wrong case"},
        )
        self.assertEqual(cross_case.status_code, 404)

        self.client.force_login(deputy)
        deputy.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="hydra_legalization",
                codename="manage_legalizationdelegation",
            )
        )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            deputy.__dict__.pop(cache_name, None)
        with self.assertRaises(PermissionDenied):
            create_legalization_delegation(
                case_uuid=case.uuid,
                deputy=self.user,
                valid_from=timezone.localdate() + timedelta(days=20),
                valid_until=timezone.localdate() + timedelta(days=22),
                reason="Deputy cannot appoint another deputy",
                actor=deputy,
            )
        nonowner = self.client.post(
            reverse("hydra-legalization-delegate", args=(case.uuid,)),
            {
                "deputy": self.user.pk,
                "valid_from": timezone.localdate().isoformat(),
                "valid_until": (timezone.localdate() + timedelta(days=2)).isoformat(),
                "reason": "Unauthorized",
            },
        )
        self.assertEqual(nonowner.status_code, 403)
