"""
The database-initialization flow must be unreachable once initialized.

The bug this guards: every step view after the password-gated entry view
carried only ``@hx_request_required``, which asserts an ``HX-Request`` header
and nothing else -- forgeable with a single curl flag.
``initialize_database_user`` calls ``create_superuser()`` then ``login()``, so
an unauthenticated caller could create a superuser under an unused username on
a fully provisioned instance and be logged in as them.
"""

from django.test import TestCase, override_settings
from django.urls import reverse

from base.models import Company
from horilla.testkit import make_employee
from horilla_auth.models import HorillaUser

# Every view in the flow, including the edit/delete endpoints that are easy to
# miss when auditing "the signup steps".
STEP_URL_NAMES = [
    "initialize-database-user",
    "initialize-database-company",
    "initialize-database-department",
    "initialize-database-job-position",
]


class InitializedDatabaseRejectsSetupFlow(TestCase):
    """With a superuser that has an employee, setup is over and must 404."""

    def setUp(self):
        company = Company.objects.create(company="Acme", hq=True)
        user = HorillaUser.objects.create_superuser(
            username="root", email="root@test.horilla", password="pw-not-real"
        )
        # initialize_database_condition() only counts setup as finished when a
        # superuser has an employee attached, so the guard is not armed without
        # this.
        make_employee(company=company, email="root@test.horilla", user=user)

    @override_settings(DEBUG=True)
    def test_step_views_404_when_database_already_initialized(self):
        for name in STEP_URL_NAMES:
            with self.subTest(view=name):
                response = self.client.get(
                    reverse(name), headers={"hx-request": "true"}
                )
                self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True)
    def test_forged_hx_header_cannot_create_a_superuser(self):
        before = HorillaUser.objects.filter(is_superuser=True).count()

        response = self.client.post(
            reverse("initialize-database-user"),
            {
                "username": "backdoor",
                "password": "attacker-chosen",
                "confirm_password": "attacker-chosen",
                "firstname": "Back",
                "lastname": "Door",
                "badge_id": "BD1",
                "email": "backdoor@test.horilla",
                "phone": "9999999999",
            },
            headers={"hx-request": "true"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(HorillaUser.objects.filter(username="backdoor").exists())
        self.assertEqual(HorillaUser.objects.filter(is_superuser=True).count(), before)
        # A 404 that still logged the caller in would defeat the point.
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(DEBUG=False)
    def test_step_views_404_in_production_regardless_of_state(self):
        for name in STEP_URL_NAMES:
            with self.subTest(view=name):
                response = self.client.get(
                    reverse(name), headers={"hx-request": "true"}
                )
                self.assertEqual(response.status_code, 404)


class UninitializedDatabaseAllowsSetupFlow(TestCase):
    """The guard must not break a genuinely fresh install."""

    @override_settings(DEBUG=True)
    def test_user_step_is_reachable_before_any_user_exists(self):
        self.assertFalse(HorillaUser.objects.exists())

        response = self.client.get(
            reverse("initialize-database-user"), headers={"hx-request": "true"}
        )

        self.assertEqual(response.status_code, 200)
