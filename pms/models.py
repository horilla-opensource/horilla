import operator

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, Department, JobPosition
from employee.models import BonusPoint, Employee
from horilla import horilla_middlewares
from horilla.models import HorillaModel
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from horilla_views.cbv_methods import render_template

"""Objectives and key result section"""


class Period(HorillaModel):
    """this is a period model used for creating period"""

    period_name = models.CharField(max_length=150, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager("company_id")

    def __str__(self):
        return self.period_name


class KeyResult(HorillaModel):
    """model used to create key results"""

    PROGRESS_CHOICES = (
        ("%", _("Percentage")),
        ("#", _("Number")),
        ("Currency", (("$", "USD$"), ("₹", "INR"), ("€", "EUR"))),
    )
    title = models.CharField(
        max_length=60, null=True, blank=False, verbose_name="Title"
    )
    description = models.TextField(
        blank=False, null=False, max_length=255, verbose_name="Description"
    )
    progress_type = models.CharField(
        max_length=60, default="%", choices=PROGRESS_CHOICES
    )
    target_value = models.IntegerField(null=True, blank=True, default=100)
    duration = models.IntegerField(null=True, blank=True)
    archive = models.BooleanField(default=False)
    history = HorillaAuditLog(bases=[HorillaAuditInfo])
    company_id = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        verbose_name=_("Company"),
        on_delete=models.CASCADE,
    )
    objects = HorillaCompanyManager()

    class Meta:
        """
        Meta class for additional options
        """

        ordering = [
            "-id",
        ]

    def __str__(self):
        return f"{self.title}"


class Objective(HorillaModel):
    """Model used for creating objectives"""

    DURATION_UNIT = (
        ("days", _("Days")),
        ("months", _("Months")),
        ("years", _("Years")),
    )
    title = models.CharField(
        null=False, blank=False, max_length=100, verbose_name="Title"
    )
    description = models.TextField(
        blank=False, null=False, max_length=255, verbose_name="Description"
    )
    managers = models.ManyToManyField(
        Employee, related_name="objective", blank=True, verbose_name="Managers"
    )
    assignees = models.ManyToManyField(
        Employee,
        related_name="assignees_objective",
        blank=True,
        verbose_name="Assignees",
    )
    key_result_id = models.ManyToManyField(
        KeyResult,
        blank=True,
        related_name="objective",
        verbose_name="Default Key results",
    )
    duration_unit = models.CharField(
        max_length=20,
        choices=DURATION_UNIT,
        null=True,
        blank=True,
        default="days",
        verbose_name="Duration Unit",
    )
    duration = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    add_assignees = models.BooleanField(default=False)
    archive = models.BooleanField(default=False)
    history = HorillaAuditLog(bases=[HorillaAuditInfo])
    company_id = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        verbose_name=_("Company"),
        on_delete=models.CASCADE,
    )
    self_employee_progress_update = models.BooleanField(default=True)
    objects = HorillaCompanyManager()

    class Meta:
        """
        Meta class for additional options
        """

        ordering = [
            "-id",
        ]

    def __str__(self):
        return f"{self.title}"

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        selected_company = request.session.get("selected_company")
        if (
            not self.id
            and not self.company_id
            and selected_company
            and selected_company != "all"
        ):
            self.company_id = Company.find(selected_company)

        super().save()


class EmployeeObjective(HorillaModel):
    """this is a EmployObjective model used for creating Employee objectives"""

    STATUS_CHOICES = (
        ("On Track", _("On Track")),
        ("Behind", _("Behind")),
        ("Closed", _("Closed")),
        ("At Risk", _("At Risk")),
        ("Not Started", _("Not Started")),
    )
    objective = models.CharField(
        null=True,
        blank=True,
        max_length=100,
        verbose_name="Title",
    )
    objective_description = models.TextField(
        blank=True,
        null=True,
        max_length=255,
        verbose_name="Description",
    )
    created_at = models.DateField(auto_now_add=True)
    objective_id = models.ForeignKey(
        Objective,
        null=True,
        blank=True,
        related_name="employee_objective",
        verbose_name="Objective",
        on_delete=models.PROTECT,
    )
    employee_id = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        related_name="employee_objective",
        on_delete=models.PROTECT,
        verbose_name="Employee",
    )
    key_result_id = models.ManyToManyField(
        KeyResult,
        blank=True,
        related_name="employee_objective",
        verbose_name="Key results",
    )
    updated_at = models.DateField(auto_now=True)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=False,
        blank=False,
        default="Not Started",
    )
    progress_percentage = models.IntegerField(default=0)

    history = HorillaAuditLog(bases=[HorillaAuditInfo], related_name="history_set")
    archive = models.BooleanField(default=False)
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class for additional options
        """

        unique_together = ("employee_id", "objective_id")

    def update_objective_progress(self):
        """
        used for updating progress percentage when current value of key result change
        """
        krs = self.employee_key_result.all()
        if len(krs) > 0:
            current = 0
            for kr in krs:
                current += kr.progress_percentage
            self.progress_percentage = int(current / len(krs))
            self.save()

    def __str__(self):
        return f"{self.objective_id} | {self.employee_id}"

    def save(self, *args, **kwargs):
        if not self.pk and self.objective_id and self.start_date:
            duration = self.objective_id.duration
            if self.objective_id.duration_unit == "days":
                self.end_date = self.start_date + relativedelta(days=duration)
            elif self.objective_id.duration_unit == "months":
                self.end_date = self.start_date + relativedelta(months=duration)
            elif self.objective_id.duration_unit == "years":
                self.end_date = self.start_date + relativedelta(years=duration)
        # Add assignees to the objective
        objective = self.objective_id
        if self.employee_id not in objective.assignees.all():
            objective.assignees.add(self.employee_id)
        super().save(*args, **kwargs)

    def tracking(self):
        return get_diff(self)


class Comment(models.Model):
    """comments for objectives"""

    comment = models.CharField(max_length=150)
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="comment",
        null=True,
        blank=True,
    )
    employee_objective_id = models.ForeignKey(
        EmployeeObjective,
        on_delete=models.CASCADE,
        related_name="emp_objective",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    history = HorillaAuditLog(excluded_fields=["comment"], bases=[HorillaAuditInfo])
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.comment} "


class EmployeeKeyResult(models.Model):
    """employee key result creation"""

    PROGRESS_CHOICES = (
        ("%", _("Percentage")),
        ("#", _("Number")),
        ("Currency", (("$", "USD$"), ("₹", "INR"), ("€", "EUR"))),
    )
    STATUS_CHOICES = (
        ("On Track", _("On Track")),
        ("Behind", _("Behind")),
        ("Closed", _("Closed")),
        ("At Risk", _("At Risk")),
        ("Not Started", _("Not Started")),
    )

    key_result = models.CharField(max_length=60, null=True, blank=True)
    key_result_description = models.TextField(blank=True, null=True, max_length=255)
    employee_objective_id = models.ForeignKey(
        EmployeeObjective,
        null=True,
        blank=True,
        related_name="employee_key_result",
        on_delete=models.CASCADE,
    )
    key_result_id = models.ForeignKey(
        KeyResult,
        null=True,
        blank=True,
        related_name="employee_key_result",
        verbose_name="Key result",
        on_delete=models.PROTECT,
    )
    progress_type = models.CharField(
        max_length=60, null=True, blank=True, choices=PROGRESS_CHOICES
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        default="Not Started",
    )
    created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateField(auto_now=True, null=True, blank=True)
    start_value = models.IntegerField(null=True, blank=True, default=0)
    current_value = models.IntegerField(null=True, blank=True, default=0)
    target_value = models.IntegerField(null=True, blank=True, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    history = HorillaAuditLog(bases=[HorillaAuditInfo])
    objects = HorillaCompanyManager(
        related_company_field="employee_objective_id__objective_id__company_id"
    )
    progress_percentage = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.key_result_id} | {self.employee_objective_id.employee_id} "

    def update_kr_progress(self):
        if self.target_value != 0:
            self.progress_percentage = (
                int(self.current_value) / int(self.target_value)
            ) * 100

    def clean(self):
        from pms.forms import validate_date

        super().clean()
        start_date = self.start_date
        end_date = self.end_date
        # Check that start date is before end date
        validate_date(start_date, end_date)
        start_value = self.start_value
        current_value = self.current_value
        target_value = self.target_value

        # Unique constraint employee_objective_id and key_result_id
        if self.pk:
            if (
                EmployeeKeyResult.objects.filter(
                    key_result_id=self.key_result_id,
                    employee_objective_id=self.employee_objective_id,
                )
                .exclude(id=self.pk)
                .exists()
            ):
                raise ValidationError(
                    _(
                        f"{self.employee_objective_id.employee_id} already assigned {self.key_result_id}."
                    )
                )
        else:
            if EmployeeKeyResult.objects.filter(
                key_result_id=self.key_result_id,
                employee_objective_id=self.employee_objective_id,
            ).exists():
                raise ValidationError(
                    _(
                        f"{self.employee_objective_id.employee_id} already assigned {self.key_result_id}."
                    )
                )
        if target_value == 0:
            raise ValidationError(
                {"target_value": _("The target value can't be zero.")}
            )
        if self.key_result_id.progress_type == "%" and target_value > 100:
            raise ValidationError(
                {
                    "target_value": _(
                        "The key result progress type is in percentage, so the target value cannot exceed 100."
                    )
                }
            )
        if start_value > current_value or start_value > target_value:
            raise ValidationError(
                "The start value can't be greater than current value or target value."
            )
        if current_value > target_value:
            raise ValidationError(
                {
                    "current_value": _(
                        "The current value can't be greater than target value."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.start_date and not self.end_date:
            self.end_date = self.start_date + relativedelta(
                days=self.key_result_id.duration
            )
        if not self.pk and not self.current_value:
            self.current_value = self.start_value
        if self.key_result_id:
            self.key_result = self.key_result_id.title
        self.update_kr_progress()
        super().save(*args, **kwargs)
        self.employee_objective_id.update_objective_progress()

    class meta:
        """
        Meta class to add some additional options
        """

        unique_together = ("key_result_id", "employee_objective_id")


"""360degree feedback section"""


class QuestionTemplate(HorillaModel):
    """question template creation"""

    question_template = models.CharField(
        max_length=100, null=False, blank=False, unique=True, verbose_name="Title"
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager("company_id")

    def __str__(self):
        return self.question_template


class Question(HorillaModel):
    """question creation"""

    QUESTION_TYPE_CHOICE = (
        ("1", _("Text")),
        ("2", _("Rating")),
        ("3", _("Boolean")),
        ("4", _("Multi-choices")),
        ("5", _("Likert")),
    )
    question = models.CharField(max_length=250, null=False, blank=False)
    question_type = models.CharField(
        choices=QUESTION_TYPE_CHOICE, max_length=100, null=True, blank=True
    )
    template_id = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.CASCADE,
        related_name="question",
        null=True,
        blank=True,
    )
    objects = HorillaCompanyManager("template_id__company_id")

    def __str__(self):
        return self.question


class QuestionOptions(HorillaModel):
    """options for question"""

    question_id = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="question_options",
        null=True,
        blank=True,
    )
    option_a = models.CharField(max_length=250, null=True, blank=True)
    option_b = models.CharField(max_length=250, null=True, blank=True)
    option_c = models.CharField(max_length=250, null=True, blank=True)
    option_d = models.CharField(max_length=250, null=True, blank=True)
    objects = HorillaCompanyManager("question_id__template_id__company_id")


class Feedback(HorillaModel):
    """feedback model for creating feedback"""

    STATUS_CHOICES = (
        ("On Track", _("On Track")),
        ("Behind", _("Behind")),
        ("Closed", _("Closed")),
        ("At Risk", _("At Risk")),
        ("Not Started", _("Not Started")),
    )
    PERIOD = (
        ("days", _("Days")),
        ("months", _("Months")),
        ("years", _("Years")),
    )
    review_cycle = models.CharField(
        max_length=100, null=False, blank=False, verbose_name=_("Title")
    )
    manager_id = models.ForeignKey(
        Employee,
        related_name="feedback_manager",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("Manager"),
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="feedback_employee",
        null=False,
        blank=False,
        verbose_name=_("Employee"),
    )
    colleague_id = models.ManyToManyField(
        Employee,
        related_name="feedback_colleague",
        blank=True,
        verbose_name=_("Colleague"),
        help_text=_("Employees working on the same department."),
    )
    subordinate_id = models.ManyToManyField(
        Employee,
        related_name="feedback_subordinate",
        blank=True,
        verbose_name=_("Subordinates"),
        help_text=_(
            "Employees for whom the feedback requester is the reporting manager"
        ),
    )
    others_id = models.ManyToManyField(
        Employee,
        related_name="feedback_others",
        blank=True,
        verbose_name=_("Other Employees"),
    )
    question_template_id = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.DO_NOTHING,
        related_name="feedback_question_template",
        null=False,
        blank=False,
        verbose_name=_("Question Template"),
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="Not Started"
    )
    archive = models.BooleanField(null=True, blank=True, default=False)
    start_date = models.DateField(null=False, blank=False, verbose_name=_("Start Date"))
    end_date = models.DateField(null=True, blank=False, verbose_name=_("End Date"))
    employee_key_results_id = models.ManyToManyField(
        EmployeeKeyResult, blank=True, verbose_name=_("Key Result")
    )
    cyclic_feedback = models.BooleanField(
        default=False, verbose_name=_("Is Cyclic Feedback")
    )
    cyclic_feedback_days_count = models.IntegerField(
        blank=True, null=True, verbose_name=_("Cycle Period")
    )
    cyclic_feedback_period = models.CharField(
        max_length=50, choices=PERIOD, blank=True, null=True
    )
    cyclic_next_start_date = models.DateField(null=True, blank=True)
    cyclic_next_end_date = models.DateField(null=True, blank=True)

    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        ordering = ["-id"]
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedbacks")

    def save(self, *args, **kwargs):
        start_date = self.start_date
        end_date = self.end_date
        cyclic_feedback_period = self.cyclic_feedback_period
        cyclic_feedback_days_count = self.cyclic_feedback_days_count

        if cyclic_feedback_period == "months":
            self.cyclic_next_start_date = self.start_date + relativedelta(
                months=cyclic_feedback_days_count
            )
            self.cyclic_next_end_date = end_date + relativedelta(
                months=cyclic_feedback_days_count
            )
        elif cyclic_feedback_period == "years":
            self.cyclic_next_start_date = start_date + relativedelta(
                years=cyclic_feedback_days_count
            )
            self.cyclic_next_end_date = end_date + relativedelta(
                years=cyclic_feedback_days_count
            )
        elif cyclic_feedback_period == "days":
            self.cyclic_next_start_date = start_date + relativedelta(
                days=cyclic_feedback_days_count
            )
            self.cyclic_next_end_date = end_date + relativedelta(
                days=cyclic_feedback_days_count
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.review_cycle}"

    def requested_employees(self):
        employees = set(self.subordinate_id.all())
        employees.update(self.colleague_id.all())
        employees.update(self.others_id.all())
        if self.manager_id:
            employees.add(self.manager_id)
        if self.employee_id:
            employees.add(self.employee_id)
        return list(employees)


class AnonymousFeedback(models.Model):
    """feedback model for creating feedback"""

    STATUS_CHOICES = (
        ("On Track", _("On Track")),
        ("Behind", _("Behind")),
        ("Closed", _("Closed")),
        ("At Risk", _("At Risk")),
        ("Not Started", _("Not Started")),
    )
    BASED_ON_CHOICES = (
        ("general", _("General")),
        ("employee", _("Employee")),
        ("department", _("Department")),
        ("job_position", _("Job Position")),
    )
    feedback_subject = models.CharField(max_length=100, null=False, blank=False)
    based_on = models.CharField(
        max_length=50, choices=BASED_ON_CHOICES, default="general"
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Employee"),
    )
    department_id = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Department"),
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Job Position"),
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="Not Started"
    )
    created_at = models.DateField(auto_now_add=True)
    archive = models.BooleanField(null=True, blank=True, default=False)
    anonymous_feedback_id = models.CharField(
        max_length=10, null=True, blank=False, editable=False
    )
    feedback_description = models.TextField(null=True, blank=True, max_length=255)
    objects = models.Manager()

    def __str__(self) -> str:
        return f"Feedback based on a {self.based_on}"

    def clean(self, *args, **kwargs):
        if self.based_on == "employee":
            self._validate_required_field("employee_id", "Employee")
            self.department_id = None
            self.job_position_id = None
        elif self.based_on == "department":
            self._validate_required_field("department_id", "Department")
            self.employee_id = None
            self.job_position_id = None
        elif self.based_on == "job_position":
            self._validate_required_field("job_position_id", "Job Position")
            self.employee_id = None
            self.department_id = None

        return super().clean(*args, **kwargs)

    def _validate_required_field(self, field_name, field_label):
        if not getattr(self, field_name):
            raise ValidationError(
                {
                    field_name: _(
                        f"The {field_label} field is required when the 'Based on' field is set to '{field_label}'."
                    )
                }
            )


class Answer(models.Model):
    """feedback answer model"""

    answer = models.JSONField(max_length=200, null=True, blank=True)
    question_id = models.ForeignKey(
        Question,
        on_delete=models.DO_NOTHING,
        related_name="answer_question_id",
        null=True,
        blank=True,
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="employee_answer",
        null=True,
        blank=True,
    )
    feedback_id = models.ForeignKey(
        Feedback, on_delete=models.PROTECT, related_name="feedback_answer"
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.answer}"


class KeyResultFeedback(models.Model):
    feedback_id = models.ForeignKey(
        Feedback,
        on_delete=models.PROTECT,
        related_name="feedback_key_result",
        null=True,
        blank=True,
    )
    employee_id = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING, related_name="employee_key_result"
    )
    answer = models.JSONField(max_length=200, null=True, blank=True)
    key_result_id = models.ForeignKey(
        EmployeeKeyResult,
        related_name="key_result_feedback",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")


class Meetings(HorillaModel):
    title = models.CharField(max_length=100)
    date = models.DateTimeField(null=True, blank=True)
    employee_id = models.ManyToManyField(
        Employee,
        related_name="meeting_employee",
        verbose_name=_("Employee"),
    )
    manager = models.ManyToManyField(Employee, related_name="meeting_manager")
    answer_employees = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="meeting_answer_employees",
        verbose_name=_("Answerable Employees"),
        help_text=_(
            "Select the employees who can respond to question template in this meeting's, if any are added."
        ),
    )
    question_template = models.ForeignKey(
        QuestionTemplate, on_delete=models.PROTECT, null=True, blank=True
    )
    response = models.TextField(null=True, blank=True)
    show_response = models.BooleanField(default=False, editable=False)
    company_id = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Company"),
        on_delete=models.CASCADE,
    )
    objects = HorillaCompanyManager()

    class Meta:
        verbose_name = _("Meetings")
        verbose_name_plural = _("Meetings")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        selected_company = request.session.get("selected_company")
        if (
            not self.id
            and not self.company_id
            and selected_company
            and selected_company != "all"
        ):
            self.company_id = Company.find(selected_company)

        super().save()


class MeetingsAnswer(models.Model):
    """feedback answer model"""

    answer = models.JSONField(max_length=200, null=True, blank=True)
    question_id = models.ForeignKey(
        Question,
        on_delete=models.DO_NOTHING,
        related_name="meeting_answer_question_id",
        null=True,
        blank=True,
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="employee_meeting_answer",
        null=True,
        blank=True,
        verbose_name="Employee",
    )
    meeting_id = models.ForeignKey(
        Meetings, on_delete=models.PROTECT, related_name="meeting_answer"
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.answer}"


class EmployeeBonusPoint(HorillaModel):
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="employe_bonus_point",
        null=True,
        blank=True,
        verbose_name="Employee",
    )
    bonus_point = models.IntegerField(default=0)
    instance = models.CharField(max_length=150, null=True, blank=True)
    based_on = models.CharField(max_length=150)
    bonus_point_id = models.ForeignKey(
        BonusPoint,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="employeebonuspoint_set",
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.bonus_point}"

    def action_template(self):
        """
        This method for get custom column for managers.
        """
        return render_template(
            path="bonus/bonus_point_action.html",
            context={"instance": self},
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not BonusPoint.objects.filter(employee_id=self.employee_id).exists():
            bonus_point = BonusPoint.objects.create(
                employee_id=self.employee_id,
                points=self.bonus_point,
                reason=self.based_on,
            )
        else:
            bonus_point = BonusPoint.objects.get(employee_id=self.employee_id)
        bonus_point.points += self.bonus_point
        bonus_point.reason = self.based_on
        bonus_point.save()


class BonusPointSetting(models.Model):
    MODEL_CHOICES = [
        ("pms.models.EmployeeObjective", _("Objective")),
        ("pms.models.EmployeeKeyResult", _("Key Result")),
    ]
    if apps.is_installed("project"):
        MODEL_CHOICES += [
            ("project.models.Task", _("Task")),
            ("project.models.Project", _("Project")),
        ]
    BONUS_FOR = [
        ("completed", _("Completing")),
        ("Closed", _("Closing")),
    ]
    CONDITIONS = [
        ("=", "="),
        (">", ">"),
        ("<", "<"),
        ("<=", "<="),
        (">=", ">="),
    ]
    FIELD_1 = [
        ("complition_date", _("Completion Date")),
    ]
    FIELD_2 = [
        ("end_date", _("End Date")),
    ]
    APPLECABLE_FOR = [
        ("owner", _("Owner")),
        ("members", _("Members")),
        ("managers", _("Managers")),
    ]
    model = models.CharField(max_length=100, choices=MODEL_CHOICES, null=False)
    applicable_for = models.CharField(
        max_length=50, choices=APPLECABLE_FOR, null=True, blank=True
    )
    bonus_for = models.CharField(max_length=25, choices=BONUS_FOR)
    field_1 = models.CharField(max_length=25, choices=FIELD_1, null=True, blank=True)
    conditions = models.CharField(
        max_length=25, choices=CONDITIONS, null=True, blank=True
    )
    field_2 = models.CharField(max_length=25, choices=FIELD_2, null=True, blank=True)
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    def get_model_display(self):
        """
        Display model
        """
        return dict(BonusPointSetting.MODEL_CHOICES).get(self.model)

    def get_bonus_for_display(self):
        """
        Display bonus_for
        """
        return dict(BonusPointSetting.BONUS_FOR).get(self.bonus_for)

    def get_field_1_display(self):
        """
        Display field_1
        """
        return dict(BonusPointSetting.FIELD_1).get(self.field_1)

    def get_field_2_display(self):
        """
        Display field_2
        """
        return dict(BonusPointSetting.FIELD_2).get(self.field_2)

    def get_applicable_for_display(self):
        """
        Display applicable_for
        """
        return dict(BonusPointSetting.APPLECABLE_FOR).get(self.applicable_for)

    def get_condition(self):
        """
        Get the condition for bonus
        """
        return f" {dict(BonusPointSetting.FIELD_1).get(self.field_1)} {self.conditions} {dict(BonusPointSetting.FIELD_2).get(self.field_2)}"

    def action_template(self):
        """
        This method for get custom column for managers.
        """

        return render_template(
            path="bonus/bonus_seetting_action.html",
            context={"instance": self},
        )

    def is_active_toggle(self):
        """
        For toggle is_active field
        """
        return render_template(
            path="bonus/is_active_toggle.html",
            context={"instance": self},
        )

    def create_employee_bonus(self, employee, field_1, field_2, instance):
        """
        For creating employee bonus
        """
        operator_mapping = {
            "=": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            ">": operator.gt,
            "<=": operator.le,
            ">=": operator.ge,
        }
        if (
            operator_mapping[self.conditions](field_1, field_2)
        ) and not EmployeeBonusPoint.objects.filter(
            employee_id=employee,
            instance=instance,
            based_on=(f"{self.get_bonus_for_display()} {instance}"),
        ).exists():
            EmployeeBonusPoint(
                employee_id=employee,
                based_on=(f"{self.get_bonus_for_display()} {instance}"),
                bonus_point=self.points,
                instance=instance,
            ).save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Bonus point {self.get_model_display()}"


def manipulate_existing_data():
    from dateutil.relativedelta import relativedelta

    try:
        for emp_objective in EmployeeObjective.objects.exclude(objective=None):
            objective, _ = Objective.objects.get_or_create(
                title=emp_objective.objective
            )
            objective.duration = 20
            objective.save()
            emp_objective.end_date = emp_objective.start_date + relativedelta(days=20)
            emp_objective.objective_id = objective
            emp_objective.objective = None
            emp_objective.objective_description = None
            emp_objective.save()

        for e_kr in EmployeeKeyResult.objects.exclude(key_result=None):
            kr, _ = KeyResult.objects.get_or_create(title=e_kr.key_result)
            kr.duration = 2
            kr.save()
            e_kr.end_date = e_kr.start_date + relativedelta(days=2)
            e_kr.key_result = None
            e_kr.key_result_description = None
            e_kr.key_result_id = kr
            e_kr.save()

    except Exception as e:
        return


manipulate_existing_data()
