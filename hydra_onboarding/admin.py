from django.contrib import admin

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
    assignment_events_for_user,
    assignments_for_user,
    course_versions_for_user,
    courses_for_user,
    rules_for_user,
)


class ScopedReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        model = self.model
        if model is Course:
            return courses_for_user(user=request.user)
        if model is CourseVersion:
            return course_versions_for_user(user=request.user)
        if model is CourseAssignmentRule:
            return rules_for_user(user=request.user)
        if model is CourseAssignment:
            return assignments_for_user(user=request.user)
        if model is CourseAssignmentEvent:
            return assignment_events_for_user(user=request.user)
        if model in (Lesson, Quiz, QuizQuestion, QuizOption):
            path = {
                Lesson: "course_version__course",
                Quiz: "course_version__course",
                QuizQuestion: "quiz__course_version__course",
                QuizOption: "question__quiz__course_version__course",
            }[model]
            return super().get_queryset(request).filter(
                **{f"{path}__in": courses_for_user(user=request.user)}
            )
        if model in (QuizAttempt, CourseConfirmation):
            return super().get_queryset(request).filter(
                assignment__in=assignments_for_user(user=request.user)
            )
        return super().get_queryset(request).none()


@admin.register(Course)
class CourseAdmin(ScopedReadOnlyAdmin):
    list_display = ("code", "name", "company", "default_language", "is_active")
    search_fields = ("code", "name")
    list_filter = ("company", "default_language", "is_active")


@admin.register(CourseVersion)
class CourseVersionAdmin(ScopedReadOnlyAdmin):
    list_display = ("course", "language", "version_number", "status", "published_at")
    list_filter = ("status", "language", "course__company")


@admin.register(Lesson)
class LessonAdmin(ScopedReadOnlyAdmin):
    list_display = ("course_version", "sequence", "title", "estimated_minutes")


@admin.register(Quiz)
class QuizAdmin(ScopedReadOnlyAdmin):
    list_display = ("course_version", "title", "passing_score", "max_attempts")


@admin.register(QuizQuestion)
class QuizQuestionAdmin(ScopedReadOnlyAdmin):
    list_display = ("quiz", "sequence", "prompt")


@admin.register(QuizOption)
class QuizOptionAdmin(ScopedReadOnlyAdmin):
    list_display = ("question", "sequence", "label", "is_correct")


@admin.register(CourseAssignmentRule)
class CourseAssignmentRuleAdmin(ScopedReadOnlyAdmin):
    list_display = ("course", "priority", "location", "department", "team", "language")
    list_filter = ("company", "language", "is_active")


@admin.register(CourseAssignment)
class CourseAssignmentAdmin(ScopedReadOnlyAdmin):
    list_display = ("person", "course", "course_version", "status", "due_at", "source")
    list_filter = ("company", "status", "source")
    search_fields = ("person__hydra_id", "person__passport_name", "course__code")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(ScopedReadOnlyAdmin):
    list_display = ("assignment", "sequence", "score", "passed", "submitted_at")


@admin.register(CourseConfirmation)
class CourseConfirmationAdmin(ScopedReadOnlyAdmin):
    list_display = ("assignment", "confirmed_by", "confirmed_at")


@admin.register(CourseAssignmentEvent)
class CourseAssignmentEventAdmin(ScopedReadOnlyAdmin):
    list_display = ("assignment", "sequence", "action", "actor", "occurred_at")
    list_filter = ("action", "source")
