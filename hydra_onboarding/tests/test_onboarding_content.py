from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from django.db.models import QuerySet

from hydra_arrivals.tests.test_onboarding_handoff import OnboardingHandoffTestCase
from hydra_onboarding.models import (
    Course,
    CourseAssignment,
    CourseAssignmentEvent,
    CourseAssignmentRule,
    CourseConfirmation,
    CourseVersion,
    Lesson,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
)
from hydra_onboarding.selectors import assignments_for_user, courses_for_user
from hydra_onboarding.services import (
    apply_course_rules_for_person,
    assign_course_manually,
    confirm_course_assignment,
    create_draft_version,
    publish_course_version,
    save_assignment_rule,
    save_course,
    save_lesson,
    save_option,
    save_question,
    save_quiz,
    submit_quiz_attempt,
)
from hydra_people.models import Person
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from hydra_ops.readiness import domain_integrity_results


READ_PERMISSIONS = (
    ("hydra_onboarding", "view_course"),
    ("hydra_onboarding", "view_courseversion"),
    ("hydra_onboarding", "view_courseassignment"),
    ("hydra_onboarding", "view_courseassignmentrule"),
    ("hydra_onboarding", "view_courseassignmentevent"),
    ("hydra_people", "view_person"),
)

WRITE_PERMISSIONS = READ_PERMISSIONS + (
    ("hydra_onboarding", "add_course"),
    ("hydra_onboarding", "add_courseversion"),
    ("hydra_onboarding", "publish_courseversion"),
    ("hydra_onboarding", "add_lesson"),
    ("hydra_onboarding", "add_quiz"),
    ("hydra_onboarding", "add_quizquestion"),
    ("hydra_onboarding", "add_quizoption"),
    ("hydra_onboarding", "add_courseassignmentrule"),
    ("hydra_onboarding", "assign_course"),
    ("hydra_onboarding", "start_courseassignment"),
    ("hydra_onboarding", "submit_quizattempt"),
    ("hydra_onboarding", "confirm_courseassignment"),
)


class HydraOnboardingContentTestCase(HydraRecruitmentTestCase):
    def grant_permissions(self, permissions=WRITE_PERMISSIONS):
        self.grant(*permissions)

    def make_course(self, *, company=None, code="SAFETY", default_language="uk"):
        return save_course(
            course=Course(
                company=company or self.company_a,
                code=code,
                name=f"{code} onboarding",
                description="Reviewed onboarding course",
                default_language=default_language,
            ),
            actor=self.admin,
        )

    def make_draft(self, *, course=None, language="uk", title="Safety basics"):
        return create_draft_version(
            course_uuid=(course or self.make_course()).uuid,
            language=language,
            title=title,
            summary="Scope-safe published content",
            actor=self.admin,
        )

    def add_lesson(self, version, *, sequence=1):
        return save_lesson(
            lesson=Lesson(
                sequence=sequence,
                title=f"Lesson {sequence}",
                body="Verified lesson content.",
                estimated_minutes=10,
                requires_confirmation=True,
            ),
            version_uuid=version.uuid,
            actor=self.admin,
        )

    def add_quiz(self, version):
        quiz = save_quiz(
            quiz=Quiz(title="Safety check", passing_score=100, max_attempts=2),
            version_uuid=version.uuid,
            actor=self.admin,
        )
        question = save_question(
            question=QuizQuestion(sequence=1, prompt="Choose the safe answer."),
            quiz_uuid=quiz.uuid,
            actor=self.admin,
        )
        correct = save_option(
            option=QuizOption(sequence=1, label="Use required PPE", is_correct=True),
            question_uuid=question.uuid,
            actor=self.admin,
        )
        wrong = save_option(
            option=QuizOption(sequence=2, label="Ignore the procedure", is_correct=False),
            question_uuid=question.uuid,
            actor=self.admin,
        )
        return quiz, question, correct, wrong

    def make_published(self, *, course=None, language="uk", with_quiz=False):
        version = self.make_draft(course=course, language=language)
        lesson = self.add_lesson(version)
        quiz_rows = self.add_quiz(version) if with_quiz else None
        version = publish_course_version(version_uuid=version.uuid, actor=self.admin)
        return version, lesson, quiz_rows


class CoursePublicationTests(HydraOnboardingContentTestCase):
    def test_published_version_and_nested_content_are_immutable(self):
        version, lesson, _quiz = self.make_published()

        self.assertEqual(len(version.content_fingerprint), 64)
        lesson.body = "Rewritten after publication"
        with self.assertRaisesMessage(TypeError, "immutable"):
            lesson.save()
        version.title = "Rewritten title"
        with self.assertRaisesMessage(TypeError, "immutable"):
            version.save(service_update=True)

    def test_publication_requires_a_lesson(self):
        version = self.make_draft()

        with self.assertRaisesMessage(ValidationError, "at least one lesson"):
            publish_course_version(version_uuid=version.uuid, actor=self.admin)

        version.refresh_from_db()
        self.assertEqual(version.status, CourseVersion.Status.DRAFT)

    def test_publication_rejects_ambiguous_quiz_answers(self):
        version = self.make_draft()
        self.add_lesson(version)
        _quiz, question, _correct, wrong = self.add_quiz(version)
        wrong.is_correct = True
        wrong.save()

        with self.assertRaisesMessage(ValidationError, "exactly one correct"):
            publish_course_version(version_uuid=version.uuid, actor=self.admin)

    def test_new_language_versions_receive_independent_monotonic_numbers(self):
        course = self.make_course()
        first_uk = self.make_draft(course=course, language="uk", title="UK first")
        second_uk = self.make_draft(course=course, language="uk", title="UK second")
        first_pl = self.make_draft(course=course, language="pl", title="PL first")

        self.assertEqual((first_uk.version_number, second_uk.version_number), (1, 2))
        self.assertEqual(first_pl.version_number, 1)


class CourseRuleTests(HydraOnboardingContentTestCase):
    def test_fixed_dimension_rule_assigns_once_with_snapshot_and_due_date(self):
        version, _lesson, _quiz = self.make_published()
        rule = save_assignment_rule(
            rule=CourseAssignmentRule(
                company=self.company_a,
                course=version.course,
                location=self.team_a.section.location,
                department=self.department_a,
                team=self.team_a,
                language=Person.PreferredLanguage.UKRAINIAN,
                priority=200,
                due_days=7,
            ),
            actor=self.admin,
        )

        first = apply_course_rules_for_person(person=self.person_a)
        second = apply_course_rules_for_person(person=self.person_a)

        self.assertEqual((first.matched_rules, first.created_assignments), (1, 1))
        self.assertEqual((second.created_assignments, second.existing_assignments), (0, 1))
        assignment = CourseAssignment.objects.get(person=self.person_a)
        self.assertEqual(assignment.rule, rule)
        self.assertEqual(assignment.due_at, timezone.localdate() + timedelta(days=7))
        self.assertEqual(
            assignment.assignment_snapshot["content_fingerprint"],
            version.content_fingerprint,
        )
        event = assignment.events.get()
        self.assertEqual(event.source, CourseAssignmentEvent.Source.SYSTEM)
        self.assertIsNone(event.actor)

    def test_wrong_language_and_foreign_team_do_not_match(self):
        version, _lesson, _quiz = self.make_published()
        for team, language in (
            (self.team_b, "uk"),
            (self.team_a, "pl"),
        ):
            save_assignment_rule(
                rule=CourseAssignmentRule(
                    company=team.section.location.company,
                    course=(
                        version.course
                        if team == self.team_a
                        else self.make_course(company=self.company_b, code="REMOTE")
                    ),
                    team=team,
                    language=language,
                ),
                actor=self.admin,
            )

        result = apply_course_rules_for_person(person=self.person_a)

        self.assertEqual(result.matched_rules, 0)
        self.assertFalse(CourseAssignment.objects.exists())

    def test_person_language_falls_back_to_course_default_published_version(self):
        course = self.make_course(default_language="pl")
        version, _lesson, _quiz = self.make_published(course=course, language="pl")
        save_assignment_rule(
            rule=CourseAssignmentRule(
                company=self.company_a,
                course=course,
                team=self.team_a,
                language="",
            ),
            actor=self.admin,
        )

        result = apply_course_rules_for_person(person=self.person_a)

        self.assertEqual(result.created_assignments, 1)
        self.assertEqual(CourseAssignment.objects.get().course_version, version)

    def test_more_specific_higher_priority_rule_wins_for_the_same_course(self):
        version, _lesson, _quiz = self.make_published()
        generic = save_assignment_rule(
            rule=CourseAssignmentRule(
                company=self.company_a,
                course=version.course,
                priority=100,
            ),
            actor=self.admin,
        )
        specific = save_assignment_rule(
            rule=CourseAssignmentRule(
                company=self.company_a,
                course=version.course,
                priority=200,
                team=self.team_a,
            ),
            actor=self.admin,
        )

        apply_course_rules_for_person(person=self.person_a)

        assignment = CourseAssignment.objects.get()
        self.assertEqual(assignment.rule, specific)
        self.assertNotEqual(assignment.rule, generic)


class CourseCompletionTests(HydraOnboardingContentTestCase):
    def setUp(self):
        super().setUp()
        self.grant_permissions()
        self.version, _lesson, quiz_rows = self.make_published(with_quiz=True)
        self.quiz, self.question, self.correct, self.wrong = quiz_rows
        self.assignment = assign_course_manually(
            actor=self.user,
            person_uuid=self.person_a.uuid,
            version_uuid=self.version.uuid,
            request_key=uuid4(),
        )

    def test_passed_quiz_then_confirmation_complete_with_append_only_sequence(self):
        attempt = submit_quiz_attempt(
            actor=self.user,
            assignment_uuid=self.assignment.uuid,
            answers={str(self.question.uuid): str(self.correct.uuid)},
        )
        confirmation = confirm_course_assignment(
            actor=self.user,
            assignment_uuid=self.assignment.uuid,
            statement="Safety course reviewed and completed",
        )

        self.assignment.refresh_from_db()
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.score, 100)
        self.assertEqual(self.assignment.status, CourseAssignment.Status.COMPLETED)
        self.assertEqual(
            list(self.assignment.events.values_list("sequence", "action")),
            [
                (1, CourseAssignmentEvent.Action.ASSIGNED),
                (2, CourseAssignmentEvent.Action.STARTED),
                (3, CourseAssignmentEvent.Action.QUIZ_SUBMITTED),
                (4, CourseAssignmentEvent.Action.COMPLETED),
            ],
        )
        self.assertEqual(
            confirmation.statement_snapshot["content_fingerprint"],
            self.version.content_fingerprint,
        )
        with self.assertRaises(TypeError):
            QuizAttempt.objects.filter(pk=attempt.pk).update(score=0)
        with self.assertRaises(TypeError):
            CourseConfirmation.objects.filter(pk=confirmation.pk).delete()

    def test_confirmation_requires_a_passed_quiz(self):
        submit_quiz_attempt(
            actor=self.user,
            assignment_uuid=self.assignment.uuid,
            answers={str(self.question.uuid): str(self.wrong.uuid)},
        )

        with self.assertRaisesMessage(ValidationError, "Pass the quiz"):
            confirm_course_assignment(
                actor=self.user,
                assignment_uuid=self.assignment.uuid,
                statement="Attempted but not passed",
            )

    def test_maximum_quiz_attempts_is_enforced(self):
        for _index in range(2):
            submit_quiz_attempt(
                actor=self.user,
                assignment_uuid=self.assignment.uuid,
                answers={str(self.question.uuid): str(self.wrong.uuid)},
            )

        with self.assertRaisesMessage(ValidationError, "maximum number"):
            submit_quiz_attempt(
                actor=self.user,
                assignment_uuid=self.assignment.uuid,
                answers={str(self.question.uuid): str(self.correct.uuid)},
            )


class OnboardingScopeAndUiTests(HydraOnboardingContentTestCase):
    def setUp(self):
        super().setUp()
        self.grant_permissions()

    def test_cross_scope_courses_assignments_and_direct_urls_are_hidden(self):
        remote_course = self.make_course(company=self.company_b, code="REMOTE")
        remote_version, _lesson, _quiz = self.make_published(
            course=remote_course,
            language="uk",
        )
        assign_course_manually(
            actor=self.admin,
            person_uuid=self.person_b.uuid,
            version_uuid=remote_version.uuid,
            request_key=uuid4(),
        )
        self.login()

        self.assertFalse(courses_for_user(user=self.user).filter(pk=remote_course.pk).exists())
        self.assertFalse(assignments_for_user(user=self.user).filter(person=self.person_b).exists())
        self.assertEqual(
            self.client.get(remote_course.get_absolute_url()).status_code,
            404,
        )

    def test_operator_ui_creates_course_version_and_lesson(self):
        self.login()
        course_response = self.client.post(
            reverse("hydra-onboarding-course-create"),
            {
                "company": self.company_a.pk,
                "code": "WELCOME",
                "name": "Welcome course",
                "description": "First day content",
                "default_language": "uk",
            },
        )
        course = Course.objects.get(code="WELCOME")
        version_response = self.client.post(
            reverse("hydra-onboarding-version-create", args=(course.uuid,)),
            {"language": "uk", "title": "Welcome", "summary": "Day one"},
        )
        version = CourseVersion.objects.get(course=course)
        lesson_response = self.client.post(
            reverse("hydra-onboarding-lesson-create", args=(version.uuid,)),
            {
                "sequence": 1,
                "title": "Arrival",
                "body": "Meet the coordinator.",
                "estimated_minutes": 5,
                "requires_confirmation": "on",
            },
        )

        self.assertEqual(course_response.status_code, 302)
        self.assertEqual(version_response.status_code, 302)
        self.assertEqual(lesson_response.status_code, 302)
        self.assertTrue(Lesson.objects.filter(course_version=version).exists())

    def test_person_detail_renders_assigned_version_and_actions(self):
        version, _lesson, _quiz = self.make_published()
        assignment = assign_course_manually(
            actor=self.user,
            person_uuid=self.person_a.uuid,
            version_uuid=version.uuid,
            request_key=uuid4(),
        )
        self.login()

        response = self.client.get(self.person_a.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onboarding courses")
        self.assertContains(response, assignment.get_absolute_url())
        self.assertContains(
            response,
            reverse("hydra-onboarding-person-apply-rules", args=(self.person_a.uuid,)),
        )


class OnboardingReadinessTests(HydraOnboardingContentTestCase):
    def _result_map(self):
        return {
            result.name: result
            for result in domain_integrity_results()
            if result.name.startswith("onboarding_")
        }

    def test_readiness_accepts_consistent_published_content_and_assignment(self):
        self.grant_permissions()
        version, _lesson, _quiz = self.make_published()
        assign_course_manually(
            actor=self.user,
            person_uuid=self.person_a.uuid,
            version_uuid=version.uuid,
            request_key=uuid4(),
        )

        results = self._result_map()

        self.assertEqual(
            set(results),
            {
                "onboarding_published_content",
                "onboarding_assignment_rules",
                "onboarding_assignment_snapshots",
                "onboarding_completion_evidence",
            },
        )
        self.assertTrue(all(result.ok for result in results.values()))

    def test_readiness_detects_direct_content_and_snapshot_corruption(self):
        self.grant_permissions()
        version, lesson, _quiz = self.make_published()
        assignment = assign_course_manually(
            actor=self.user,
            person_uuid=self.person_a.uuid,
            version_uuid=version.uuid,
            request_key=uuid4(),
        )
        QuerySet(model=Lesson, using="default").filter(pk=lesson.pk).update(
            body="Direct database rewrite"
        )
        QuerySet(model=CourseAssignment, using="default").filter(
            pk=assignment.pk
        ).update(assignment_snapshot={"invalid": True})

        results = self._result_map()

        self.assertFalse(results["onboarding_published_content"].ok)
        self.assertFalse(results["onboarding_assignment_snapshots"].ok)


class OnboardingRuleHandoffIntegrationTests(OnboardingHandoffTestCase):
    def test_confirmed_arrival_handoff_applies_location_language_rule(self):
        course = save_course(
            course=Course(
                company=self.company_a,
                code="ARRIVAL",
                name="Arrival course",
                default_language="uk",
            ),
            actor=self.admin,
        )
        version = create_draft_version(
            course_uuid=course.uuid,
            language="uk",
            title="Arrival at work",
            summary="Arrival content",
            actor=self.admin,
        )
        save_lesson(
            lesson=Lesson(
                sequence=1,
                title="Meet the team",
                body="Follow the location induction procedure.",
            ),
            version_uuid=version.uuid,
            actor=self.admin,
        )
        version = publish_course_version(version_uuid=version.uuid, actor=self.admin)
        save_assignment_rule(
            rule=CourseAssignmentRule(
                company=self.company_a,
                course=course,
                location=self.location_a,
                language="uk",
            ),
            actor=self.admin,
        )
        plan = self.confirmed_plan()
        self.grant_handoff_start()

        from hydra_arrivals.onboarding import start_onboarding_handoff

        start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        assignment = CourseAssignment.objects.get(person=self.person_a, course=course)
        self.assertEqual(assignment.course_version, version)
        self.assertEqual(assignment.source, CourseAssignment.Source.RULE)
