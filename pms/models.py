from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, Department, JobPosition
from employee.models import Employee
from horilla.models import HorillaModel
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog

"""Objectives and key result section"""


class Period(HorillaModel):
    """this is a period model used for creating period"""

    period_name = models.CharField(max_length=150, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

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
    archive = models.BooleanField(default=False, null=True, blank=True)
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
        if target_value == 0:
            raise ValidationError(
                {"target_value": _("The target value can't be zero.")}
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
        # if self.employee_id is None:
        #     self.employee_id = self.employee_objective_id.employee_id
        # if self.target_value != 0:
        if not self.pk and not self.current_value:
            self.current_value = self.start_value
        if self.key_result_id:
            self.key_result = self.key_result_id.title
        self.update_kr_progress()
        super().save(*args, **kwargs)
        self.employee_objective_id.update_objective_progress()

    # class meta:
    #     """
    #     Meta class to add some additional options
    #     """

    #     unique_together = ("key_result_id", "employee_objective_id")


"""360degree feedback section"""


class QuestionTemplate(HorillaModel):
    """question template creation"""

    question_template = models.CharField(
        max_length=100, null=False, blank=False, unique=True
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager()

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
    review_cycle = models.CharField(max_length=100, null=False, blank=False)
    manager_id = models.ForeignKey(
        Employee,
        related_name="feedback_manager",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=False,
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="feedback_employee",
        null=False,
        blank=False,
    )
    colleague_id = models.ManyToManyField(
        Employee, related_name="feedback_colleague", blank=True
    )
    subordinate_id = models.ManyToManyField(
        Employee, related_name="feedback_subordinate", blank=True
    )
    question_template_id = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.DO_NOTHING,
        related_name="feedback_question_template",
        null=False,
        blank=False,
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="Not Started"
    )
    archive = models.BooleanField(null=True, blank=True, default=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=False)
    employee_key_results_id = models.ManyToManyField(
        EmployeeKeyResult,
        blank=True,
    )
    cyclic_feedback = models.BooleanField(default=False)
    cyclic_feedback_days_count = models.IntegerField(blank=True, null=True)
    cyclic_feedback_period = models.CharField(
        max_length=50, choices=PERIOD, blank=True, null=True
    )
    cyclic_next_start_date = models.DateField(null=True, blank=True)
    cyclic_next_end_date = models.DateField(null=True, blank=True)

    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        ordering = ["-id"]

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
        Employee, related_name="meeting_employee", verbose_name="Employee"
    )
    manager = models.ManyToManyField(Employee, related_name="meeting_manager")
    answer_employees = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="meeting_answer_employees",
        verbose_name="Answerable Employees",
    )
    question_template = models.ForeignKey(
        QuestionTemplate, on_delete=models.PROTECT, null=True, blank=True
    )
    response = models.TextField(null=True, blank=True)
    show_response = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Meetings")

    def __str__(self):
        return self.title


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


def manipulate_existing_data():
    from dateutil.relativedelta import relativedelta

    from horilla.decorators import logger

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
