from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company, Department, EmployeeType
from hydra.models import HorillaModel
from hydra_coordination.models import Location, Team
from hydra_people.models import Person


class Course(HorillaModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_courses",
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True, max_length=2000)
    default_language = models.CharField(
        max_length=3,
        choices=Person.PreferredLanguage.choices,
        default=Person.PreferredLanguage.POLISH,
    )

    class Meta:
        ordering = ("company__company", "code", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("company", "code"),
                name="hyd_onb_course_company_code",
            ),
        )

    def __str__(self):
        return f"{self.code} — {self.name}"

    def get_absolute_url(self):
        return reverse("hydra-onboarding-course-detail", args=(self.uuid,))

    def clean(self):
        super().clean()
        self.code = self.code.strip().upper()
        self.name = " ".join(self.name.split())
        self.description = self.description.strip()
        if len(self.code) < 2:
            raise ValidationError({"code": _("Enter at least two characters.")})


class ProtectedVersionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Course versions must be changed through onboarding services.")

    def delete(self):
        raise TypeError("Course versions cannot be bulk-deleted.")


class CourseVersion(HorillaModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        RETIRED = "retired", _("Retired")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField(editable=False)
    language = models.CharField(
        max_length=3,
        choices=Person.PreferredLanguage.choices,
    )
    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True, max_length=2000)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        editable=False,
    )
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="published_hydra_course_versions",
        null=True,
        blank=True,
        editable=False,
    )
    content_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
    )

    objects = ProtectedVersionQuerySet.as_manager()

    IMMUTABLE_FIELDS = (
        "course_id",
        "version_number",
        "language",
        "title",
        "summary",
        "status",
        "published_at",
        "published_by_id",
        "content_fingerprint",
        "is_active",
        "created_by_id",
        "created_at",
    )

    class Meta:
        ordering = ("course_id", "language", "-version_number", "pk")
        permissions = (
            ("publish_courseversion", "Can publish a Hydra course version"),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("course", "language", "version_number"),
                name="hyd_onb_version_identity",
            ),
            models.CheckConstraint(
                check=Q(version_number__gte=1),
                name="hyd_onb_version_positive",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        status="draft",
                        published_at__isnull=True,
                        published_by__isnull=True,
                        content_fingerprint="",
                    )
                    | Q(
                        status__in=("published", "retired"),
                        published_at__isnull=False,
                        published_by__isnull=False,
                        content_fingerprint__gt="",
                    )
                ),
                name="hyd_onb_version_publish_shape",
            ),
        )

    def __str__(self):
        return f"{self.course.code} / {self.language} / v{self.version_number}"

    def get_absolute_url(self):
        return reverse("hydra-onboarding-version-detail", args=(self.uuid,))

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT

    def clean(self):
        super().clean()
        self.title = " ".join(self.title.split())
        self.summary = self.summary.strip()
        if self.version_number < 1:
            raise ValidationError({"version_number": _("Version must be positive.")})

    def save(self, *args, **kwargs):
        service_update = kwargs.pop("service_update", False)
        if self.pk:
            original = type(self)._base_manager.values(*self.IMMUTABLE_FIELDS).get(
                pk=self.pk
            )
            changed = any(
                original[field] != getattr(self, field)
                for field in self.IMMUTABLE_FIELDS
            )
            if original["status"] != self.Status.DRAFT and changed:
                raise TypeError("Published course versions are immutable.")
            if changed and not service_update:
                raise TypeError("Course versions must be changed through onboarding services.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status != self.Status.DRAFT:
            raise TypeError("Published course versions cannot be deleted.")
        return super().delete(*args, **kwargs)


class DraftContentQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Published course content is immutable.")

    def delete(self):
        raise TypeError("Course content cannot be bulk-deleted.")


class DraftContentModel(models.Model):
    objects = DraftContentQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def owning_version(self):
        raise NotImplementedError

    def _assert_draft(self):
        version = self.owning_version
        current_status = CourseVersion._base_manager.values_list(
            "status", flat=True
        ).get(pk=version.pk)
        if current_status != CourseVersion.Status.DRAFT:
            raise TypeError("Published course content is immutable.")

    def save(self, *args, **kwargs):
        self._assert_draft()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._assert_draft()
        return super().delete(*args, **kwargs)


class Lesson(DraftContentModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    course_version = models.ForeignKey(
        CourseVersion,
        on_delete=models.PROTECT,
        related_name="lessons",
    )
    sequence = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    body = models.TextField()
    estimated_minutes = models.PositiveSmallIntegerField(default=5)
    requires_confirmation = models.BooleanField(default=True)

    class Meta:
        ordering = ("course_version_id", "sequence", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("course_version", "sequence"),
                name="hyd_onb_lesson_sequence",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_onb_lesson_seq_positive",
            ),
            models.CheckConstraint(
                check=Q(estimated_minutes__gte=1) & Q(estimated_minutes__lte=480),
                name="hyd_onb_lesson_minutes",
            ),
        )

    @property
    def owning_version(self):
        return self.course_version

    def __str__(self):
        return f"{self.sequence}. {self.title}"

    def clean(self):
        super().clean()
        self.title = " ".join(self.title.split())
        self.body = self.body.strip()
        if not self.body:
            raise ValidationError({"body": _("Lesson content is required.")})


class Quiz(DraftContentModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    course_version = models.OneToOneField(
        CourseVersion,
        on_delete=models.PROTECT,
        related_name="quiz",
    )
    title = models.CharField(max_length=180)
    passing_score = models.PositiveSmallIntegerField(default=80)
    max_attempts = models.PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ("course_version_id",)
        constraints = (
            models.CheckConstraint(
                check=Q(passing_score__gte=1) & Q(passing_score__lte=100),
                name="hyd_onb_quiz_passing_score",
            ),
            models.CheckConstraint(
                check=Q(max_attempts__gte=1) & Q(max_attempts__lte=20),
                name="hyd_onb_quiz_max_attempts",
            ),
        )

    @property
    def owning_version(self):
        return self.course_version

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        self.title = " ".join(self.title.split())


class QuizQuestion(DraftContentModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.PROTECT,
        related_name="questions",
    )
    sequence = models.PositiveIntegerField()
    prompt = models.TextField(max_length=1000)

    class Meta:
        ordering = ("quiz_id", "sequence", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("quiz", "sequence"),
                name="hyd_onb_question_sequence",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_onb_question_seq_positive",
            ),
        )

    @property
    def owning_version(self):
        return self.quiz.course_version

    def __str__(self):
        return f"{self.sequence}. {self.prompt}"

    def clean(self):
        super().clean()
        self.prompt = " ".join(self.prompt.split())


class QuizOption(DraftContentModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.PROTECT,
        related_name="options",
    )
    sequence = models.PositiveIntegerField()
    label = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ("question_id", "sequence", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("question", "sequence"),
                name="hyd_onb_option_sequence",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_onb_option_seq_positive",
            ),
        )

    @property
    def owning_version(self):
        return self.question.quiz.course_version

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        self.label = " ".join(self.label.split())


class CourseAssignmentRule(HorillaModel):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_course_assignment_rules",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="assignment_rules",
    )
    priority = models.PositiveSmallIntegerField(default=100)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="course_assignment_rules",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="hydra_course_assignment_rules",
        null=True,
        blank=True,
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="course_assignment_rules",
        null=True,
        blank=True,
    )
    language = models.CharField(
        max_length=3,
        choices=Person.PreferredLanguage.choices,
        blank=True,
    )
    employee_type = models.ForeignKey(
        EmployeeType,
        on_delete=models.PROTECT,
        related_name="hydra_course_assignment_rules",
        null=True,
        blank=True,
    )
    due_days = models.PositiveSmallIntegerField(null=True, blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ("-priority", "course__code", "pk")
        constraints = (
            models.CheckConstraint(
                check=Q(priority__lte=1000),
                name="hyd_onb_rule_priority",
            ),
            models.CheckConstraint(
                check=(
                    Q(due_days__isnull=True)
                    | (Q(due_days__gte=1) & Q(due_days__lte=365))
                ),
                name="hyd_onb_rule_due_days",
            ),
        )

    def __str__(self):
        return f"{self.course.code} / priority {self.priority}"

    @property
    def specificity(self):
        return sum(
            bool(value)
            for value in (
                self.location_id,
                self.department_id,
                self.team_id,
                self.language,
                self.employee_type_id,
            )
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.course_id and self.company_id and self.course.company_id != self.company_id:
            errors["course"] = _("Course and rule must belong to the same Company.")
        if self.location_id and self.company_id and self.location.company_id != self.company_id:
            errors["location"] = _("Location must belong to the rule Company.")
        if self.department_id and self.company_id and not self.department.company_id.filter(
            pk=self.company_id
        ).exists():
            errors["department"] = _("Department must belong to the rule Company.")
        if self.team_id:
            team_company_id = self.team.section.location.company_id
            if self.company_id and team_company_id != self.company_id:
                errors["team"] = _("Team must belong to the rule Company.")
            if self.location_id and self.team.section.location_id != self.location_id:
                errors["team"] = _("Team must belong to the selected Location.")
            if self.department_id and self.team.section.department_id != self.department_id:
                errors["team"] = _("Team must belong to the selected Department.")
        if self.employee_type_id and self.company_id and not self.employee_type.company_id.filter(
            pk=self.company_id
        ).exists():
            errors["employee_type"] = _("Employee type must belong to the rule Company.")
        if errors:
            raise ValidationError(errors)


class ProtectedAssignmentQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Course assignments must be changed through onboarding services.")

    def delete(self):
        raise TypeError("Course assignments are durable records.")


class CourseAssignment(HorillaModel):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", _("Assigned")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")

    class Source(models.TextChoices):
        RULE = "rule", _("Automatic rule")
        MANUAL = "manual", _("Manual")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    request_key = models.UUIDField(default=uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="hydra_course_assignments",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="course_assignments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    course_version = models.ForeignKey(
        CourseVersion,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    rule = models.ForeignKey(
        CourseAssignmentRule,
        on_delete=models.PROTECT,
        related_name="assignments",
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=12, choices=Source.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ASSIGNED,
        editable=False,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_hydra_courses",
        null=True,
        blank=True,
        editable=False,
    )
    assigned_at = models.DateTimeField(default=timezone.now, editable=False)
    due_at = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True, editable=False)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    assignment_snapshot = models.JSONField(editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)

    objects = ProtectedAssignmentQuerySet.as_manager()

    IDENTITY_FIELDS = (
        "request_key",
        "company_id",
        "person_id",
        "course_id",
        "course_version_id",
        "rule_id",
        "source",
        "assigned_by_id",
        "assigned_at",
        "due_at",
        "assignment_snapshot",
        "is_active",
        "created_by_id",
        "created_at",
    )
    STATE_FIELDS = ("status", "started_at", "completed_at", "version", "modified_by_id")

    class Meta:
        ordering = ("status", "due_at", "assigned_at", "pk")
        permissions = (
            ("assign_course", "Can assign Hydra onboarding courses"),
            ("start_courseassignment", "Can start a Hydra course assignment"),
            ("confirm_courseassignment", "Can confirm Hydra course completion"),
            ("submit_quizattempt", "Can submit Hydra course quiz attempts"),
        )
        indexes = (
            models.Index(
                fields=("company", "status", "due_at"),
                name="hyd_onb_assign_state_idx",
            ),
            models.Index(
                fields=("person", "status"),
                name="hyd_onb_assign_person_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("person", "course"),
                name="hyd_onb_person_course_uniq",
            ),
            models.CheckConstraint(
                check=Q(version__gte=1),
                name="hyd_onb_assign_version",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        status="assigned",
                        started_at__isnull=True,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status="in_progress",
                        started_at__isnull=False,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status="completed",
                        started_at__isnull=False,
                        completed_at__isnull=False,
                    )
                ),
                name="hyd_onb_assign_state_shape",
            ),
            models.CheckConstraint(
                check=(
                    Q(source="rule", rule__isnull=False)
                    | Q(source="manual", rule__isnull=True)
                ),
                name="hyd_onb_assign_source_shape",
            ),
        )

    def __str__(self):
        return f"{self.person.hydra_id} / {self.course.code}"

    def get_absolute_url(self):
        return reverse("hydra-onboarding-assignment-detail", args=(self.uuid,))

    def clean(self):
        super().clean()
        errors = {}
        if self.person_id and self.person.merged_into_id:
            errors["person"] = _("Assignments require the canonical Person record.")
        if self.course_id and self.company_id and self.course.company_id != self.company_id:
            errors["course"] = _("Course and assignment Company differ.")
        if self.course_version_id and self.course_id:
            if self.course_version.course_id != self.course_id:
                errors["course_version"] = _("Version belongs to another course.")
            if self.course_version.status != CourseVersion.Status.PUBLISHED:
                errors["course_version"] = _("Only a published version can be assigned.")
        if self.rule_id and self.course_id and self.rule.course_id != self.course_id:
            errors["rule"] = _("Rule belongs to another course.")
        if not self.assignment_snapshot:
            errors["assignment_snapshot"] = _("Assignment snapshot is required.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        service_update = kwargs.pop("service_update", False)
        if self.pk:
            original = type(self)._base_manager.values(
                *(self.IDENTITY_FIELDS + self.STATE_FIELDS)
            ).get(pk=self.pk)
            if any(
                original[field] != getattr(self, field)
                for field in self.IDENTITY_FIELDS
            ):
                raise TypeError("Course assignment identity is immutable.")
            if not service_update and any(
                original[field] != getattr(self, field)
                for field in self.STATE_FIELDS
            ):
                raise TypeError("Course assignments must be changed through onboarding services.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Course assignments are durable records.")


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Onboarding learning evidence is append-only.")

    def delete(self):
        raise TypeError("Onboarding learning evidence is append-only.")


class QuizAttempt(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.PROTECT,
        related_name="quiz_attempts",
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    sequence = models.PositiveIntegerField()
    score = models.PositiveSmallIntegerField()
    passed = models.BooleanField()
    answers_snapshot = models.JSONField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_quiz_attempts",
    )
    submitted_at = models.DateTimeField(default=timezone.now)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("assignment_id", "sequence", "pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("assignment", "sequence"),
                name="hyd_onb_attempt_sequence",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_onb_attempt_seq_positive",
            ),
            models.CheckConstraint(
                check=Q(score__gte=0) & Q(score__lte=100),
                name="hyd_onb_attempt_score",
            ),
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.assignment_id and self.quiz_id:
            if self.assignment.course_version_id != self.quiz.course_version_id:
                errors["quiz"] = _("Quiz belongs to another assigned version.")
        if not self.answers_snapshot:
            errors["answers_snapshot"] = _("Answer evidence is required.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Quiz attempts are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Quiz attempts are append-only.")


class CourseConfirmation(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    assignment = models.OneToOneField(
        CourseAssignment,
        on_delete=models.PROTECT,
        related_name="confirmation",
    )
    statement = models.CharField(max_length=500)
    statement_snapshot = models.JSONField()
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_course_confirmations",
    )
    confirmed_at = models.DateTimeField(default=timezone.now)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-confirmed_at", "-pk")
        default_permissions = ("view",)

    def clean(self):
        super().clean()
        self.statement = " ".join(self.statement.split())
        if not self.statement:
            raise ValidationError({"statement": _("Confirmation statement is required.")})
        if not self.statement_snapshot:
            raise ValidationError(
                {"statement_snapshot": _("Confirmation snapshot is required.")}
            )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Course confirmations are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Course confirmations are append-only.")


class CourseAssignmentEvent(models.Model):
    class Action(models.TextChoices):
        ASSIGNED = "assigned", _("Course assigned")
        STARTED = "started", _("Course started")
        QUIZ_SUBMITTED = "quiz_submitted", _("Quiz submitted")
        COMPLETED = "completed", _("Course completed")

    class Source(models.TextChoices):
        USER = "user", _("User")
        SYSTEM = "system", _("System")

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.PROTECT,
        related_name="events",
    )
    sequence = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=Action.choices)
    source = models.CharField(max_length=8, choices=Source.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_course_assignment_events",
        null=True,
        blank=True,
    )
    quiz_attempt = models.OneToOneField(
        QuizAttempt,
        on_delete=models.PROTECT,
        related_name="assignment_event",
        null=True,
        blank=True,
    )
    confirmation = models.OneToOneField(
        CourseConfirmation,
        on_delete=models.PROTECT,
        related_name="assignment_event",
        null=True,
        blank=True,
    )
    details_snapshot = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(default=timezone.now)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("assignment_id", "sequence", "pk")
        default_permissions = ("view",)
        constraints = (
            models.UniqueConstraint(
                fields=("assignment", "sequence"),
                name="hyd_onb_event_sequence",
            ),
            models.CheckConstraint(
                check=Q(sequence__gte=1),
                name="hyd_onb_event_seq_positive",
            ),
            models.CheckConstraint(
                check=(
                    Q(source="user", actor__isnull=False)
                    | Q(source="system", actor__isnull=True)
                ),
                name="hyd_onb_event_actor_shape",
            ),
            models.CheckConstraint(
                check=(
                    Q(
                        action__in=("assigned", "started"),
                        quiz_attempt__isnull=True,
                        confirmation__isnull=True,
                    )
                    | Q(
                        action="quiz_submitted",
                        quiz_attempt__isnull=False,
                        confirmation__isnull=True,
                    )
                    | Q(
                        action="completed",
                        quiz_attempt__isnull=True,
                        confirmation__isnull=False,
                    )
                ),
                name="hyd_onb_event_subject_shape",
            ),
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Course assignment events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Course assignment events are append-only.")
