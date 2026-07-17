from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from employee.models import Employee
from hydra_coordination.models import ScopeGrant
from hydra_legalization.models import LegalizationCase
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from hydra_people.timeline import person_timeline_for_user
from hydra_ops.readiness import domain_integrity_results
from hydra_tasks.models import (
    HydraTask,
    HydraTaskEvent,
    HydraTaskNotificationDelivery,
    TaskTargetKind,
)
from hydra_tasks.selectors import tasks_for_user
from hydra_tasks.services import (
    create_task,
    dispatch_task_notification,
    reassign_task,
    transition_task,
    update_task,
)


TASK_PERMISSIONS = (
    ("hydra_people", "view_person"),
    ("hydra_tasks", "view_hydratask"),
    ("hydra_tasks", "view_hydrataskevent"),
    ("hydra_tasks", "add_hydratask"),
    ("hydra_tasks", "change_hydratask"),
    ("hydra_tasks", "assign_hydratask"),
    ("hydra_tasks", "transition_hydratask"),
    ("hydra_tasks", "reopen_hydratask"),
)


class HydraTaskTests(HydraRecruitmentTestCase):
    def setUp(self):
        super().setUp()
        self.assignee = User.objects.create_user(
            username="task-assignee-a",
            email="task-assignee-a@example.test",
            password="test-password",
            is_new_employee=False,
        )
        employee = Employee.objects.create(
            employee_user_id=self.assignee,
            employee_first_name="Task",
            employee_last_name="Assignee A",
            email="task-assignee-a@example.test",
            phone="+48222222222",
        )
        employee.employee_work_info.company_id = self.company_a
        employee.employee_work_info.save()
        self.assignee_scope = ScopeGrant.objects.create(
            user=self.assignee,
            team=self.team_a,
        )

        self.outsider = User.objects.create_user(
            username="task-assignee-b",
            email="task-assignee-b@example.test",
            password="test-password",
            is_new_employee=False,
        )
        outsider_employee = Employee.objects.create(
            employee_user_id=self.outsider,
            employee_first_name="Task",
            employee_last_name="Assignee B",
            email="task-assignee-b@example.test",
            phone="+48333333333",
        )
        outsider_employee.employee_work_info.company_id = self.company_b
        outsider_employee.employee_work_info.save()
        ScopeGrant.objects.create(user=self.outsider, team=self.team_b)

        self.grant_user(self.user, *TASK_PERMISSIONS)
        self.grant_user(self.assignee, *TASK_PERMISSIONS)
        self.grant_user(self.outsider, *TASK_PERMISSIONS)

    @staticmethod
    def grant_user(user, *permissions):
        for app_label, codename in permissions:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            user.__dict__.pop(cache_name, None)

    def create(self, **overrides):
        data = {
            "actor": self.user,
            "person_uuid": self.person_a.uuid,
            "company": self.company_a,
            "assignee": self.assignee,
            "title": "Prepare arrival checklist",
            "description": "Verify the operational checklist.",
            "priority": HydraTask.Priority.HIGH,
            "due_at": timezone.now() + timedelta(days=2),
            "target_reference": f"person:{self.person_a.uuid}",
            "request_key": uuid4(),
        }
        data.update(overrides)
        return create_task(**data)

    def test_create_is_scoped_idempotent_audited_and_notified_without_pii(self):
        request_key = uuid4()
        due_at = timezone.now() + timedelta(days=2)
        with self.captureOnCommitCallbacks(execute=True):
            task = self.create(
                request_key=request_key,
                title="Passport follow-up for a private case",
                due_at=due_at,
            )
        same = self.create(
            request_key=request_key,
            title="Passport follow-up for a private case",
            due_at=due_at,
        )

        self.assertEqual(task.pk, same.pk)
        self.assertEqual(HydraTask._base_manager.count(), 1)
        event = HydraTaskEvent.objects.get(task=task)
        self.assertEqual(event.action, HydraTaskEvent.Action.CREATED)
        self.assertEqual(event.sequence, 1)
        delivery = HydraTaskNotificationDelivery.objects.get(event=event)
        self.assertEqual(delivery.status, delivery.Status.SENT)
        self.assertEqual(delivery.notification.recipient, self.assignee)
        rendered = f"{delivery.notification.verb} {delivery.notification.data}"
        self.assertNotIn("Passport", rendered)
        self.assertNotIn(self.person_a.hydra_id, rendered)
        self.assertEqual(
            delivery.notification.data["redirect"],
            reverse("hydra-notification-center"),
        )

    def test_invalid_input_and_target_tampering_write_nothing(self):
        with self.assertRaises(ValidationError):
            self.create(due_at=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(ValidationError):
            self.create(target_reference=f"person:{self.person_b.uuid}")
        with self.assertRaises(ValidationError):
            self.create(title=" ")

        self.assertFalse(HydraTask._base_manager.exists())
        self.assertFalse(HydraTaskEvent.objects.exists())

    def test_approved_domain_target_is_resolved_and_cross_scope_target_is_denied(self):
        self.grant_user(self.user, ("hydra_legalization", "view_legalizationcase"))
        visible_case = LegalizationCase.objects.create(
            person=self.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            **self.legalization_case_configuration(company=self.company_a),
            responsible=self.admin,
            reference_number="TASK-LINK-A",
        )
        hidden_case = LegalizationCase.objects.create(
            person=self.person_b,
            case_type=LegalizationCase.CaseType.VISA,
            **self.legalization_case_configuration(
                company=self.company_b,
                case_type=LegalizationCase.CaseType.VISA,
            ),
            responsible=self.admin,
            reference_number="TASK-LINK-B",
        )

        task = self.create(
            target_reference=f"legalization_case:{visible_case.uuid}"
        )

        self.assertEqual(task.target_kind, TaskTargetKind.LEGALIZATION_CASE)
        self.assertEqual(task.target_uuid, visible_case.uuid)
        self.assertEqual(task.target_label, "Legalization / TASK-LINK-A")
        with self.assertRaises(ValidationError):
            self.create(target_reference=f"legalization_case:{hidden_case.uuid}")

    def test_permission_and_cross_scope_creation_are_denied(self):
        unprivileged = User.objects.create_user(
            username="task-unprivileged",
            password="test-password",
            is_new_employee=False,
        )
        with self.assertRaises(PermissionDenied):
            self.create(actor=unprivileged)
        with self.assertRaises(Http404):
            self.create(person_uuid=self.person_b.uuid)
        with self.assertRaises(ValidationError):
            self.create(assignee=self.outsider)

    def test_visibility_requires_involvement_or_view_all_inside_scope(self):
        task = self.create()
        peer = User.objects.create_user(
            username="task-peer-a",
            password="test-password",
            is_new_employee=False,
        )
        ScopeGrant.objects.create(user=peer, team=self.team_a)
        self.grant_user(peer, ("hydra_people", "view_person"), ("hydra_tasks", "view_hydratask"))

        self.assertTrue(tasks_for_user(user=self.user).filter(pk=task.pk).exists())
        self.assertTrue(tasks_for_user(user=self.assignee).filter(pk=task.pk).exists())
        self.assertFalse(tasks_for_user(user=peer).filter(pk=task.pk).exists())

        self.grant_user(peer, ("hydra_tasks", "view_all_hydratask"))
        self.assertTrue(tasks_for_user(user=peer).filter(pk=task.pk).exists())

    def test_update_reassign_transition_and_reopen_preserve_sequence(self):
        task = self.create()
        task = update_task(
            actor=self.user,
            task_uuid=task.uuid,
            expected_version=task.version,
            title="Prepare final arrival checklist",
            description=task.description,
            priority=HydraTask.Priority.URGENT,
            due_at=task.due_at + timedelta(days=1),
        )
        task = reassign_task(
            actor=self.user,
            task_uuid=task.uuid,
            expected_version=task.version,
            assignee=self.user,
            reason="Coordinator accepts ownership",
        )
        task = transition_task(
            actor=self.user,
            task_uuid=task.uuid,
            expected_version=task.version,
            to_status=HydraTask.Status.IN_PROGRESS,
        )
        task = transition_task(
            actor=self.user,
            task_uuid=task.uuid,
            expected_version=task.version,
            to_status=HydraTask.Status.COMPLETED,
            reason="Checklist verified and recorded",
        )
        task = transition_task(
            actor=self.user,
            task_uuid=task.uuid,
            expected_version=task.version,
            to_status=HydraTask.Status.OPEN,
            reason="New verified action is required",
        )

        task.refresh_from_db()
        self.assertEqual(task.status, HydraTask.Status.OPEN)
        self.assertIsNone(task.completed_at)
        self.assertEqual(task.resolution_reason, "")
        self.assertEqual(task.version, 6)
        self.assertQuerySetEqual(
            task.events.values_list("sequence", flat=True),
            [1, 2, 3, 4, 5, 6],
            transform=lambda value: value,
        )

    def test_stale_and_invalid_transitions_are_atomic(self):
        task = self.create()
        with self.assertRaises(ValidationError):
            transition_task(
                actor=self.assignee,
                task_uuid=task.uuid,
                expected_version=task.version + 1,
                to_status=HydraTask.Status.IN_PROGRESS,
            )
        with self.assertRaises(ValidationError):
            transition_task(
                actor=self.assignee,
                task_uuid=task.uuid,
                expected_version=task.version,
                to_status=HydraTask.Status.COMPLETED,
                reason="",
            )
        with self.assertRaises(ValidationError):
            transition_task(
                actor=self.assignee,
                task_uuid=task.uuid,
                expected_version=task.version,
                to_status=HydraTask.Status.OPEN,
            )

        task.refresh_from_db()
        self.assertEqual(task.status, HydraTask.Status.OPEN)
        self.assertEqual(task.version, 1)
        self.assertEqual(task.events.count(), 1)

    def test_direct_mutation_hard_delete_and_event_rewrite_are_blocked(self):
        task = self.create()
        task.title = "Bypass"
        with self.assertRaises(TypeError):
            task.save()
        with self.assertRaises(TypeError):
            HydraTask.objects.filter(pk=task.pk).update(title="Bypass")
        task.refresh_from_db()
        task.is_active = False
        with self.assertRaises(TypeError):
            task.save()
        with self.assertRaises(TypeError):
            task.delete()
        event = task.events.get()
        event.reason = "rewrite"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            HydraTaskEvent.objects.filter(pk=event.pk).delete()
        delivery = HydraTaskNotificationDelivery.objects.get(task=task)
        delivery.recipient = self.outsider
        with self.assertRaises(TypeError):
            delivery.save()
        with self.assertRaises(TypeError):
            HydraTaskNotificationDelivery.objects.filter(pk=delivery.pk).update(
                recipient=self.outsider
            )
        with self.assertRaises(TypeError):
            delivery.delete()
        with self.assertRaises(TypeError):
            HydraTaskNotificationDelivery.objects.filter(pk=delivery.pk).delete()

    def test_delivery_rechecks_current_scope_and_becomes_not_applicable(self):
        task = self.create()
        delivery = HydraTaskNotificationDelivery.objects.get(task=task)
        self.assignee_scope.is_active = False
        self.assignee_scope.save(update_fields=("is_active",))

        self.assertTrue(dispatch_task_notification(delivery.pk))

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, delivery.Status.NOT_APPLICABLE)
        self.assertIsNone(delivery.notification_id)

    def test_person_timeline_contains_only_permissioned_task_events(self):
        task = self.create()
        items = person_timeline_for_user(user=self.user, person=self.person_a)
        self.assertTrue(
            any(item.source_key.endswith(str(task.events.get().uuid)) for item in items)
        )
        self.user.user_permissions.remove(
            Permission.objects.get(
                content_type__app_label="hydra_tasks",
                codename="view_hydrataskevent",
            )
        )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)
        items = person_timeline_for_user(user=self.user, person=self.person_a)
        self.assertFalse(any(item.category == "tasks" for item in items))

    def test_readiness_checks_target_event_sequence_and_current_assignee(self):
        self.create()
        results = {result.name: result for result in domain_integrity_results()}
        self.assertTrue(results["task_targets"].ok)
        self.assertTrue(results["task_event_sequences"].ok)
        self.assertTrue(results["task_assignees"].ok)

        self.assignee_scope.is_active = False
        self.assignee_scope.save(update_fields=("is_active",))
        results = {result.name: result for result in domain_integrity_results()}
        self.assertFalse(results["task_assignees"].ok)

    def test_scoped_views_and_direct_url_denial(self):
        task = self.create()
        self.login()
        listing = self.client.get(reverse("hydra-task-list"))
        detail = self.client.get(task.get_absolute_url())
        form = self.client.get(reverse("hydra-task-create", args=(self.person_a.uuid,)))

        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, task.title)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Immutable task history")
        self.assertEqual(form.status_code, 200)
        self.assertContains(form, f"{self.company_a.company} / {self.person_a.hydra_id}")
        self.assertEqual(detail.headers["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

        outsider_denied = self.client.get(
            reverse("hydra-task-create", args=(self.person_b.uuid,))
        )
        self.assertEqual(outsider_denied.status_code, 404)


class HydraTaskModelConstraintTests(TestCase):
    def test_task_module_exposes_no_delete_permission(self):
        self.assertFalse(
            Permission.objects.filter(
                content_type__app_label="hydra_tasks",
                codename="delete_hydratask",
            ).exists()
        )
