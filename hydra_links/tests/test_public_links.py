from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.models import ScopeGrant
from hydra_links.models import PublicHydraLink
from hydra_links.public_urls import public_hydra_url, validate_public_hydra_url
from hydra_links.services import save_public_hydra_link
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from hydra_shell.templatetags.hydra_shell_tags import hydra_nav_is_active


class PublicHydraLinkTestCase(HydraRecruitmentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.location_a = cls.team_a.section.location
        cls.location_b = cls.team_b.section.location
        cls.global_link = PublicHydraLink.objects.get(
            kind=PublicHydraLink.Kind.ARRIVAL_GUIDANCE,
            location=None,
        )
        cls.training_a = save_public_hydra_link(
            link=PublicHydraLink(
                kind=PublicHydraLink.Kind.LOCATION_TRAINING,
                location=cls.location_a,
                label="Training Location A",
                base_url="https://training-a.example.test/start",
                order=20,
            ),
            actor=cls.admin,
        )
        cls.training_b = save_public_hydra_link(
            link=PublicHydraLink(
                kind=PublicHydraLink.Kind.LOCATION_TRAINING,
                location=cls.location_b,
                label="Training Location B",
                base_url="https://training-b.example.test/start",
                order=20,
            ),
            actor=cls.admin,
        )

    def grant_links(self, *, write=False, global_manage=False):
        permissions = [("hydra_links", "view_publichydralink")]
        if write:
            permissions.extend(
                (
                    ("hydra_links", "add_publichydralink"),
                    ("hydra_links", "change_publichydralink"),
                )
            )
        if global_manage:
            permissions.append(
                ("hydra_links", "manage_global_publichydralink")
            )
        self.grant(*permissions)


class PublicUrlContractTests(PublicHydraLinkTestCase):
    def test_builder_preserves_public_version_and_adds_only_language_and_source(self):
        url = public_hydra_url(
            base_url="https://portal.example.test/arrival?v=share-check-2",
            language_code="uk-UA",
        )

        self.assertEqual(
            url,
            "https://portal.example.test/arrival?v=share-check-2&lang=ua&from=hydra",
        )
        self.assertNotIn("person", url)
        self.assertNotIn("token", url)

    def test_validator_rejects_insecure_private_or_ambiguous_urls(self):
        invalid_urls = (
            "http://portal.example.test/",
            "https://user:secret@portal.example.test/",
            "https://portal.example.test:8443/",
            "https://portal.example.test/#private",
            "https://portal.example.test/?token=secret",
            "https://portal.example.test/?v=one&v=two",
        )
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    validate_public_hydra_url(url)

    def test_model_requires_global_arrival_and_location_training(self):
        invalid_arrival = PublicHydraLink(
            kind=PublicHydraLink.Kind.ARRIVAL_GUIDANCE,
            location=self.location_a,
            label="Arrival A",
            base_url="https://arrival.example.test/",
        )
        invalid_training = PublicHydraLink(
            kind=PublicHydraLink.Kind.LOCATION_TRAINING,
            label="Training",
            base_url="https://training.example.test/",
        )

        with self.assertRaises(ValidationError):
            invalid_arrival.full_clean()
        with self.assertRaises(ValidationError):
            invalid_training.full_clean()


class PublicLinkScopeAndPermissionTests(PublicHydraLinkTestCase):
    def test_directory_and_direct_update_intersect_permission_and_scope(self):
        self.grant_links(write=True)
        self.login()

        response = self.client.get(reverse("hydra-public-link-list"))
        denied = self.client.get(
            reverse("hydra-public-link-update", args=(self.training_b.uuid,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.global_link.label)
        self.assertContains(response, self.training_a.label)
        self.assertNotContains(response, self.training_b.label)
        self.assertContains(response, 'aria-current="page"')
        self.assertTrue(hydra_nav_is_active(response.context, "public_links"))
        self.assertEqual(denied.status_code, 404)

    def test_missing_view_permission_returns_403(self):
        self.login()

        response = self.client.get(reverse("hydra-public-link-list"))

        self.assertEqual(response.status_code, 403)

    def test_create_rejects_location_outside_active_scope(self):
        self.grant_links(write=True)
        self.login()

        response = self.client.post(
            reverse("hydra-public-link-create"),
            {
                "kind": PublicHydraLink.Kind.LOCATION_TRAINING,
                "location": self.location_b.pk,
                "label": "Outside scope",
                "base_url": "https://outside.example.test/",
                "order": 30,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(PublicHydraLink.objects.filter(label="Outside scope").exists())

    def test_non_global_manager_cannot_create_global_arrival_link(self):
        self.grant_links(write=True)
        PublicHydraLink.objects.filter(pk=self.global_link.pk).delete()
        self.login()

        response = self.client.post(
            reverse("hydra-public-link-create"),
            {
                "kind": PublicHydraLink.Kind.ARRIVAL_GUIDANCE,
                "location": "",
                "label": "Replacement arrival",
                "base_url": "https://arrival.example.test/",
                "order": 10,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(PublicHydraLink.objects.filter(label="Replacement arrival").exists())

    def test_service_rechecks_location_scope(self):
        self.grant_links(write=True)

        with self.assertRaises(PermissionDenied):
            save_public_hydra_link(
                link=PublicHydraLink(
                    kind=PublicHydraLink.Kind.LOCATION_TRAINING,
                    location=self.location_b,
                    label="Bypass",
                    base_url="https://bypass.example.test/",
                ),
                actor=self.user,
            )

    def test_selected_company_all_does_not_widen_links(self):
        self.grant_links()
        self.login()

        response = self.client.get(reverse("hydra-public-link-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.training_a.label)
        self.assertNotContains(response, self.training_b.label)


class ContextualPublicLinkTests(PublicHydraLinkTestCase):
    def test_person_detail_shows_global_and_current_location_links_only(self):
        self.grant_links()
        self.grant(
            ("hydra_people", "view_person"),
            ("hydra_coordination", "view_team"),
        )
        self.login()

        response = self.client.get(self.person_a.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.global_link.label)
        self.assertContains(response, self.training_a.label)
        self.assertNotContains(response, self.training_b.label)
        self.assertContains(response, "lang=en&amp;from=hydra")
        self.assertNotContains(response, f"person={self.person_a.pk}")

    def test_arrival_detail_shows_global_and_destination_training(self):
        self.grant_links()
        self.grant(
            ("hydra_arrivals", "view_arrivalplan"),
            ("hydra_coordination", "view_location"),
            ("hydra_people", "view_person"),
            ("recruitment", "view_candidate"),
        )
        ScopeGrant.objects.create(user=self.user, location=self.location_a)
        plan = ArrivalPlan.objects.create(
            person=self.person_a,
            candidate=self.candidate_a,
            planned_at=timezone.now(),
            destination_location=self.location_a,
            coordinator=self.user,
            created_by=self.admin,
        )
        self.login()

        response = self.client.get(plan.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.global_link.label)
        self.assertContains(response, self.training_a.label)
        self.assertNotContains(response, self.training_b.label)

    def test_brigadier_and_coordinator_receive_selected_location_training(self):
        self.grant_links()
        self.grant(
            ("hydra_coordination", "view_brigadier_panel"),
            ("hydra_coordination", "view_coordinator_panel"),
            ("hydra_coordination", "view_location"),
            ("hydra_people", "view_person"),
            ("employee", "view_employee"),
            ("attendance", "view_attendance"),
            ("hydra_arrivals", "view_arrivalplan"),
            ("hydra_legalization", "view_legalizationcase"),
        )
        ScopeGrant.objects.create(user=self.user, location=self.location_a)
        self.login()

        brigadier = self.client.get(
            reverse("hydra-brigadier-panel"),
            {"team": self.team_a.pk},
        )
        coordinator = self.client.get(
            reverse("hydra-coordinator-panel"),
            {"location": self.location_a.pk},
        )

        self.assertEqual(brigadier.status_code, 200)
        self.assertEqual(coordinator.status_code, 200)
        self.assertContains(brigadier, self.training_a.label)
        self.assertContains(coordinator, self.training_a.label)
        self.assertNotContains(brigadier, self.training_b.label)
        self.assertNotContains(coordinator, self.training_b.label)
