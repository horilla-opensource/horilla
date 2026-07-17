from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from employee.models import Employee
from hydra_arrivals.models import ArrivalPlan, OnboardingHandoff
from hydra_coordination.models import Location, PersonAssignment, Section, Team
from hydra_documents.models import (
    PrivateDocument,
    PrivateDocumentType,
    QuarantinedUpload,
)
from hydra_housing.models import (
    HousingAssignment,
    HousingBed,
    HousingFacility,
    HousingRoom,
)
from hydra_legalization.models import LegalizationCase, LegalizationProcedureType
from hydra_people.duplicate_services import (
    MERGE_FIELDS,
    build_merge_plan,
    dismiss_duplicate_suggestion,
    merge_duplicate_people,
    refresh_duplicate_suggestions_for_person,
)
from hydra_people.models import (
    Person,
    PersonApplication,
    PersonDuplicateSuggestion,
    PersonMergeEvent,
    PersonMergeReference,
)
from hydra_people.tests.test_people import HydraPeopleTestCase
from onboarding.models import CandidateStage, OnboardingStage


BASE_MERGE_CODENAMES = (
    "view_person",
    "change_person",
    "review_person_duplicates",
    "merge_person",
    "link_candidate",
    "view_candidate",
)


class PersonDuplicateDetectionTests(HydraPeopleTestCase):
    def matching_people(self):
        first = self.create_person(email="first@example.test", phone="+48 111 222 333")
        second = self.create_person(email="second@example.test", phone="+48 999 888 777")
        return first, second

    def suggestion(self):
        return PersonDuplicateSuggestion.objects.get(state="open")

    def test_exact_identity_creates_suggestion_but_never_auto_merges(self):
        first, second = self.matching_people()

        suggestion = self.suggestion()

        self.assertEqual(suggestion.person_low_id, min(first.pk, second.pk))
        self.assertEqual(suggestion.person_high_id, max(first.pk, second.pk))
        self.assertIn("identity_exact", suggestion.match_reasons)
        self.assertEqual(suggestion.score, 100)
        self.assertIsNone(first.merged_into_id)
        self.assertIsNone(second.merged_into_id)
        self.assertEqual(PersonMergeEvent.objects.count(), 0)

    def test_phone_match_is_normalized_and_a_changed_pair_becomes_stale(self):
        first = self.create_person(
            passport_name="ANNA ONE",
            first_name="Anna",
            last_name="One",
            date_of_birth=timezone.localdate().replace(year=1990),
            email="anna-one@example.test",
            phone="+48 (123) 456-789",
        )
        second = self.create_person(
            passport_name="MARIA TWO",
            first_name="Maria",
            last_name="Two",
            date_of_birth=timezone.localdate().replace(year=1991),
            email="maria-two@example.test",
            phone="48123456789",
        )
        suggestion = self.suggestion()
        self.assertEqual(suggestion.match_reasons, ["phone_exact"])

        second.phone = "+48 000 000 000"
        second.save()
        refresh_duplicate_suggestions_for_person(person_id=second.pk)

        suggestion.refresh_from_db()
        self.assertEqual(suggestion.state, PersonDuplicateSuggestion.State.STALE)
        self.assertIsNotNone(suggestion.resolved_at)
        self.assertIsNone(first.merged_into_id)

    def test_dismissal_requires_permission_scope_and_reason(self):
        self.matching_people()
        suggestion = self.suggestion()
        self.grant("view_person", "review_person_duplicates", "dismiss_person_duplicate")

        with self.assertRaises(ValidationError):
            dismiss_duplicate_suggestion(
                suggestion=suggestion,
                actor=self.user,
                reason="short",
            )
        dismissed = dismiss_duplicate_suggestion(
            suggestion=suggestion,
            actor=self.user,
            reason="Verified different passport holders",
        )

        self.assertEqual(dismissed.state, PersonDuplicateSuggestion.State.DISMISSED)
        self.assertEqual(dismissed.resolved_by, self.user)
        refresh_duplicate_suggestions_for_person(person_id=dismissed.person_low_id)
        dismissed.refresh_from_db()
        self.assertEqual(dismissed.state, PersonDuplicateSuggestion.State.DISMISSED)

    def test_duplicate_queue_is_permission_protected(self):
        self.matching_people()
        self.login()

        denied = self.client.get(reverse("hydra-duplicate-list"))
        self.grant("view_person", "review_person_duplicates")
        allowed = self.client.get(reverse("hydra-duplicate-list"))

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, "Hydra never merges people automatically")


class PersonMergeServiceTests(HydraPeopleTestCase):
    def setUp(self):
        super().setUp()
        self.first = self.create_person(
            email="canonical@example.test",
            phone="+48 111 222 333",
        )
        self.second = self.create_person(
            email="source@example.test",
            phone="+48 999 888 777",
        )
        self.suggestion = PersonDuplicateSuggestion.objects.get(state="open")

    def grant_merge(self, *extra):
        self.grant(*BASE_MERGE_CODENAMES, *extra)

    def merge(self, *, survivor=None, plan=None, field_sources=None):
        survivor = survivor or self.first
        plan = plan or build_merge_plan(
            suggestion=self.suggestion,
            survivor_id=survivor.pk,
        )
        return merge_duplicate_people(
            suggestion=self.suggestion,
            survivor_id=survivor.pk,
            field_sources=field_sources
            or {field_name: "person_a" for field_name in MERGE_FIELDS},
            reason="Reviewed exact identity and supporting records",
            expected_version_token=plan["version_token"],
            actor=self.user,
        )

    def test_merge_moves_distinct_applications_and_preserves_source_alias(self):
        first_candidate = self.create_candidate("alpha")
        second_candidate = self.create_candidate("two")
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")
        from hydra_people.services import link_candidate

        link_candidate(person=self.first, candidate=first_candidate, actor=self.user)
        source_link = link_candidate(
            person=self.second,
            candidate=second_candidate,
            actor=self.user,
        )
        self.grant_merge("view_personmergeevent")
        plan = build_merge_plan(suggestion=self.suggestion, survivor_id=self.first.pk)

        event = self.merge(plan=plan)

        self.second.refresh_from_db()
        source_link.refresh_from_db()
        self.suggestion.refresh_from_db()
        self.assertEqual(source_link.person, self.first)
        self.assertEqual(self.first.applications.count(), 2)
        self.assertEqual(self.second.merged_into, self.first)
        self.assertFalse(self.second.is_active)
        self.assertEqual(self.second.lifecycle_state, Person.LifecycleState.INACTIVE)
        self.assertEqual(event.preserved_source_identifiers["duplicate_hydra_id"], self.second.hydra_id)
        self.assertEqual(event.moved_reference_counts["applications"], 1)
        self.assertTrue(
            PersonMergeReference.objects.filter(
                event=event,
                relation_kind="applications",
                object_id=str(source_link.pk),
            ).exists()
        )
        self.assertEqual(self.suggestion.state, PersonDuplicateSuggestion.State.MERGED)
        self.assertEqual(list(Person.objects.filter(merged_into__isnull=True)), [self.first])
        with self.assertRaises(TypeError):
            self.second.save()
        with self.assertRaises(TypeError):
            PersonMergeEvent.objects.filter(pk=event.pk).update(reason="rewrite")

    def test_same_recruitment_conflict_blocks_every_write(self):
        first_candidate = self.create_candidate("alpha")
        second_candidate = self.create_candidate("beta")
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")
        from hydra_people.services import link_candidate

        link_candidate(person=self.first, candidate=first_candidate, actor=self.user)
        link_candidate(person=self.second, candidate=second_candidate, actor=self.user)
        self.grant_merge()
        plan = build_merge_plan(suggestion=self.suggestion, survivor_id=self.first.pk)
        self.assertIn("same_recruitment", {item.code for item in plan["conflicts"]})

        with self.assertRaises(ValidationError):
            self.merge(plan=plan)

        self.second.refresh_from_db()
        self.assertIsNone(self.second.merged_into_id)
        self.assertEqual(PersonMergeEvent.objects.count(), 0)
        self.assertEqual(PersonApplication.objects.filter(person=self.second).count(), 1)

    def test_employee_backed_source_must_be_selected_as_canonical(self):
        self.second.employee = self.employee
        self.second.lifecycle_state = Person.LifecycleState.EMPLOYEE
        self.second.save()
        self.grant_merge()

        plan = build_merge_plan(suggestion=self.suggestion, survivor_id=self.first.pk)

        self.assertIn("duplicate_employee", {item.code for item in plan["conflicts"]})
        with self.assertRaises(ValidationError):
            self.merge(plan=plan)
        self.assertFalse(PersonMergeEvent.objects.exists())

    def test_changed_data_invalidates_preview_token_and_rolls_back(self):
        self.grant_merge()
        plan = build_merge_plan(suggestion=self.suggestion, survivor_id=self.first.pk)
        Person.objects.filter(pk=self.second.pk).update(email="changed@example.test")

        with self.assertRaisesRegex(ValidationError, "changed after preview"):
            self.merge(plan=plan)

        self.second.refresh_from_db()
        self.assertIsNone(self.second.merged_into_id)
        self.assertFalse(PersonMergeEvent.objects.exists())

    def test_merge_service_denies_actor_without_dedicated_permissions(self):
        plan = build_merge_plan(suggestion=self.suggestion, survivor_id=self.first.pk)

        with self.assertRaises(PermissionDenied):
            self.merge(plan=plan)

        self.second.refresh_from_db()
        self.assertIsNone(self.second.merged_into_id)
        self.assertFalse(PersonMergeEvent.objects.exists())

    def test_even_superuser_cannot_attach_new_work_to_merged_alias(self):
        self.grant_merge()
        event = self.merge()
        candidate = self.create_candidate("two")
        self.user.is_superuser = True
        self.user.save(update_fields=("is_superuser",))
        from hydra_people.services import link_candidate

        with self.assertRaisesRegex(ValidationError, "merged alias"):
            link_candidate(person=event.duplicate, candidate=candidate, actor=self.user)

        self.assertFalse(PersonApplication.objects.filter(candidate=candidate).exists())

    def test_merge_moves_every_supported_operational_reference(self):
        location = Location.objects.create(
            company=self.company,
            name="Merge location",
            code="MRG",
        )
        section = Section.objects.create(
            location=location,
            department=self.department,
            name="Merge section",
            code="MRG",
        )
        team = Team.objects.create(section=section, name="Merge team", code="MRG")
        assignment = PersonAssignment.objects.create(
            person=self.second,
            team=team,
            department=self.department,
            valid_from=timezone.localdate(),
        )
        facility = HousingFacility.objects.create(
            location=location,
            name="Merge house",
            address="Merge street 1",
        )
        room = HousingRoom.objects.create(facility=facility, name="1")
        bed = HousingBed.objects.create(room=room, label="A")
        housing = HousingAssignment.objects.create(
            person=self.second,
            bed=bed,
            valid_from=timezone.localdate(),
        )
        candidate = self.create_candidate("two")
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")
        from hydra_people.services import link_candidate

        link_candidate(person=self.second, candidate=candidate, actor=self.user)
        arrival = ArrivalPlan.objects.create(
            person=self.second,
            candidate=candidate,
            destination_location=location,
            coordinator=self.user,
            planned_at=timezone.now() - timedelta(hours=1),
            status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=timezone.now(),
        )
        onboarding_stage = OnboardingStage._base_manager.get(
            recruitment_id=self.recruitment_two,
            sequence=0,
        )
        candidate_stage = CandidateStage._base_manager.create(
            candidate_id=candidate,
            onboarding_stage_id=onboarding_stage,
        )
        handoff = OnboardingHandoff.objects.create(
            arrival=arrival,
            person=self.second,
            candidate=candidate,
            candidate_stage=candidate_stage,
            initiated_by=self.user,
            started_snapshot={"source": "duplicate-test"},
        )
        self.second.lifecycle_state = Person.LifecycleState.ONBOARDING
        self.second.save(update_fields=("lifecycle_state",))
        procedure = LegalizationProcedureType.objects.get(
            company__isnull=True,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
        )
        case = LegalizationCase.objects.create(
            person=self.second,
            company=self.company,
            procedure_type=procedure,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            procedure_snapshot=procedure.rules_snapshot(company_id=self.company.pk),
            responsible=self.user,
        )
        document_type = PrivateDocumentType.objects.get(
            code="identity-document", company__isnull=True
        )
        document = PrivateDocument.objects.create(
            person=self.second,
            candidate=candidate,
            document_type=document_type,
            title="Identity evidence",
            category=PrivateDocument.Category.IDENTITY,
            original_filename="identity.pdf",
            verified_content_type="application/pdf",
            size=0,
            sha256="0" * 64,
        )
        quarantine = QuarantinedUpload.objects.create(
            person=self.second,
            candidate=candidate,
            actor=self.user,
            original_filename="pending.pdf",
            verified_content_type="application/pdf",
            size=0,
            sha256="1" * 64,
            purge_after=timezone.now() + timedelta(hours=1),
        )
        self.grant_merge(
            "view_arrivalplan",
            "change_arrivalplan",
            "view_onboardinghandoff",
            "reconcile_onboardinghandoff",
            "view_personassignment",
            "change_personassignment",
            "assign_person",
            "view_team",
            "view_housingfacility",
            "view_housingroom",
            "view_housingbed",
            "view_housingassignment",
            "change_housingassignment",
            "move_housingassignment",
            "view_location",
            "view_legalizationcase",
            "change_legalizationcase",
            "view_privatedocument",
            "change_privatedocument",
            "view_quarantinedupload",
        )
        plan = build_merge_plan(suggestion=self.suggestion, survivor_id=self.first.pk)
        self.assertEqual(plan["conflicts"], ())

        field_sources = {field_name: "person_a" for field_name in MERGE_FIELDS}
        field_sources["lifecycle_state"] = "person_b"
        event = self.merge(plan=plan, field_sources=field_sources)

        for record in (
            assignment,
            housing,
            arrival,
            handoff,
            case,
            document,
            quarantine,
        ):
            record.refresh_from_db()
            self.assertEqual(record.person_id, self.first.pk)
        self.assertEqual(event.moved_reference_counts["applications"], 1)
        self.assertEqual(event.moved_reference_counts["arrival_plans"], 1)
        self.assertEqual(event.moved_reference_counts["onboarding_handoffs"], 1)
        self.assertEqual(event.moved_reference_counts["coordination_assignments"], 1)
        self.assertEqual(event.moved_reference_counts["housing_assignments"], 1)
        self.assertEqual(event.moved_reference_counts["legalization_cases"], 1)
        self.assertEqual(event.moved_reference_counts["private_documents"], 1)
        self.assertEqual(event.moved_reference_counts["quarantined_uploads"], 1)
        self.assertEqual(event.moved_references.count(), 8)


class PersonDuplicateViewTests(HydraPeopleTestCase):
    def setUp(self):
        super().setUp()
        self.first = self.create_person(email="view-one@example.test")
        self.second = self.create_person(email="view-two@example.test")
        self.suggestion = PersonDuplicateSuggestion.objects.get(state="open")
        self.grant(*BASE_MERGE_CODENAMES, "dismiss_person_duplicate")
        self.login()

    def test_preview_and_signed_commit_complete_the_reviewed_journey(self):
        payload = {
            "canonical_person": str(self.first.pk),
            "reason": "Reviewed matching identity and chose the canonical source",
        }
        payload.update({f"source_{field}": "person_a" for field in MERGE_FIELDS})

        preview = self.client.post(
            reverse("hydra-duplicate-preview", args=(self.suggestion.uuid,)),
            payload,
        )

        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "Canonical merge preview")
        signed_payload = preview.context["commit_form"].initial["payload"]
        commit = self.client.post(
            reverse("hydra-duplicate-commit", args=(self.suggestion.uuid,)),
            {"payload": signed_payload, "confirmation": "on"},
        )
        self.assertRedirects(commit, self.first.get_absolute_url())
        self.second.refresh_from_db()
        self.assertEqual(self.second.merged_into, self.first)

        alias_response = self.client.get(self.second.get_absolute_url())
        self.assertRedirects(alias_response, self.first.get_absolute_url())
        search = self.client.get(reverse("hydra-person-list"), {"q": self.second.hydra_id})
        self.assertContains(search, self.first.hydra_id)
        self.assertNotContains(search, f'href="{self.second.get_absolute_url()}"')

    def test_cross_scope_pair_is_hidden_from_direct_review_url(self):
        outsider = User.objects.create_user(
            username="duplicate-outsider",
            password="test-password",
            is_new_employee=False,
        )
        outsider_employee = Employee.objects.create(
            employee_user_id=outsider,
            employee_first_name="Outside",
            employee_last_name="Reviewer",
            email="duplicate-outsider@example.test",
            phone="+48123123123",
        )
        outsider_work_info = outsider_employee.employee_work_info
        outsider_work_info.company_id = self.company
        outsider_work_info.save()
        outsider.user_permissions.add(
            *Permission.objects.filter(
                codename__in=("view_person", "review_person_duplicates")
            )
        )
        self.client.force_login(outsider)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

        response = self.client.get(
            reverse("hydra-duplicate-detail", args=(self.suggestion.uuid,))
        )

        self.assertEqual(response.status_code, 404)
