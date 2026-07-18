from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from hydra_people.models import (
    CandidateStageTransition,
    RecruitmentStageTransitionRule,
)
from hydra_people.recruitment_workflow import transition_candidate
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from hydra_people.timeline import person_timeline_for_user
from recruitment.models import Candidate, Stage


class ControlledRecruitmentWorkflowTests(HydraRecruitmentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.interview_a = Stage._base_manager.create(
            recruitment_id=cls.recruitment_a,
            stage="Interview A",
            stage_type="interview",
            sequence=2,
        )
        cls.hired_a = Stage._base_manager.create(
            recruitment_id=cls.recruitment_a,
            stage="Hired A",
            stage_type="hired",
            sequence=3,
        )
        cls.cancelled_a = Stage._base_manager.create(
            recruitment_id=cls.recruitment_a,
            stage="Cancelled A",
            stage_type="cancelled",
            sequence=50,
        )
        cls.cancelled_a_secondary = Stage._base_manager.create(
            recruitment_id=cls.recruitment_a,
            stage="Cancelled after review A",
            stage_type="cancelled",
            sequence=51,
        )
        cls.interview_b = Stage._base_manager.create(
            recruitment_id=cls.recruitment_b,
            stage="Interview B",
            stage_type="interview",
            sequence=2,
        )

    def grant_transition(self, *, history=False, override=False):
        self.grant_read()
        permissions = [("recruitment", "change_candidate")]
        if history:
            permissions.append(("hydra_people", "view_candidatestagetransition"))
        if override:
            permissions.append(("hydra_people", "override_recruitment_transition"))
        self.grant(*permissions)

    def test_default_rules_preserve_pipeline_and_require_risky_move_evidence(self):
        adjacent = RecruitmentStageTransitionRule.objects.get(
            from_stage=self.stage_a,
            to_stage=self.interview_a,
        )
        cancellation = RecruitmentStageTransitionRule.objects.get(
            from_stage=self.stage_a,
            to_stage=self.cancelled_a,
        )
        hiring = RecruitmentStageTransitionRule.objects.get(
            from_stage=self.interview_a,
            to_stage=self.hired_a,
        )

        self.assertFalse(adjacent.requires_reason)
        self.assertTrue(cancellation.requires_reason)
        self.assertTrue(hiring.requires_joining_date)

    def test_adjacent_transition_updates_candidate_and_records_immutable_event(self):
        self.grant_transition(history=True)

        candidate, event = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.interview_a,
            actor=self.user,
        )

        self.assertEqual(candidate.stage_id, self.interview_a)
        self.assertFalse(candidate.hired)
        self.assertFalse(candidate.canceled)
        self.assertEqual(event.from_stage, self.stage_a)
        self.assertEqual(event.to_stage, self.interview_a)
        self.assertEqual(event.actor, self.user)
        self.assertFalse(event.override)
        self.assertEqual(event.requirements_snapshot["rule_id"], event.rule_id)
        with self.assertRaises(TypeError):
            CandidateStageTransition.objects.filter(pk=event.pk).update(reason="changed")
        with self.assertRaises(TypeError):
            event.delete()

    def test_configured_requirements_reject_invalid_hiring_without_partial_write(self):
        self.grant_transition()
        candidate, _event = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.interview_a,
            actor=self.user,
        )
        event_count = CandidateStageTransition.objects.count()

        with self.assertRaises(ValidationError) as caught:
            transition_candidate(
                candidate=candidate,
                target_stage=self.hired_a,
                actor=self.user,
            )

        self.assertIn("joining_date", caught.exception.message_dict)
        candidate.refresh_from_db()
        self.assertEqual(candidate.stage_id, self.interview_a)
        self.assertEqual(CandidateStageTransition.objects.count(), event_count)

    def test_reasoned_cancellation_keeps_the_configured_target_stage(self):
        self.grant_transition()
        with self.assertRaises(ValidationError):
            transition_candidate(
                candidate=self.candidate_a,
                target_stage=self.cancelled_a_secondary,
                actor=self.user,
            )

        candidate, event = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.cancelled_a_secondary,
            actor=self.user,
            reason="Candidate withdrew after review.",
        )

        self.assertTrue(candidate.canceled)
        self.assertEqual(candidate.stage_id, self.cancelled_a_secondary)
        self.assertEqual(event.to_stage, self.cancelled_a_secondary)

    def test_authorized_override_requires_reason_and_keeps_reason_out_of_person_timeline(self):
        self.grant_transition(history=True, override=True)
        secret_reason = "PRIVATE DECISION DETAIL 2026"

        candidate, event = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.hired_a,
            actor=self.user,
            reason=secret_reason,
            override=True,
        )
        items = person_timeline_for_user(user=self.user, person=self.person_a)
        timeline_event = next(
            item
            for item in items
            if item.source_key
            == f"hydra_people.candidatestagetransition:{event.pk}"
        )

        self.assertEqual(candidate.stage_id, self.hired_a)
        self.assertTrue(candidate.hired)
        self.assertTrue(event.override)
        self.assertEqual(event.reason, secret_reason)
        self.assertIn("Initial", str(timeline_event.detail))
        self.assertIn("Hired A", str(timeline_event.detail))
        self.assertNotIn(secret_reason, str(timeline_event.detail))

    def test_missing_permission_and_cross_scope_are_denied(self):
        self.grant_read()
        with self.assertRaises(PermissionDenied):
            transition_candidate(
                candidate=self.candidate_a,
                target_stage=self.interview_a,
                actor=self.user,
            )

        self.grant(("recruitment", "change_candidate"))
        with self.assertRaises(PermissionDenied):
            transition_candidate(
                candidate=self.candidate_b,
                target_stage=self.interview_b,
                actor=self.user,
            )

    def test_cross_recruitment_and_disabled_rule_are_rejected(self):
        self.grant_transition()
        with self.assertRaises(ValidationError):
            transition_candidate(
                candidate=self.candidate_a,
                target_stage=self.interview_b,
                actor=self.user,
            )

        rule = RecruitmentStageTransitionRule.objects.get(
            from_stage=self.stage_a,
            to_stage=self.interview_a,
        )
        rule.is_active = False
        rule.save(update_fields=("is_active",))
        with self.assertRaises(ValidationError) as caught:
            transition_candidate(
                candidate=self.candidate_a,
                target_stage=self.interview_a,
                actor=self.user,
            )
        self.assertIn("not enabled", str(caught.exception))

    def test_direct_save_and_bulk_update_cannot_bypass_controlled_service(self):
        candidate = Candidate._base_manager.get(pk=self.candidate_a.pk)
        candidate.stage_id = self.interview_a
        with self.assertRaises(ValidationError):
            candidate.save()

        with self.assertRaises(ValidationError):
            Candidate._base_manager.filter(pk=self.candidate_a.pk).update(
                stage_id=self.interview_a
            )
        self.candidate_a.refresh_from_db()
        self.assertEqual(self.candidate_a.stage_id, self.stage_a)
        self.assertFalse(
            CandidateStageTransition.objects.filter(candidate=self.candidate_a).exists()
        )

    def test_hydra_transition_ui_is_scoped_and_renders_history(self):
        self.grant_transition(history=True)
        self.login()
        url = reverse("hydra-recruitment-transition", args=(self.candidate_a.pk,))

        form_response = self.client.get(url)
        denied = self.client.get(
            reverse("hydra-recruitment-transition", args=(self.candidate_b.pk,))
        )
        saved = self.client.post(
            url,
            {
                "target_stage": self.interview_a.pk,
                "reason": "",
                "schedule_date": "",
                "joining_date": "",
            },
        )
        detail = self.client.get(
            reverse("hydra-recruitment-detail", args=(self.candidate_a.pk,))
        )

        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, self.interview_a.stage)
        self.assertNotContains(form_response, self.interview_b.stage)
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(saved.status_code, 302)
        self.assertContains(detail, "Stage history")
        self.assertContains(detail, "Initial")
        self.assertContains(detail, "Interview A")
        self.assertContains(detail, 'class="hydra-timeline"')

    def test_legacy_pipeline_route_uses_same_transition_service(self):
        self.client.force_login(self.admin)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

        response = self.client.post(
            reverse("candidate-stage-update", args=(self.candidate_a.pk,)),
            {"stageId": self.interview_a.pk},
        )

        self.assertEqual(response.status_code, 200)
        event = CandidateStageTransition.objects.get(candidate=self.candidate_a)
        self.assertEqual(
            event.source,
            CandidateStageTransition.Source.HYDRA_PIPELINE,
        )
        self.assertEqual(event.to_stage, self.interview_a)

    def test_hired_transition_accepts_joining_date_without_override(self):
        self.grant_transition()
        candidate, _event = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.interview_a,
            actor=self.user,
        )

        candidate, event = transition_candidate(
            candidate=candidate,
            target_stage=self.hired_a,
            actor=self.user,
            joining_date=date(2026, 8, 3),
        )

        self.assertEqual(candidate.joining_date, date(2026, 8, 3))
        self.assertFalse(event.override)
