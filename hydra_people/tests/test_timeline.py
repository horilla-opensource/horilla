from datetime import timedelta

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from hydra_housing.tests.test_housing import HydraHousingTestCase
from hydra_people.models import Person
from hydra_people.timeline import MAX_TIMELINE_ITEMS, person_timeline_for_user


class PersonTimelineTests(HydraHousingTestCase):
    def grant_full_timeline_read(self):
        self.grant_housing_read()
        self.grant(
            ("hydra_coordination", "view_team"),
            ("hydra_coordination", "view_personassignment"),
            ("hydra_coordination", "view_organizationaccessevent"),
            ("hydra_housing", "view_housingassignmentevent"),
            ("hydra_arrivals", "view_arrivalplan"),
            ("hydra_arrivals", "view_arrivalstatushistory"),
            ("hydra_arrivals", "view_onboardinghandoff"),
            ("hydra_arrivals", "view_onboardinghandoffevent"),
            ("hydra_legalization", "view_legalizationcase"),
            ("hydra_legalization", "view_legalizationstatushistory"),
            ("hydra_legalization", "view_legalizationworkevent"),
            ("hydra_legalization", "view_legalizationauthorityevent"),
            ("hydra_legalization", "view_legalizationrenewallink"),
            ("hydra_documents", "view_privatedocument"),
            ("hydra_documents", "view_documentaccesslog"),
            ("hydra_people", "view_candidatestagetransition"),
        )

    def test_timeline_composes_scoped_authoritative_facts_in_order(self):
        self.grant_full_timeline_read()
        _facility, _room, bed = self.make_inventory(actor=self.admin)
        self.make_assignment(bed=bed, actor=self.admin)

        items = person_timeline_for_user(user=self.user, person=self.person_a)

        source_keys = [item.source_key for item in items]
        self.assertTrue(
            any(key.startswith("hydra_housing.housingassignmentevent:") for key in source_keys)
        )
        self.assertTrue(
            any(key.startswith("hydra_people.personapplication:") for key in source_keys)
        )
        self.assertTrue(
            any(key.startswith("hydra_coordination.personassignment:") for key in source_keys)
        )
        self.assertEqual(len(source_keys), len(set(source_keys)))
        self.assertEqual(
            [item.occurred_at for item in items],
            sorted((item.occurred_at for item in items), reverse=True),
        )

    def test_each_domain_fact_requires_its_source_permission(self):
        self.grant_housing_read()
        _facility, _room, bed = self.make_inventory(actor=self.admin)
        self.make_assignment(bed=bed, actor=self.admin)

        without_event_permission = person_timeline_for_user(
            user=self.user,
            person=self.person_a,
        )
        self.assertFalse(
            any(item.category == "housing" for item in without_event_permission)
        )

        self.grant(("hydra_housing", "view_housingassignmentevent"))
        with_event_permission = person_timeline_for_user(
            user=self.user,
            person=self.person_a,
        )
        self.assertTrue(any(item.category == "housing" for item in with_event_permission))

    def test_cross_scope_person_has_no_timeline_and_direct_url_is_404(self):
        self.grant_full_timeline_read()

        items = person_timeline_for_user(user=self.user, person=self.person_b)
        self.login()
        response = self.client.get(
            reverse("hydra-person-detail", args=(self.person_b.uuid,))
        )

        self.assertEqual(items, [])
        self.assertEqual(response.status_code, 404)

    def test_audit_payload_values_are_not_copied_to_display_items(self):
        self.grant_read()
        content_type = ContentType.objects.get_for_model(
            Person,
            for_concrete_model=False,
        )
        LogEntry.objects.create(
            content_type=content_type,
            object_pk=str(self.person_a.pk),
            object_id=self.person_a.pk,
            object_repr=str(self.person_a),
            action=LogEntry.Action.UPDATE,
            changes={"passport_name": ["OLD SECRET NAME", "NEW SECRET NAME"]},
            changes_text="",
            actor=self.user,
        )

        items = person_timeline_for_user(user=self.user, person=self.person_a)
        rendered_projection = " ".join(
            f"{item.category_label} {item.label} {item.detail}" for item in items
        )

        self.assertIn("Person record updated", rendered_projection)
        self.assertNotIn("OLD SECRET NAME", rendered_projection)
        self.assertNotIn("NEW SECRET NAME", rendered_projection)

    def test_timeline_limit_is_fail_safe_and_bounded(self):
        self.grant_read()
        content_type = ContentType.objects.get_for_model(
            Person,
            for_concrete_model=False,
        )
        now = timezone.now()
        LogEntry.objects.bulk_create(
            [
                LogEntry(
                    content_type=content_type,
                    object_pk=str(self.person_a.pk),
                    object_id=self.person_a.pk,
                    object_repr=str(self.person_a),
                    action=LogEntry.Action.UPDATE,
                    changes={"lifecycle_state": ["candidate", "candidate"]},
                    changes_text="",
                    actor=self.user,
                    timestamp=now - timedelta(microseconds=index),
                )
                for index in range(MAX_TIMELINE_ITEMS + 5)
            ]
        )

        items = person_timeline_for_user(
            user=self.user,
            person=self.person_a,
            limit=9999,
        )

        self.assertEqual(len(items), MAX_TIMELINE_ITEMS)
        self.assertGreaterEqual(items[0].occurred_at, items[-1].occurred_at)

    def test_selector_query_count_is_bounded_not_per_event(self):
        self.grant_full_timeline_read()
        _facility, _room, bed = self.make_inventory(actor=self.admin)
        self.make_assignment(bed=bed, actor=self.admin)
        self.user.get_all_permissions()
        ContentType.objects.get_for_model(Person, for_concrete_model=False)

        with CaptureQueriesContext(connection) as queries:
            person_timeline_for_user(user=self.user, person=self.person_a)

        self.assertLessEqual(
            len(queries),
            20,
            "\n".join(query["sql"] for query in queries.captured_queries),
        )

    def test_person_detail_renders_mobile_friendly_timeline(self):
        self.grant_full_timeline_read()
        _facility, _room, bed = self.make_inventory(actor=self.admin)
        self.make_assignment(bed=bed, actor=self.admin)
        self.login()

        response = self.client.get(
            reverse("hydra-person-detail", args=(self.person_a.uuid,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="person-timeline-title"')
        self.assertContains(response, 'class="hydra-timeline"')
        self.assertContains(response, "Housing assigned")
