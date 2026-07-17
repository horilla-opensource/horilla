from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from hydra_onboarding.forms import (
    CourseAssignmentRuleForm,
    CourseConfirmationForm,
    CourseForm,
    CourseVersionForm,
    LessonForm,
    ManualCourseAssignmentForm,
    QuizAttemptForm,
    QuizForm,
    QuizOptionForm,
    QuizQuestionForm,
)
from hydra_onboarding.models import (
    CourseAssignment,
    CourseVersion,
    Lesson,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
)
from hydra_onboarding.selectors import (
    ONBOARDING_VIEW_PERMISSIONS,
    assignment_events_for_user,
    assignment_for_user,
    assignments_for_user,
    course_for_user,
    course_version_for_user,
    courses_for_user,
    rules_for_user,
)
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
    start_course_assignment,
    submit_quiz_attempt,
)
from hydra_people.selectors import person_for_user


def _add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error(None, error)


@login_required
@permission_required(ONBOARDING_VIEW_PERMISSIONS, raise_exception=True)
def onboarding_dashboard(request):
    query = " ".join(request.GET.get("q", "").split())
    courses = courses_for_user(user=request.user)
    assignments = assignments_for_user(user=request.user)
    rules = rules_for_user(user=request.user)
    if query:
        courses = courses.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(description__icontains=query)
        )
        assignments = assignments.filter(
            Q(person__hydra_id__icontains=query)
            | Q(person__passport_name__icontains=query)
            | Q(course__code__icontains=query)
            | Q(course__name__icontains=query)
        )
    return render(
        request,
        "hydra_onboarding/dashboard.html",
        {
            "query": query,
            "courses": courses.prefetch_related("versions")[:100],
            "rules": rules[:100],
            "assignments": assignments[:100],
            "course_count": courses.count(),
            "rule_count": rules.filter(is_active=True).count(),
            "open_assignment_count": assignments.exclude(
                status=CourseAssignment.Status.COMPLETED
            ).count(),
        },
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.add_course",),
    raise_exception=True,
)
def course_create(request):
    form = CourseForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            course = save_course(course=form.save(commit=False), actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Course created."))
            return redirect(course)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {"form": form, "page_title": _("Create onboarding course")},
    )


@login_required
@permission_required(ONBOARDING_VIEW_PERMISSIONS, raise_exception=True)
def course_detail(request, course_uuid):
    course = course_for_user(user=request.user, course_uuid=course_uuid)
    versions = (
        CourseVersion._base_manager.filter(course=course)
        .select_related("published_by")
        .order_by("language", "-version_number", "pk")
    )
    return render(
        request,
        "hydra_onboarding/course_detail.html",
        {
            "course": course,
            "versions": versions,
            "rules": rules_for_user(user=request.user).filter(course=course),
        },
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.add_courseversion",),
    raise_exception=True,
)
def version_create(request, course_uuid):
    course = course_for_user(user=request.user, course_uuid=course_uuid)
    form = CourseVersionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            version = create_draft_version(
                course_uuid=course.uuid,
                actor=request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Draft course version created."))
            return redirect(version)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {
            "form": form,
            "page_title": _("Create course version"),
            "cancel_url": course.get_absolute_url(),
        },
    )


@login_required
@permission_required(ONBOARDING_VIEW_PERMISSIONS, raise_exception=True)
def version_detail(request, version_uuid):
    version = course_version_for_user(user=request.user, version_uuid=version_uuid)
    lessons = Lesson._base_manager.filter(course_version=version).order_by(
        "sequence", "pk"
    )
    try:
        quiz = (
            Quiz._base_manager.filter(course_version=version)
            .prefetch_related(
                Prefetch(
                    "questions",
                    queryset=QuizQuestion._base_manager.prefetch_related(
                        Prefetch(
                            "options",
                            queryset=QuizOption._base_manager.order_by("sequence", "pk"),
                        )
                    ).order_by("sequence", "pk"),
                )
            )
            .get()
        )
    except Quiz.DoesNotExist:
        quiz = None
    return render(
        request,
        "hydra_onboarding/version_detail.html",
        {"version": version, "lessons": lessons, "quiz": quiz},
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.add_lesson",),
    raise_exception=True,
)
def lesson_create(request, version_uuid):
    version = course_version_for_user(user=request.user, version_uuid=version_uuid)
    form = LessonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            save_lesson(
                lesson=form.save(commit=False),
                version_uuid=version.uuid,
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Lesson added."))
            return redirect(version)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {
            "form": form,
            "page_title": _("Add lesson"),
            "cancel_url": version.get_absolute_url(),
        },
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.add_quiz",),
    raise_exception=True,
)
def quiz_create(request, version_uuid):
    version = course_version_for_user(user=request.user, version_uuid=version_uuid)
    form = QuizForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            save_quiz(
                quiz=form.save(commit=False),
                version_uuid=version.uuid,
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Quiz added."))
            return redirect(version)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {
            "form": form,
            "page_title": _("Add quiz"),
            "cancel_url": version.get_absolute_url(),
        },
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.add_quizquestion",),
    raise_exception=True,
)
def question_create(request, quiz_uuid):
    form = QuizQuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            question = save_question(
                question=form.save(commit=False),
                quiz_uuid=quiz_uuid,
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Quiz question added."))
            return redirect(question.quiz.course_version)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {"form": form, "page_title": _("Add quiz question")},
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.add_quizoption",),
    raise_exception=True,
)
def option_create(request, question_uuid):
    form = QuizOptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            option = save_option(
                option=form.save(commit=False),
                question_uuid=question_uuid,
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Quiz option added."))
            return redirect(option.question.quiz.course_version)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {"form": form, "page_title": _("Add answer option")},
    )


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS + ("hydra_onboarding.publish_courseversion",),
    raise_exception=True,
)
@require_POST
def version_publish(request, version_uuid):
    try:
        version = publish_course_version(version_uuid=version_uuid, actor=request.user)
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect("hydra-onboarding-version-detail", version_uuid=version_uuid)
    messages.success(request, _("Course version published and locked."))
    return redirect(version)


@login_required
@permission_required(
    ONBOARDING_VIEW_PERMISSIONS
    + (
        "hydra_onboarding.view_courseassignmentrule",
        "hydra_onboarding.add_courseassignmentrule",
    ),
    raise_exception=True,
)
def rule_create(request):
    form = CourseAssignmentRuleForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            rule = save_assignment_rule(rule=form.save(commit=False), actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Automatic assignment rule created."))
            return redirect(rule.course)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {"form": form, "page_title": _("Create automatic course rule")},
    )


@login_required
@permission_required(
    ("hydra_people.view_person", "hydra_onboarding.assign_course")
    + ONBOARDING_VIEW_PERMISSIONS,
    raise_exception=True,
)
def person_course_assign(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    form = ManualCourseAssignmentForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            assignment = assign_course_manually(
                actor=request.user,
                person_uuid=person.uuid,
                version_uuid=form.cleaned_data["course_version"].uuid,
                due_at=form.cleaned_data["due_at"],
                request_key=form.cleaned_data["request_key"],
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Course assigned."))
            return redirect(assignment)
    return render(
        request,
        "hydra_onboarding/model_form.html",
        {
            "form": form,
            "page_title": _("Assign course to %(person)s") % {"person": person.passport_name},
            "cancel_url": person.get_absolute_url(),
        },
    )


@login_required
@permission_required(
    ("hydra_people.view_person", "hydra_onboarding.assign_course")
    + ONBOARDING_VIEW_PERMISSIONS,
    raise_exception=True,
)
@require_POST
def person_apply_rules(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    result = apply_course_rules_for_person(person=person)
    messages.success(
        request,
        _("Rules matched %(matched)s course(s); %(created)s assignment(s) created.")
        % {"matched": result.matched_rules, "created": result.created_assignments},
    )
    return redirect(person)


@login_required
@permission_required("hydra_onboarding.view_courseassignment", raise_exception=True)
def assignment_detail(request, assignment_uuid):
    assignment = assignment_for_user(
        user=request.user,
        assignment_uuid=assignment_uuid,
    )
    lessons = Lesson._base_manager.filter(
        course_version=assignment.course_version
    ).order_by("sequence", "pk")
    attempts = QuizAttempt._base_manager.filter(assignment=assignment).select_related(
        "submitted_by"
    )
    return render(
        request,
        "hydra_onboarding/assignment_detail.html",
        {
            "assignment": assignment,
            "lessons": lessons,
            "attempts": attempts,
            "events": assignment_events_for_user(user=request.user).filter(
                assignment=assignment
            ),
        },
    )


@login_required
@permission_required(
    (
        "hydra_onboarding.view_courseassignment",
        "hydra_onboarding.start_courseassignment",
    ),
    raise_exception=True,
)
@require_POST
def assignment_start(request, assignment_uuid):
    try:
        assignment = start_course_assignment(
            actor=request.user,
            assignment_uuid=assignment_uuid,
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect("hydra-onboarding-assignment-detail", assignment_uuid=assignment_uuid)
    messages.success(request, _("Course started."))
    return redirect(assignment)


@login_required
@permission_required(
    (
        "hydra_onboarding.view_courseassignment",
        "hydra_onboarding.submit_quizattempt",
    ),
    raise_exception=True,
)
def assignment_quiz(request, assignment_uuid):
    assignment = assignment_for_user(user=request.user, assignment_uuid=assignment_uuid)
    try:
        quiz = Quiz._base_manager.prefetch_related("questions__options").get(
            course_version=assignment.course_version
        )
    except Quiz.DoesNotExist:
        messages.error(request, _("This assignment has no quiz."))
        return redirect(assignment)
    form = QuizAttemptForm(request.POST or None, quiz=quiz)
    if request.method == "POST" and form.is_valid():
        try:
            attempt = submit_quiz_attempt(
                actor=request.user,
                assignment_uuid=assignment.uuid,
                answers=form.answers,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if attempt.passed:
                messages.success(request, _("Quiz passed with %(score)s%%.") % {"score": attempt.score})
            else:
                messages.warning(request, _("Quiz score: %(score)s%%.") % {"score": attempt.score})
            return redirect(assignment)
    return render(
        request,
        "hydra_onboarding/quiz_form.html",
        {"form": form, "assignment": assignment, "quiz": quiz},
    )


@login_required
@permission_required(
    (
        "hydra_onboarding.view_courseassignment",
        "hydra_onboarding.confirm_courseassignment",
    ),
    raise_exception=True,
)
def assignment_confirm(request, assignment_uuid):
    assignment = assignment_for_user(user=request.user, assignment_uuid=assignment_uuid)
    form = CourseConfirmationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            confirm_course_assignment(
                actor=request.user,
                assignment_uuid=assignment.uuid,
                statement=form.cleaned_data["statement"],
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Course completion confirmed."))
            return redirect(assignment)
    return render(
        request,
        "hydra_onboarding/confirmation_form.html",
        {"form": form, "assignment": assignment},
    )
