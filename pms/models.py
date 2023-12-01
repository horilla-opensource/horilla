from django.db import models
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from base.models import Company
from base.horilla_company_manager import HorillaCompanyManager

# importing simple history
from simple_history.models import HistoricalRecords
from employee.models import Employee
from horilla_audit.models import HorillaAuditLog, HorillaAuditInfo

"""Objectives and key result section"""


class Period(models.Model):
    """this is a period model used for creating period"""

    period_name = models.CharField(max_length=150, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

    def __str__(self):
        return self.period_name


class EmployeeObjective(models.Model):

    """this is a EmployObjective model used for creating Employee objectives"""

    STATUS_CHOICES = (
        ("On Track", _("On Track")),
        ("Behind", _("Behind")),
        ("Closed", _("Closed")),
        ("At Risk", _("At Risk")),
        ("Not Started", _("Not Started")),
    )
    objective = models.CharField(null=False, blank=False, max_length=100)
    objective_description = models.TextField(blank=False, null=False)
    created_at = models.DateField(auto_now_add=True)
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="employee_objective",
        null=True,
        blank=True,
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
    history = HorillaAuditLog(bases=[HorillaAuditInfo])
    archive = models.BooleanField(default=False, null=True, blank=True)
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.objective}"


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
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

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

    key_result = models.CharField(max_length=60, null=True, blank=False)
    key_result_description = models.TextField(blank=False, null=True)
    employee_objective_id = models.ForeignKey(
        EmployeeObjective, on_delete=models.CASCADE, related_name="emp_obj_id"
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        related_name="emp_kpi",
        null=True,
        blank=True,
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
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")
    progress_percentage = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return f"{self.key_result} "

    def save(self, *args, **kwargs):
        if self.employee_id is None:
            self.employee_id = self.employee_objective_id.employee_id
        if self.target_value != 0:
            self.progress_percentage = (int(self.current_value)/int(self.target_value))*100
        
        super().save(*args, **kwargs)


"""360degree feedback section"""


class QuestionTemplate(models.Model):
    """question template creation"""

    question_template = models.CharField(
        max_length=100, null=False, blank=False, unique=True
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager()

    def __str__(self):
        return self.question_template


class Question(models.Model):
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


class QuestionOptions(models.Model):
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


class Feedback(models.Model):
    """feedback model for creating feedback"""

    STATUS_CHOICES = (
        ("On Track", _("On Track")),
        ("Behind", _("Behind")),
        ("Closed", _("Closed")),
        ("At Risk", _("At Risk")),
        ("Not Started", _("Not Started")),
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
    created_at = models.DateField(auto_now_add=True)
    archive = models.BooleanField(null=True, blank=True, default=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=False)
    employee_key_results_id = models.ManyToManyField(
        EmployeeKeyResult,
        blank=True,
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id+")

    def __str__(self):
        return f"{self.employee_id.employee_first_name} - {self.review_cycle}"


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
