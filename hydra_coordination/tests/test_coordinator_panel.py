from datetime import datetime, time, timedelta

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils import timezone

from employee.models import Employee
from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.coordinator_selectors import (
    COORDINATOR_PERMISSIONS,
    coordinator_locations_for_user,
    coordinator_snapshot_for_location,
)
from hydra_coordination.models import Location, ScopeGrant
from hydra_legalization.models import LegalizationCase
from hydra_people.models import Person
from hydra_people.services import link_candidate
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


class CoordinatorPanelTestCase(HydraRecruitmentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.today = timezone.localdate()
        cls.location_a = Location.objects.get(name="Location A")
        cls.location_b = Location.objects.get(name="Location B")
        cls.company_only = cls.make_operator("company-only-coordinator")
        cls.limited = cls.make_operator("limited-coordinator")

        cls.grant_permissions(cls.user, *COORDINATOR_PERMISSIONS)
        cls.grant_permissions(cls.company_only, *COORDINATOR_PERMISSIONS)
        cls.grant_permissions(cls.limited, *COORDINATOR_PERMISSIONS[1:])
        ScopeGrant.objects.create(user=cls.user, location=cls.location_a)
        ScopeGrant.objects.create(
            user=cls.user,
            location=cls.location_b,
            valid_from=cls.today - timedelta(days=10),
            valid_until=cls.today - timedelta(days=1),
        )
        ScopeGrant.objects.create(user=cls.company_only, company=cls.company_a)
        ScopeGrant.objects.create(user=cls.limited, location=cls.location_a)

        cls.candidate_c = cls.make_candidate(
            "Celina application",
            "celina.application@example.test",
            cls.recruitment_a,
            cls.job_a,
            cls.stage_a,
        )
        link_candidate(
            person=cls.person_c,
            candidate=cls.candidate_c,
            actor=cls.admin,
        )
        cls.gap_person = cls.make_person("GAP PERSON", "Gap", "Person")
        cls.gap_candidate = cls.make_candidate(
            "Gap application",
            "gap.application@example.test",
            cls.recruitment_a,
            cls.job_a,
            cls.stage_a,
        )
        link_candidate(
            person=cls.gap_person,
            candidate=cls.gap_candidate,
            actor=cls.admin,
        )

        start_of_today = timezone.make_aware(
            datetime.combine(cls.today, time.min),
            timezone.get_current_timezone(),
        )
        cls.overdue_arrival = cls.make_arrival(
            person=cls.person_a,
            candidate=cls.candidate_a,
            location=cls.location_a,
            planned_at=start_of_today,
        )
        cls.no_show_arrival = cls.make_arrival(
            person=cls.person_c,
            candidate=cls.candidate_c,
            location=cls.location_a,
            planned_at=start_of_today + timedelta(hours=5),
            status=ArrivalPlan.Status.NO_SHOW,
            no_show_reason="Did not arrive",
        )
        cls.outside_arrival = cls.make_arrival(
            person=cls.person_b,
            candidate=cls.candidate_b,
            location=cls.location_b,
            planned_at=start_of_today,
        )
        cls.gap_arrival = cls.make_arrival(
            person=cls.gap_person,
            candidate=cls.gap_candidate,
            location=cls.location_a,
            planned_at=start_of_today - timedelta(days=1),
            status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=start_of_today - timedelta(hours=12),
        )

        cls.overdue_case = cls.make_case(
            person=cls.person_a,
            reference="OVERDUE-A",
            status=LegalizationCase.Status.SUBMITTED,
            deadline=cls.today - timedelta(days=1),
        )
        cls.missing_deadline_case = cls.make_case(
            person=cls.person_a,
            reference="MISSING-A",
            status=LegalizationCase.Status.DRAFT,
            deadline=None,
        )
        cls.expiring_case = cls.make_case(
            person=cls.person_c,
            reference="EXPIRING-A",
            status=LegalizationCase.Status.APPROVED,
            deadline=cls.today - timedelta(days=30),
            valid_from=cls.today - timedelta(days=30),
            valid_until=cls.today + timedelta(days=10),
        )
        cls.safe_case = cls.make_case(
            person=cls.person_c,
            reference="SAFE-A",
            status=LegalizationCase.Status.APPROVED,
            deadline=cls.today - timedelta(days=30),
            valid_from=cls.today - timedelta(days=30),
            valid_until=cls.today + timedelta(days=180),
        )
        cls.outside_case = cls.make_case(
            person=cls.person_b,
            reference="OUTSIDE-B",
            status=LegalizationCase.Status.SUBMITTED,
            deadline=cls.today - timedelta(days=1),
        )

    @classmethod
    def make_operator(cls, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password="test-password",
            is_new_employee=False,
        )
        Employee.objects.create(
            employee_user_id=user,
            employee_first_name=username,
            employee_last_name="Operator",
            email=f"{username}@example.test",
            phone="+48123456789",
        )
        return user

    @classmethod
    def grant_permissions(cls, user, *permissions):
        user.user_permissions.add(
            *[
                Permission.objects.get(
                    content_type__app_label=permission.split(".", 1)[0],
                    codename=permission.split(".", 1)[1],
                )
                for permission in permissions
            ]
        )

    @classmethod
    def make_arrival(
        cls,
        *,
        person,
        candidate,
        location,
        planned_at,
        status=ArrivalPlan.Status.PLANNED,
        actual_arrived_at=None,
        no_show_reason="",
    ):
        return ArrivalPlan.objects.create(
            person=person,
            candidate=candidate,
            destination_location=location,
            coordinator=cls.admin,
            planned_at=planned_at,
            status=status,
            actual_arrived_at=actual_arrived_at,
            no_show_reason=no_show_reason,
            created_by=cls.admin,
            modified_by=cls.admin,
        )

    @classmethod
    def make_case(
        cls,
        *,
        person,
        reference,
        status,
        deadline,
        valid_from=None,
        valid_until=None,
    ):
        return LegalizationCase.objects.create(
            person=person,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            status=status,
            responsible=cls.admin,
            reference_number=reference,
            deadline=deadline,
            valid_from=valid_from,
            valid_until=valid_until,
            created_by=cls.admin,
            modified_by=cls.admin,
        )

    def setUp(self):
        super().setUp()
        self.company_only = User.objects.get(pk=self.company_only.pk)
        self.limited = User.objects.get(pk=self.limited.pk)

    def login_user(self, user):
        self.client.force_login(user)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()


class CoordinatorSelectorTests(CoordinatorPanelTestCase):
    def test_only_current_direct_location_grants_open_panel(self):
        self.assertQuerySetEqual(
            coordinator_locations_for_user(user=self.user),
            [self.location_a],
            transform=lambda location: location,
        )
        self.assertFalse(
            coordinator_locations_for_user(user=self.company_only).exists()
        )

    def test_snapshot_composes_scoped_operational_exceptions(self):
        snapshot = coordinator_snapshot_for_location(
            user=self.user,
            location=self.location_a,
            day=self.today,
        )

        self.assertEqual(snapshot.arrivals_today, 2)
        self.assertEqual(snapshot.arrival_exception_count, 2)
        self.assertEqual(snapshot.assignment_gap_count, 1)
        self.assertEqual(snapshot.legalization_exception_count, 3)
        self.assertEqual(
            {row.person for row in snapshot.arrival_exceptions},
            {self.person_a, self.person_c},
        )
        self.assertEqual(snapshot.assignment_gaps[0].person, self.gap_person)
        legalization_references = {
            row.case.reference_number for row in snapshot.legalization_exceptions
        }
        self.assertEqual(
            legalization_references,
            {"OVERDUE-A", "MISSING-A", "EXPIRING-A"},
        )
        self.assertNotIn("OUTSIDE-B", legalization_references)
        self.assertNotIn("SAFE-A", legalization_references)

    def test_snapshot_rechecks_location_scope(self):
        with self.assertRaises(PermissionDenied):
            coordinator_snapshot_for_location(
                user=self.user,
                location=self.location_b,
                day=self.today,
            )


class CoordinatorPanelViewTests(CoordinatorPanelTestCase):
    def test_panel_shows_only_direct_location_exceptions(self):
        self.login_user(self.user)

        response = self.client.get(reverse("hydra-coordinator-panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.location_a.name)
        self.assertNotContains(response, self.location_b.name)
        self.assertContains(response, self.person_a.passport_name)
        self.assertContains(response, self.gap_person.passport_name)
        self.assertContains(response, "Overdue arrival")
        self.assertContains(response, "No-show")
        self.assertContains(response, "No team assignment")
        self.assertContains(response, "Overdue deadline")
        self.assertContains(response, "Missing deadline")
        self.assertContains(response, "Validity within 30 days")
        self.assertNotContains(response, self.person_b.passport_name)
        self.assertNotContains(response, self.outside_case.reference_number)
        self.assertContains(response, 'aria-current="page"')

    def test_direct_url_location_tampering_returns_404(self):
        self.login_user(self.user)

        response = self.client.get(
            reverse("hydra-coordinator-panel"),
            {"location": self.location_b.pk},
        )

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(
            response,
            self.person_b.passport_name,
            status_code=404,
        )

    def test_selected_company_all_does_not_widen_location_scope(self):
        self.login_user(self.user)

        response = self.client.get(reverse("hydra-coordinator-panel"))

        self.assertNotContains(response, self.location_b.name)
        self.assertNotContains(response, self.person_b.hydra_id)

    def test_company_grant_does_not_open_coordinator_location(self):
        self.login_user(self.company_only)

        response = self.client.get(reverse("hydra-coordinator-panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No direct location scope")
        self.assertNotContains(response, self.location_a.name)
        self.assertNotContains(response, self.person_a.passport_name)

    def test_missing_dedicated_permission_returns_403(self):
        self.login_user(self.limited)

        response = self.client.get(reverse("hydra-coordinator-panel"))

        self.assertEqual(response.status_code, 403)

    def test_future_date_is_rejected(self):
        self.login_user(self.user)

        response = self.client.get(
            reverse("hydra-coordinator-panel"),
            {"date": self.today + timedelta(days=1)},
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_location_identifier_returns_404(self):
        self.login_user(self.user)

        response = self.client.get(
            reverse("hydra-coordinator-panel"),
            {"location": "not-a-number"},
        )

        self.assertEqual(response.status_code, 404)
