import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_coordination.models import PersonAssignment
from hydra_coordination.selectors import company_ids_for_user, grant_covers_target
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
from hydra_onboarding.selectors import (
    assignment_for_user,
    course_for_user,
    course_version_for_user,
)
from hydra_people.identity import ensure_canonical_person
from hydra_people.models import Person
from hydra_people.selectors import person_for_user


def _require(actor, *permissions):
    if actor is None or not actor.is_authenticated or not actor.has_perms(permissions):
        raise PermissionDenied


def _clean_text(value, *, field, maximum, required=True):
    value = " ".join(str(value or "").split())
    if required and not value:
        raise ValidationError({field: _("This field is required.")})
    if len(value) > maximum:
        raise ValidationError(
            {field: _("Ensure this value has at most %(limit)s characters.") % {"limit": maximum}}
        )
    return value


def _request_uuid(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as error:
        raise ValidationError({"request_key": _("Invalid request key.")}) from error


@transaction.atomic
def save_course(*, course, actor):
    permission = "change_course" if course.pk else "add_course"
    _require(actor, f"hydra_onboarding.{permission}")
    if course.company_id not in company_ids_for_user(user=actor):
        raise PermissionDenied
    course.created_by = course.created_by or actor
    course.modified_by = actor
    course.full_clean()
    course.save()
    return course


@transaction.atomic
def create_draft_version(*, course_uuid, language, title, summary, actor):
    _require(actor, "hydra_onboarding.add_courseversion")
    visible_course = course_for_user(user=actor, course_uuid=course_uuid)
    course = Course._base_manager.select_for_update().get(pk=visible_course.pk)
    next_number = (
        CourseVersion._base_manager.filter(course=course, language=language).aggregate(
            maximum=Max("version_number")
        )["maximum"]
        or 0
    ) + 1
    version = CourseVersion(
        course=course,
        version_number=next_number,
        language=language,
        title=_clean_text(title, field="title", maximum=180),
        summary=str(summary or "").strip(),
        created_by=actor,
        modified_by=actor,
    )
    version.full_clean()
    version.save(force_insert=True)
    return version


def _locked_draft(*, actor, version_uuid, permission):
    _require(actor, f"hydra_onboarding.{permission}")
    visible = course_version_for_user(user=actor, version_uuid=version_uuid)
    version = CourseVersion._base_manager.select_for_update().get(pk=visible.pk)
    if version.status != CourseVersion.Status.DRAFT:
        raise ValidationError(_("Published course content is immutable."))
    return version


@transaction.atomic
def save_lesson(*, lesson, version_uuid, actor):
    permission = "change_lesson" if lesson.pk else "add_lesson"
    version = _locked_draft(actor=actor, version_uuid=version_uuid, permission=permission)
    if lesson.pk and lesson.course_version_id != version.pk:
        raise ValidationError({"course_version": _("Lesson belongs to another version.")})
    lesson.course_version = version
    lesson.full_clean()
    lesson.save()
    return lesson


@transaction.atomic
def save_quiz(*, quiz, version_uuid, actor):
    permission = "change_quiz" if quiz.pk else "add_quiz"
    version = _locked_draft(actor=actor, version_uuid=version_uuid, permission=permission)
    if quiz.pk and quiz.course_version_id != version.pk:
        raise ValidationError({"course_version": _("Quiz belongs to another version.")})
    if not quiz.pk and Quiz._base_manager.filter(course_version=version).exists():
        raise ValidationError(_("This version already has a quiz."))
    quiz.course_version = version
    quiz.full_clean()
    quiz.save()
    return quiz


@transaction.atomic
def save_question(*, question, quiz_uuid, actor):
    _require(
        actor,
        f"hydra_onboarding.{'change_quizquestion' if question.pk else 'add_quizquestion'}",
    )
    quiz = (
        Quiz._base_manager.select_for_update()
        .select_related("course_version__course")
        .filter(
            uuid=quiz_uuid,
            course_version__course_id__in=Course._base_manager.filter(
                company_id__in=company_ids_for_user(user=actor)
            ).values("pk"),
        )
        .first()
    )
    if quiz is None:
        raise PermissionDenied
    if quiz.course_version.status != CourseVersion.Status.DRAFT:
        raise ValidationError(_("Published course content is immutable."))
    if question.pk and question.quiz_id != quiz.pk:
        raise ValidationError({"quiz": _("Question belongs to another quiz.")})
    question.quiz = quiz
    question.full_clean()
    question.save()
    return question


@transaction.atomic
def save_option(*, option, question_uuid, actor):
    _require(
        actor,
        f"hydra_onboarding.{'change_quizoption' if option.pk else 'add_quizoption'}",
    )
    question = (
        QuizQuestion._base_manager.select_for_update()
        .select_related("quiz__course_version__course")
        .filter(
            uuid=question_uuid,
            quiz__course_version__course_id__in=Course._base_manager.filter(
                company_id__in=company_ids_for_user(user=actor)
            ).values("pk"),
        )
        .first()
    )
    if question is None:
        raise PermissionDenied
    if question.quiz.course_version.status != CourseVersion.Status.DRAFT:
        raise ValidationError(_("Published course content is immutable."))
    if option.pk and option.question_id != question.pk:
        raise ValidationError({"question": _("Option belongs to another question.")})
    option.question = question
    option.full_clean()
    option.save()
    return option


def _version_payload(version):
    lessons = list(
        Lesson._base_manager.filter(course_version=version)
        .order_by("sequence", "pk")
        .values(
            "uuid",
            "sequence",
            "title",
            "body",
            "estimated_minutes",
            "requires_confirmation",
        )
    )
    try:
        quiz = Quiz._base_manager.get(course_version=version)
    except Quiz.DoesNotExist:
        quiz_payload = None
    else:
        questions = []
        for question in QuizQuestion._base_manager.filter(quiz=quiz).order_by(
            "sequence", "pk"
        ):
            questions.append(
                {
                    "uuid": str(question.uuid),
                    "sequence": question.sequence,
                    "prompt": question.prompt,
                    "options": [
                        {
                            "uuid": str(option.uuid),
                            "sequence": option.sequence,
                            "label": option.label,
                            "is_correct": option.is_correct,
                        }
                        for option in QuizOption._base_manager.filter(
                            question=question
                        ).order_by("sequence", "pk")
                    ],
                }
            )
        quiz_payload = {
            "uuid": str(quiz.uuid),
            "title": quiz.title,
            "passing_score": quiz.passing_score,
            "max_attempts": quiz.max_attempts,
            "questions": questions,
        }
    return {
        "course_uuid": str(version.course.uuid),
        "version_uuid": str(version.uuid),
        "version_number": version.version_number,
        "language": version.language,
        "title": version.title,
        "summary": version.summary,
        "lessons": [
            {**lesson, "uuid": str(lesson["uuid"])} for lesson in lessons
        ],
        "quiz": quiz_payload,
    }


def _validate_publishable(payload):
    if not payload["lessons"]:
        raise ValidationError(_("Add at least one lesson before publishing."))
    quiz = payload["quiz"]
    if quiz is None:
        return
    if not quiz["questions"]:
        raise ValidationError(_("A quiz requires at least one question."))
    for question in quiz["questions"]:
        if len(question["options"]) < 2:
            raise ValidationError(_("Every quiz question requires at least two options."))
        if sum(option["is_correct"] for option in question["options"]) != 1:
            raise ValidationError(_("Every quiz question requires exactly one correct option."))


def version_content_fingerprint(version):
    payload = _version_payload(version)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@transaction.atomic
def publish_course_version(*, version_uuid, actor):
    _require(actor, "hydra_onboarding.publish_courseversion")
    visible = course_version_for_user(user=actor, version_uuid=version_uuid)
    version = CourseVersion._base_manager.select_for_update().get(pk=visible.pk)
    if version.status == CourseVersion.Status.PUBLISHED:
        return version
    if version.status != CourseVersion.Status.DRAFT:
        raise ValidationError(_("Only a draft can be published."))
    payload = _version_payload(version)
    _validate_publishable(payload)
    version.status = CourseVersion.Status.PUBLISHED
    version.published_at = timezone.now()
    version.published_by = actor
    version.content_fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    version.modified_by = actor
    version.full_clean()
    version.save(
        service_update=True,
        update_fields=(
            "status",
            "published_at",
            "published_by",
            "content_fingerprint",
            "modified_by",
        ),
    )
    return version


@transaction.atomic
def save_assignment_rule(*, rule, actor):
    permission = "change_courseassignmentrule" if rule.pk else "add_courseassignmentrule"
    _require(actor, f"hydra_onboarding.{permission}")
    if rule.company_id not in company_ids_for_user(user=actor):
        raise PermissionDenied
    targets = (
        ("location", rule.location),
        ("department", rule.department),
        ("team", rule.team),
    )
    for field_name, target in targets:
        if target is not None and not grant_covers_target(
            user=actor,
            **{field_name: target},
        ):
            raise PermissionDenied
    rule.created_by = rule.created_by or actor
    rule.modified_by = actor
    rule.full_clean()
    rule.save()
    return rule


@dataclass(frozen=True, slots=True)
class RuleApplicationResult:
    matched_rules: int
    created_assignments: int
    existing_assignments: int


def _effective_context(*, person, day, handoff=None):
    assignment = (
        PersonAssignment._base_manager.filter(
            person=person,
            is_active=True,
            valid_from__lte=day,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .select_related("team__section__location__company", "department")
        .order_by("-is_primary", "-valid_from", "-pk")
        .first()
    )
    if assignment is not None:
        location = assignment.team.section.location
        department = assignment.department
        team = assignment.team
    elif handoff is not None:
        location = handoff.arrival.destination_location
        department = None
        team = None
    else:
        return None
    employee_type = None
    if person.employee_id:
        work_info = getattr(person.employee, "employee_work_info", None)
        employee_type = getattr(work_info, "employee_type_id", None)
    return {
        "company": location.company,
        "location": location,
        "department": department,
        "team": team,
        "language": person.preferred_language,
        "employee_type": employee_type,
    }


def _rule_matches(rule, context):
    return all(
        (
            rule.location_id is None or rule.location_id == context["location"].pk,
            rule.department_id is None
            or (
                context["department"] is not None
                and rule.department_id == context["department"].pk
            ),
            rule.team_id is None
            or (context["team"] is not None and rule.team_id == context["team"].pk),
            not rule.language or rule.language == context["language"],
            rule.employee_type_id is None
            or (
                context["employee_type"] is not None
                and rule.employee_type_id == context["employee_type"].pk
            ),
        )
    )


def _published_version_for_rule(rule, context):
    desired_language = rule.language or context["language"]
    queryset = CourseVersion._base_manager.filter(
        course=rule.course,
        status=CourseVersion.Status.PUBLISHED,
        is_active=True,
    )
    version = queryset.filter(language=desired_language).order_by(
        "-version_number", "-pk"
    ).first()
    if version is None and not rule.language and desired_language != rule.course.default_language:
        version = queryset.filter(language=rule.course.default_language).order_by(
            "-version_number", "-pk"
        ).first()
    return version


def _assignment_snapshot(*, person, version, rule, context, source):
    return {
        "source": source,
        "course_uuid": str(version.course.uuid),
        "course_version_uuid": str(version.uuid),
        "course_version": version.version_number,
        "language": version.language,
        "content_fingerprint": version.content_fingerprint,
        "rule_uuid": str(rule.uuid) if rule else None,
        "context": {
            "company_id": context["company"].pk if context else version.course.company_id,
            "location_id": context["location"].pk if context else None,
            "department_id": context["department"].pk if context and context["department"] else None,
            "team_id": context["team"].pk if context and context["team"] else None,
            "language": person.preferred_language,
            "employee_type_id": (
                context["employee_type"].pk
                if context and context["employee_type"]
                else None
            ),
        },
    }


def _create_event(*, assignment, action, actor=None, attempt=None, confirmation=None, details=None):
    return CourseAssignmentEvent.objects.create(
        assignment=assignment,
        sequence=assignment.version,
        action=action,
        source=(
            CourseAssignmentEvent.Source.USER
            if actor is not None
            else CourseAssignmentEvent.Source.SYSTEM
        ),
        actor=actor,
        quiz_attempt=attempt,
        confirmation=confirmation,
        details_snapshot=details or {},
    )


def _create_assignment(*, person, version, rule, context, actor, source, due_at, request_key=None):
    request_key = _request_uuid(request_key) if request_key else None
    if request_key:
        existing_request = CourseAssignment._base_manager.filter(
            request_key=request_key
        ).first()
        if existing_request is not None:
            if (
                existing_request.person_id == person.pk
                and existing_request.course_version_id == version.pk
                and existing_request.due_at == due_at
            ):
                return existing_request, False
            raise ValidationError(
                {"request_key": _("This request key was already used for different data.")}
            )
    existing = CourseAssignment._base_manager.filter(
        person=person,
        course=version.course,
    ).first()
    if existing is not None:
        return existing, False
    assignment = CourseAssignment(
        **({"request_key": request_key} if request_key else {}),
        company=version.course.company,
        person=person,
        course=version.course,
        course_version=version,
        rule=rule,
        source=source,
        assigned_by=actor,
        due_at=due_at,
        assignment_snapshot=_assignment_snapshot(
            person=person,
            version=version,
            rule=rule,
            context=context,
            source=source,
        ),
        created_by=actor,
        modified_by=actor,
    )
    assignment.full_clean()
    try:
        with transaction.atomic():
            assignment.save(force_insert=True)
    except IntegrityError:
        existing = CourseAssignment._base_manager.get(
            person=person,
            course=version.course,
        )
        return existing, False
    _create_event(
        assignment=assignment,
        action=CourseAssignmentEvent.Action.ASSIGNED,
        actor=actor,
        details={
            "source": source,
            "course_version_uuid": str(version.uuid),
            "rule_uuid": str(rule.uuid) if rule else None,
        },
    )
    return assignment, True


@transaction.atomic
def apply_course_rules_for_person(*, person, handoff=None, day=None):
    """Apply fixed-dimension rules idempotently; automatic events are system facts."""

    day = day or timezone.localdate()
    locked_person = Person._base_manager.select_related("employee").get(pk=person.pk)
    ensure_canonical_person(locked_person)
    context = _effective_context(person=locked_person, day=day, handoff=handoff)
    if context is None:
        return RuleApplicationResult(0, 0, 0)
    rules = list(
        CourseAssignmentRule._base_manager.filter(
            company=context["company"],
            is_active=True,
            course__is_active=True,
        ).select_related(
            "course",
            "location",
            "department",
            "team__section__location",
            "employee_type",
        )
    )
    matched = [rule for rule in rules if _rule_matches(rule, context)]
    selected = {}
    for rule in sorted(
        matched,
        key=lambda item: (-item.priority, -item.specificity, item.pk),
    ):
        selected.setdefault(rule.course_id, rule)
    created = 0
    existing = 0
    for rule in selected.values():
        version = _published_version_for_rule(rule, context)
        if version is None:
            continue
        due_at = day + timedelta(days=rule.due_days) if rule.due_days else None
        _assignment, was_created = _create_assignment(
            person=locked_person,
            version=version,
            rule=rule,
            context=context,
            actor=None,
            source=CourseAssignment.Source.RULE,
            due_at=due_at,
        )
        created += int(was_created)
        existing += int(not was_created)
    return RuleApplicationResult(len(selected), created, existing)


@transaction.atomic
def assign_course_manually(
    *, actor, person_uuid, version_uuid, due_at=None, request_key=None
):
    _require(actor, "hydra_onboarding.assign_course")
    person = person_for_user(user=actor, person_uuid=person_uuid)
    ensure_canonical_person(person)
    person = Person._base_manager.select_for_update().get(pk=person.pk)
    version = course_version_for_user(user=actor, version_uuid=version_uuid)
    version = CourseVersion._base_manager.select_for_update().get(pk=version.pk)
    if version.status != CourseVersion.Status.PUBLISHED:
        raise ValidationError({"course_version": _("Choose a published course version.")})
    return _create_assignment(
        person=person,
        version=version,
        rule=None,
        context=None,
        actor=actor,
        source=CourseAssignment.Source.MANUAL,
        due_at=due_at,
        request_key=request_key,
    )[0]


def _locked_visible_assignment(*, actor, assignment_uuid, permission):
    _require(actor, f"hydra_onboarding.{permission}")
    visible = assignment_for_user(user=actor, assignment_uuid=assignment_uuid)
    return CourseAssignment._base_manager.select_for_update().get(pk=visible.pk)


def _start_locked(*, assignment, actor):
    if assignment.status == CourseAssignment.Status.COMPLETED:
        raise ValidationError(_("A completed course cannot be restarted."))
    if assignment.status == CourseAssignment.Status.IN_PROGRESS:
        return assignment
    assignment.status = CourseAssignment.Status.IN_PROGRESS
    assignment.started_at = timezone.now()
    assignment.version += 1
    assignment.modified_by = actor
    assignment.full_clean()
    assignment.save(
        service_update=True,
        update_fields=("status", "started_at", "version", "modified_by"),
    )
    _create_event(
        assignment=assignment,
        action=CourseAssignmentEvent.Action.STARTED,
        actor=actor,
        details={"course_version_uuid": str(assignment.course_version.uuid)},
    )
    return assignment


@transaction.atomic
def start_course_assignment(*, actor, assignment_uuid):
    assignment = _locked_visible_assignment(
        actor=actor,
        assignment_uuid=assignment_uuid,
        permission="start_courseassignment",
    )
    return _start_locked(assignment=assignment, actor=actor)


@transaction.atomic
def submit_quiz_attempt(*, actor, assignment_uuid, answers):
    assignment = _locked_visible_assignment(
        actor=actor,
        assignment_uuid=assignment_uuid,
        permission="submit_quizattempt",
    )
    if assignment.status == CourseAssignment.Status.COMPLETED:
        raise ValidationError(_("The course is already completed."))
    assignment = _start_locked(assignment=assignment, actor=actor)
    try:
        quiz = Quiz._base_manager.select_related("course_version").get(
            course_version=assignment.course_version
        )
    except Quiz.DoesNotExist as error:
        raise ValidationError(_("This course version has no quiz.")) from error
    attempt_count = QuizAttempt._base_manager.filter(assignment=assignment).count()
    if attempt_count >= quiz.max_attempts:
        raise ValidationError(_("The maximum number of quiz attempts was reached."))
    questions = list(
        QuizQuestion._base_manager.filter(quiz=quiz)
        .prefetch_related("options")
        .order_by("sequence", "pk")
    )
    if not questions:
        raise ValidationError(_("The published quiz has no questions."))
    answer_rows = []
    correct = 0
    for question in questions:
        selected_uuid = str(answers.get(str(question.uuid), ""))
        options = {str(option.uuid): option for option in question.options.all()}
        selected = options.get(selected_uuid)
        if selected is None:
            raise ValidationError(
                {str(question.uuid): _("Answer every quiz question.")}
            )
        is_correct = bool(selected.is_correct)
        correct += int(is_correct)
        answer_rows.append(
            {
                "question_uuid": str(question.uuid),
                "selected_option_uuid": str(selected.uuid),
                "correct": is_correct,
            }
        )
    score = round(correct * 100 / len(questions))
    attempt = QuizAttempt(
        assignment=assignment,
        quiz=quiz,
        sequence=attempt_count + 1,
        score=score,
        passed=score >= quiz.passing_score,
        answers_snapshot=answer_rows,
        submitted_by=actor,
    )
    attempt.full_clean()
    attempt.save(force_insert=True)
    assignment.version += 1
    assignment.modified_by = actor
    assignment.save(
        service_update=True,
        update_fields=("version", "modified_by"),
    )
    _create_event(
        assignment=assignment,
        action=CourseAssignmentEvent.Action.QUIZ_SUBMITTED,
        actor=actor,
        attempt=attempt,
        details={"score": score, "passed": attempt.passed},
    )
    return attempt


@transaction.atomic
def confirm_course_assignment(*, actor, assignment_uuid, statement):
    assignment = _locked_visible_assignment(
        actor=actor,
        assignment_uuid=assignment_uuid,
        permission="confirm_courseassignment",
    )
    existing = CourseConfirmation._base_manager.filter(assignment=assignment).first()
    statement = _clean_text(statement, field="statement", maximum=500)
    if existing is not None:
        if existing.confirmed_by_id == actor.pk and existing.statement == statement:
            return existing
        raise ValidationError(_("This course already has a completion confirmation."))
    assignment = _start_locked(assignment=assignment, actor=actor)
    try:
        quiz = Quiz._base_manager.get(course_version=assignment.course_version)
    except Quiz.DoesNotExist:
        quiz = None
    if quiz is not None and not QuizAttempt._base_manager.filter(
        assignment=assignment,
        quiz=quiz,
        passed=True,
    ).exists():
        raise ValidationError(_("Pass the quiz before confirming course completion."))
    confirmation = CourseConfirmation(
        assignment=assignment,
        statement=statement,
        statement_snapshot={
            "course_version_uuid": str(assignment.course_version.uuid),
            "content_fingerprint": assignment.course_version.content_fingerprint,
            "statement": statement,
        },
        confirmed_by=actor,
    )
    confirmation.full_clean()
    confirmation.save(force_insert=True)
    assignment.status = CourseAssignment.Status.COMPLETED
    assignment.completed_at = confirmation.confirmed_at
    assignment.version += 1
    assignment.modified_by = actor
    assignment.full_clean()
    assignment.save(
        service_update=True,
        update_fields=("status", "completed_at", "version", "modified_by"),
    )
    _create_event(
        assignment=assignment,
        action=CourseAssignmentEvent.Action.COMPLETED,
        actor=actor,
        confirmation=confirmation,
        details={"content_fingerprint": assignment.course_version.content_fingerprint},
    )
    return confirmation
