from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from notifications.models import Notification

from hydra_coordination.models import (
    OrganizationAccessEvent,
    PersonAssignment,
    ScopeGrant,
    TerminationMode,
)
from hydra_coordination.selectors import (
    active_grants_for_user,
    scope_grants_for_management,
)
from hydra_coordination.services import (
    end_person_assignment,
    end_scope_grant,
    save_scope_grant,
)
from hydra_coordination.tests.test_scope import OrganizationScopeTestCase
from hydra_coordination.tests.test_team_assignment import (
    EmployeeTeamAssignmentTestCase,
)


class ScopeAccessTerminationTests(OrganizationScopeTestCase):
    def setUp(self):
        super().setUp()
        self.recipient = User.objects.create_user(
            username=f"scope-recipient-{self._testMethodName}",
            password="test-password",
            is_new_employee=False,
        )

    def grant_management_permissions(self):
        self.grant_permissions(
            ("hydra_coordination", "view_scopegrant"),
            ("hydra_coordination", "change_scopegrant"),
            ("hydra_coordination", "view_location"),
        )

    def recipient_grant(self, *, team=None, valid_until=None):
        return save_scope_grant(
            grant=ScopeGrant(
                user=self.recipient,
                team=team or self.team_a,
                valid_until=valid_until,
            ),
            actor=self.admin,
        )

    def test_immediate_revoke_is_audited_notified_and_idempotent(self):
        grant = self.recipient_grant()

        with self.captureOnCommitCallbacks(execute=True):
            result = end_scope_grant(
                grant_id=grant.pk,
                action="immediate",
                last_day=None,
                reason="Access no longer required",
                actor=self.admin,
            )

        self.assertEqual(result.pk, grant.pk)
        grant.refresh_from_db()
        self.assertFalse(grant.is_active)
        self.assertEqual(grant.termination_mode, TerminationMode.IMMEDIATE)
        self.assertEqual(grant.termination_reason, "Access no longer required")
        self.assertEqual(grant.termination_recorded_by, self.admin)
        self.assertFalse(active_grants_for_user(user=self.recipient).exists())
        event = OrganizationAccessEvent.objects.get()
        self.assertEqual(event.action, OrganizationAccessEvent.Action.SCOPE_REVOKED)
        self.assertEqual(
            event.notification_status,
            OrganizationAccessEvent.NotificationStatus.SENT,
        )
        self.assertEqual(event.notification.recipient, self.recipient)
        self.assertEqual(Notification.objects.filter(recipient=self.recipient).count(), 1)

        with self.captureOnCommitCallbacks(execute=True):
            repeated = end_scope_grant(
                grant_id=grant.pk,
                action="immediate",
                last_day=None,
                reason="Access no longer required",
                actor=self.admin,
            )
        self.assertEqual(repeated.pk, grant.pk)
        self.assertEqual(OrganizationAccessEvent.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.recipient).count(), 1)

    def test_scheduled_end_is_inclusive_and_cannot_extend_existing_access(self):
        last_day = timezone.localdate() + timedelta(days=2)
        grant = self.recipient_grant(valid_until=last_day)

        with self.captureOnCommitCallbacks(execute=True):
            end_scope_grant(
                grant_id=grant.pk,
                action="schedule",
                last_day=last_day,
                reason="Contract completion",
                actor=self.admin,
            )

        grant.refresh_from_db()
        self.assertEqual(grant.valid_until, last_day)
        self.assertEqual(grant.termination_mode, TerminationMode.SCHEDULED)
        self.assertTrue(active_grants_for_user(user=self.recipient, day=last_day).exists())
        self.assertFalse(
            active_grants_for_user(
                user=self.recipient, day=last_day + timedelta(days=1)
            ).exists()
        )
        with self.assertRaises(ValidationError):
            end_scope_grant(
                grant_id=grant.pk,
                action="schedule",
                last_day=last_day + timedelta(days=1),
                reason="Improper extension",
                actor=self.admin,
            )

    def test_manager_can_end_contained_grant_but_not_outside_scope(self):
        self.grant_management_permissions()
        self.grant_scope(company=self.company_a)
        inside = self.recipient_grant(team=self.team_a)
        outside = self.recipient_grant(team=self.team_b)

        self.assertTrue(
            scope_grants_for_management(user=self.user).filter(pk=inside.pk).exists()
        )
        self.assertFalse(
            scope_grants_for_management(user=self.user).filter(pk=outside.pk).exists()
        )
        with self.captureOnCommitCallbacks(execute=True):
            end_scope_grant(
                grant_id=inside.pk,
                action="immediate",
                last_day=None,
                reason="Manager decision",
                actor=self.user,
            )
        with self.assertRaises(PermissionDenied):
            end_scope_grant(
                grant_id=outside.pk,
                action="immediate",
                last_day=None,
                reason="Scope probe",
                actor=self.user,
            )

    def test_end_service_requires_explicit_change_permission(self):
        grant = self.recipient_grant()
        self.grant_permissions(("hydra_coordination", "view_scopegrant"))
        self.grant_scope(company=self.company_a)

        with self.assertRaises(PermissionDenied):
            end_scope_grant(
                grant_id=grant.pk,
                action="immediate",
                last_day=None,
                reason="Denied",
                actor=self.user,
            )

    def test_event_facts_are_append_only(self):
        grant = self.recipient_grant()
        with self.captureOnCommitCallbacks(execute=True):
            end_scope_grant(
                grant_id=grant.pk,
                action="immediate",
                last_day=None,
                reason="Security response",
                actor=self.admin,
            )
        event = OrganizationAccessEvent.objects.get()
        event.reason = "Changed"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            OrganizationAccessEvent.objects.filter(pk=event.pk).update(reason="Changed")
        with self.assertRaises(TypeError):
            event.delete()
        with self.assertRaises(TypeError):
            OrganizationAccessEvent.objects.filter(pk=event.pk).delete()

    def test_failed_notification_is_durable_and_retryable(self):
        grant = self.recipient_grant()
        with patch(
            "hydra_coordination.services.send_hydra_notification",
            side_effect=RuntimeError("notification backend unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                end_scope_grant(
                    grant_id=grant.pk,
                    action="immediate",
                    last_day=None,
                    reason="Urgent security revocation",
                    actor=self.admin,
                )

        grant.refresh_from_db()
        self.assertFalse(grant.is_active)
        event = OrganizationAccessEvent.objects.get()
        self.assertEqual(
            event.notification_status,
            OrganizationAccessEvent.NotificationStatus.FAILED,
        )
        self.assertEqual(event.notification_attempts, 1)
        self.assertEqual(event.notification_error_code, "RuntimeError")

        call_command("dispatch_organization_notifications", stdout=StringIO())
        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            OrganizationAccessEvent.NotificationStatus.SENT,
        )
        self.assertEqual(event.notification_attempts, 2)

    @override_settings(HYDRA_NOTIFICATION_MAX_ATTEMPTS=1)
    def test_operator_can_retry_one_event_after_automatic_attempts_are_exhausted(self):
        grant = self.recipient_grant()
        with patch(
            "hydra_coordination.services.send_hydra_notification",
            side_effect=RuntimeError("notification backend unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                end_scope_grant(
                    grant_id=grant.pk,
                    action="immediate",
                    last_day=None,
                    reason="Urgent security revocation",
                    actor=self.admin,
                )

        event = OrganizationAccessEvent.objects.get()
        call_command("dispatch_organization_notifications", stdout=StringIO())
        event.refresh_from_db()
        self.assertEqual(event.notification_attempts, 1)

        call_command(
            "dispatch_organization_notifications",
            "--event-uuid",
            str(event.uuid),
            stdout=StringIO(),
        )

        event.refresh_from_db()
        self.assertEqual(
            event.notification_status,
            OrganizationAccessEvent.NotificationStatus.SENT,
        )
        self.assertEqual(event.notification_attempts, 2)
        self.assertEqual(OrganizationAccessEvent.objects.count(), 1)

    def test_management_view_is_scoped_and_executes_service(self):
        self.grant_management_permissions()
        self.grant_scope(company=self.company_a)
        inside = self.recipient_grant(team=self.team_a)
        outside = self.recipient_grant(team=self.team_b)
        self.login_with_all_companies_selected()

        page = self.client.get(reverse("hydra-organization"))
        form = self.client.get(reverse("hydra-scope-grant-end", args=(inside.pk,)))
        hidden = self.client.get(reverse("hydra-scope-grant-end", args=(outside.pk,)))
        submitted = self.client.post(
            reverse("hydra-scope-grant-end", args=(inside.pk,)),
            {"action": "immediate", "reason": "Access review"},
        )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, self.recipient.username)
        self.assertEqual(form.status_code, 200)
        self.assertEqual(hidden.status_code, 404)
        self.assertRedirects(submitted, reverse("hydra-organization"))
        inside.refresh_from_db()
        self.assertFalse(inside.is_active)


class AssignmentAccessTerminationTests(EmployeeTeamAssignmentTestCase):
    def grant_end_permissions(self):
        self.grant_assignment_permissions()
        self.operator.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="hydra_coordination",
                codename="change_personassignment",
            )
        )
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.operator.__dict__.pop(attribute, None)

    def test_immediate_assignment_end_preserves_history_and_notifies_employee(self):
        self.grant_end_permissions()

        with self.captureOnCommitCallbacks(execute=True):
            end_person_assignment(
                assignment_id=self.initial_assignment.pk,
                action="immediate",
                last_day=None,
                reason="Employment assignment closed",
                actor=self.operator,
            )

        assignment = PersonAssignment.objects.get(pk=self.initial_assignment.pk)
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.termination_mode, TerminationMode.IMMEDIATE)
        self.assertEqual(assignment.termination_recorded_by, self.operator)
        event = OrganizationAccessEvent.objects.get()
        self.assertEqual(
            event.action, OrganizationAccessEvent.Action.ASSIGNMENT_ENDED
        )
        self.assertEqual(event.subject_user, self.employee.employee_user_id)
        self.assertEqual(
            event.notification_status,
            OrganizationAccessEvent.NotificationStatus.SENT,
        )
        work_info = self.employee.employee_work_info
        self.assertEqual(work_info.company_id, self.company_a)
        self.assertEqual(work_info.department_id, self.department_a)

    def test_scheduled_assignment_end_is_inclusive(self):
        self.grant_end_permissions()
        last_day = timezone.localdate() + timedelta(days=2)

        with self.captureOnCommitCallbacks(execute=True):
            end_person_assignment(
                assignment_id=self.initial_assignment.pk,
                action="schedule",
                last_day=last_day,
                reason="Planned rotation end",
                actor=self.operator,
            )

        assignment = PersonAssignment.objects.get(pk=self.initial_assignment.pk)
        self.assertTrue(assignment.is_current(day=last_day))
        self.assertFalse(assignment.is_current(day=last_day + timedelta(days=1)))
        self.assertEqual(assignment.termination_mode, TerminationMode.SCHEDULED)

    def test_assignment_end_view_requires_change_permission(self):
        self.grant_assignment_permissions()
        self.client.force_login(self.operator)

        response = self.client.get(
            reverse("hydra-person-assignment-end", args=(self.initial_assignment.pk,))
        )

        self.assertEqual(response.status_code, 403)

    def test_assignment_end_view_executes_scoped_service(self):
        self.grant_end_permissions()
        self.client.force_login(self.operator)

        form = self.client.get(
            reverse("hydra-person-assignment-end", args=(self.initial_assignment.pk,))
        )
        submitted = self.client.post(
            reverse("hydra-person-assignment-end", args=(self.initial_assignment.pk,)),
            {"action": "immediate", "reason": "Operational end"},
        )

        self.assertEqual(form.status_code, 200)
        self.assertEqual(submitted.status_code, 302)
        assignment = PersonAssignment.objects.get(pk=self.initial_assignment.pk)
        self.assertFalse(assignment.is_active)
