"""
models.py

This module is used to register models for employee app

"""

from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as trans

from base import thread_local_middleware
from base.horilla_company_manager import HorillaCompanyManager
from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeType,
    JobPosition,
    JobRole,
    WorkType,
    validate_time_format,
)
from employee.methods.duration_methods import format_time, strtime_seconds
from horilla.models import HorillaModel
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog

# create your model


def reporting_manager_validator(value):
    """
    Method to implement reporting manager_validator
    """
    return value


class Employee(models.Model):
    """
    Employee model
    """

    choice_gender = [
        ("male", trans("Male")),
        ("female", trans("Female")),
        ("other", trans("Other")),
    ]
    choice_marital = (
        ("single", trans("Single")),
        ("married", trans("Married")),
        ("divorced", trans("Divorced")),
    )
    badge_id = models.CharField(max_length=50, null=True, blank=True)
    employee_user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="employee_get",
        verbose_name=_("User"),
    )
    employee_first_name = models.CharField(
        max_length=200, null=False, verbose_name=_("First Name")
    )
    employee_last_name = models.CharField(
        max_length=200, null=True, blank=True, verbose_name=_("Last Name")
    )
    employee_profile = models.ImageField(
        upload_to="employee/profile", null=True, blank=True
    )
    email = models.EmailField(max_length=254, unique=True)
    phone = models.CharField(
        max_length=15,
    )
    address = models.TextField(max_length=200, blank=True, null=True)
    country = models.CharField(max_length=30, blank=True, null=True)
    state = models.CharField(max_length=30, null=True, blank=True)
    city = models.CharField(max_length=30, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, null=True, choices=choice_gender, default="male"
    )
    qualification = models.CharField(max_length=50, blank=True, null=True)
    experience = models.IntegerField(null=True, blank=True)
    marital_status = models.CharField(
        max_length=50, blank=True, null=True, choices=choice_marital, default="single"
    )
    children = models.IntegerField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=20, null=True, blank=True)
    emergency_contact_relation = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)
    objects = HorillaCompanyManager(
        related_company_field="employee_work_info__company_id"
    )

    def get_image(self):
        """
        This method is used to return the profile image path of the employee
        """
        url = False
        if self.employee_profile:
            url = self.employee_profile.url
        return url

    def get_full_name(self):
        """
        Method will return employee full name
        """
        return (
            f"{self.employee_first_name } {self.employee_last_name}"
            if self.employee_last_name
            else self.employee_first_name
        )

    def get_company(self):
        """
        This method is used to return the company of the employee
        """
        return getattr(getattr(self, "employee_work_info", None), "company_id", None)

    def get_job_position(self):
        """
        This method is used to return the job position of the employee
        """
        return getattr(
            getattr(self, "employee_work_info", None), "job_position_id", None
        )

    def get_department(self):
        """
        This method is used to return the department of the employee
        """
        return getattr(getattr(self, "employee_work_info", None), "department_id", None)

    def get_shift(self):
        """
        This method is used to return the shift of the employee
        """
        return getattr(getattr(self, "employee_work_info", None), "shift_id", None)

    def get_mail(self):
        """
        This method is used to return the shift of the employee
        """
        return getattr(getattr(self, "employee_work_info", None), "email", self.email)

    def get_email(self):
        return self.get_mail()

    def get_work_type(self):
        """
        This method is used to return the work type of the employee
        """
        return getattr(getattr(self, "employee_work_info", None), "work_type_id", None)

    def get_employee_type(self):
        """
        This method is used to return the employee type of the employee
        """
        return getattr(
            getattr(self, "employee_work_info", None), "employee_type_id", None
        )

    def get_reporting_manager(self):
        """
        This method is used to return the employee type of the employee
        """
        return getattr(
            getattr(self, "employee_work_info", None), "reporting_manager_id", None
        )

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = (
            f"https://ui-avatars.com/api/?name={self.get_full_name()}&background=random"
        )
        if self.employee_profile:
            full_filename = settings.MEDIA_ROOT + self.employee_profile.name

            if default_storage.exists(full_filename):
                url = self.employee_profile.url
        return url

    def get_leave_status(self):
        """
        This method is used to get the leave status of the employee
        """
        today = date.today()
        leaves_requests = self.leaverequest_set.filter(
            start_date__lte=today, end_date__gte=today
        )
        status = "Expected working"
        if leaves_requests.exists():
            if leaves_requests.filter(status="approved").exists():
                status = "On Leave"
            elif leaves_requests.filter(status="requested"):
                status = "Waiting Approval"
            else:
                status = "Canceled / Rejected"
        elif self.employee_attendances.filter(
            attendance_date=today,
        ).exists():
            status = "On a break"
        return status

    def get_forecasted_at_work(self):
        """
        This method is used to the employees current day shift status
        """
        today = datetime.today()
        attendance = self.employee_attendances.filter(attendance_date=today).first()
        minimum_hour_seconds = strtime_seconds(getattr(attendance, "minimum_hour", "0"))
        at_work = 0
        forecasted_pending_hours = 0
        if attendance:
            at_work = attendance.get_at_work_from_activities()
        forecasted_pending_hours = max(0, (minimum_hour_seconds - at_work))

        return {
            "forecasted_at_work": format_time(at_work),
            "forecasted_pending_hours": format_time(forecasted_pending_hours),
            "forecasted_at_work_seconds": at_work,
            "forecasted_pending_hours_seconds": forecasted_pending_hours,
        }

    def get_today_attendance(self):
        """
        This method will returns employees todays attendance
        """
        return self.employee_attendances.filter(
            attendance_date=datetime.today()
        ).first()

    def get_archive_condition(self):
        """
        Determine whether an employee is eligible for archiving based on their
        involvement in various processes.

        Returns:
            dict or bool: A dictionary containing a list of related models
                        if the employee is not eligible for archiving,
                        otherwise, False.

        This method checks the employee's association with different models,
        such as reporting manager, recruitment stage, onboarding stage, onboarding task,
        and recruitment manager. If the employee is not associated with any of these,
        they are considered eligible for archiving. If they are associated,
        a dictionary is returned with a list of related models of that employee.
        """
        from onboarding.models import OnboardingStage, OnboardingTask
        from recruitment.models import Recruitment, Stage

        reporting_manager_query = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=self.pk
        )
        recruitment_stage_query = Stage.objects.filter(stage_managers=self.pk)
        onboarding_stage_query = OnboardingStage.objects.filter(employee_id=self.pk)
        onboarding_task_query = OnboardingTask.objects.filter(employee_id=self.pk)
        recruitment_manager_query = Recruitment.objects.filter(
            recruitment_managers=self.pk
        )

        if not (
            reporting_manager_query.exists()
            or recruitment_stage_query.exists()
            or onboarding_stage_query.exists()
            or onboarding_task_query.exists()
            or recruitment_manager_query.exists()
        ):
            return False
        else:
            related_models = []
            related_model_fields = []
            if reporting_manager_query.exists():
                related_models.append(
                    {
                        "verbose_name": _("Reporting manager"),
                        "field_name": "reporting_manager_id",
                    }
                )
            if recruitment_manager_query.exists():
                related_models.append(
                    {
                        "verbose_name": _("Recruitment manager"),
                        "field_name": "recruitment_managers",
                    }
                )
            if recruitment_stage_query.exists():
                related_models.append(
                    {
                        "verbose_name": _("Recruitment stage manager"),
                        "field_name": "recruitment_stage_managers",
                    }
                )
            if onboarding_stage_query.exists():
                related_models.append(
                    {
                        "verbose_name": _("Onboarding stage manager"),
                        "field_name": "onboarding_stage_manager",
                    }
                )
            if onboarding_task_query.exists():
                related_models.append(
                    {
                        "verbose_name": _("Onboarding task manager"),
                        "field_name": "onboarding_task_manager",
                    }
                )
            related_models_dict = {
                "related_models": related_models,
            }
            try:
                REPLACE_EMPLOYEE_CHOICES = [("", _("---Choose employee---"))] + [
                    (
                        employee_id,
                        f"{first_name} {last_name}" if last_name else first_name,
                    )
                    for employee_id, first_name, last_name in Employee.objects.filter(
                        is_active=True
                    ).values_list("id", "employee_first_name", "employee_last_name")
                ]
                related_models_dict["employee_choices"] = REPLACE_EMPLOYEE_CHOICES
            except:
                pass
            return related_models_dict

    def __str__(self) -> str:
        last_name = (
            self.employee_last_name if self.employee_last_name is not None else ""
        )
        badge_id = (f"({self.badge_id})") if self.badge_id is not None else ""
        return f"{self.employee_first_name} {last_name} {badge_id}"

    def check_online(self):
        """
        This method is used to check the user in online users or not
        """
        from attendance.models import Attendance

        request = getattr(thread_local_middleware._thread_locals, "request", None)
        if not getattr(request, "working_employees", None):
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            working_employees = Attendance.objects.filter(
                attendance_date__gte=yesterday,
                attendance_date__lte=today,
                attendance_clock_out_date__isnull=True,
            ).values_list("employee_id", flat=True)
            setattr(request, "working_employees", working_employees)
        working_employees = request.working_employees
        return self.pk in working_employees

    class Meta:
        """
        Recruitment model
        """

        unique_together = ("employee_first_name", "employee_last_name", "email")
        permissions = (
            ("change_ownprofile", "Update own profile"),
            ("view_ownprofile", "View Own Profile"),
        )
        ordering = [
            "employee_first_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["badge_id"],
                condition=models.Q(badge_id__isnull=False),
                name="unique_badge_id",
            )
        ]

    def days_until_birthday(self):
        """
        This method will calculate the day until birthday
        """
        birthday = self.dob
        today = date.today()
        next_birthday = date(today.year, birthday.month, birthday.day)
        if next_birthday < today:
            next_birthday = date(today.year + 1, birthday.month, birthday.day)
        return (next_birthday - today).days

    def get_last_sent_mail(self):
        """
        This method is used to get last send mail
        """
        from base.models import EmailLog

        return (
            EmailLog.objects.filter(to__icontains=self.get_mail())
            .order_by("-created_at")
            .first()
        )

    def save(self, *args, **kwargs):
        # your custom code here
        # ...
        # call the parent class's save method to save the object
        prev_employee = Employee.objects.filter(id=self.id).first()
        super().save(*args, **kwargs)
        request = getattr(thread_local_middleware._thread_locals, "request", None)
        if request and not self.is_active and self.get_archive_condition() is not False:
            self.is_active = True
            super().save(*args, **kwargs)
        employee = self
        if prev_employee and prev_employee.email != employee.email:
            employee.employee_user_id.username = employee.email
            employee.employee_user_id.save()

        if employee.employee_user_id is None:
            # Create user if no corresponding user exists
            username = self.email
            password = self.phone
            user = User.objects.create_user(
                username=username, email=username, password=password
            )
            self.employee_user_id = user
            # default permissions
            change_ownprofile = Permission.objects.get(codename="change_ownprofile")
            view_ownprofile = Permission.objects.get(codename="view_ownprofile")
            user.user_permissions.add(view_ownprofile)
            user.user_permissions.add(change_ownprofile)

        if not hasattr(self, "employee_work_info"):
            EmployeeWorkInformation.objects.get_or_create(employee_id=self)
            return self.save()

        return self


class EmployeeTag(HorillaModel):
    """
    EmployeeTag Model
    """

    title = models.CharField(max_length=50, null=True, verbose_name=_("Title"))
    color = models.CharField(max_length=30, null=True)

    def __str__(self) -> str:
        return f"{self.title}"


class EmployeeWorkInformation(models.Model):
    """
    EmployeeWorkInformation model
    """

    employee_id = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="employee_work_info",
        verbose_name=_("Employee"),
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Job Position"),
    )
    department_id = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Department"),
    )
    work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Work Type"),
    )
    employee_type_id = models.ForeignKey(
        EmployeeType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Employee Type"),
    )
    job_role_id = models.ForeignKey(
        JobRole,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Job Role"),
    )
    reporting_manager_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="reporting_manager",
        verbose_name=_("Reporting Manager"),
    )
    company_id = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name=_("Company"),
    )
    tags = models.ManyToManyField(
        EmployeeTag, blank=True, verbose_name=_("Employee tag")
    )
    location = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Work Location")
    )
    email = models.EmailField(
        max_length=254, blank=True, null=True, verbose_name=_("Email")
    )
    mobile = models.CharField(
        max_length=254,
        blank=True,
        null=True,
    )
    shift_id = models.ForeignKey(
        EmployeeShift,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("Shift"),
    )
    date_joining = models.DateField(
        null=True, blank=True, verbose_name=_("Joining Date")
    )
    contract_end_date = models.DateField(blank=True, null=True)
    basic_salary = models.IntegerField(
        null=True, blank=True, default=0, verbose_name=_("Basic Salary")
    )
    salary_hour = models.IntegerField(
        null=True, blank=True, default=0, verbose_name=_("Salary Per Hour")
    )
    additional_info = models.JSONField(null=True, blank=True)
    experience = models.FloatField(null=True, blank=True, default=0)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager()

    def __str__(self) -> str:
        return f"{self.employee_id} - {self.job_position_id}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_history = False

    def tracking(self):
        """
        This method is used to return the tracked history of the instance
        """
        return get_diff(self)

    def experience_calculator(self):
        """
        This method is to calculate the default value for experience field
        """
        joining_date = self.date_joining
        if joining_date is None:
            return 0
        current_date = datetime.now().date()

        # Calculate the difference between the current date and joining date
        delta = current_date - joining_date

        # Calculate the total number of days
        total_days = delta.days

        # Calculate the number of experience as a float
        experience = total_days / 365.0
        self.experience = experience
        self.save()
        return self


class EmployeeBankDetails(HorillaModel):
    """
    EmployeeBankDetails model
    """

    employee_id = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        related_name="employee_bank_details",
        verbose_name=_("Employee"),
    )
    bank_name = models.CharField(max_length=50)
    account_number = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        default="",
    )
    branch = models.CharField(max_length=50)
    address = models.TextField(max_length=255)
    country = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    any_other_code1 = models.CharField(max_length=50, verbose_name="Bank Code #1")
    any_other_code2 = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Bank Code #2"
    )
    additional_info = models.JSONField(null=True, blank=True)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self) -> str:
        return f"{self.employee_id}-{self.bank_name}"

    def clean(self):
        if self.account_number is not None:
            bank_details = EmployeeBankDetails.objects.exclude(
                employee_id=self.employee_id
            ).filter(account_number=self.account_number)
            if bank_details:
                raise ValidationError(
                    {
                        "account_number": _(
                            "Bank details for an employee with this account number already exist"
                        )
                    }
                )


class NoteFiles(HorillaModel):
    files = models.FileField(upload_to="employee/NoteFiles", blank=True, null=True)
    objects = models.Manager()

    def __str__(self):
        return self.files.name.split("/")[-1]


class EmployeeNote(HorillaModel):
    """
    EmployeeNote model
    """

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee_name",
    )
    description = models.TextField(
        verbose_name=_("Description"), max_length=255, null=True
    )
    note_files = models.ManyToManyField(NoteFiles, blank=True)
    updated_by = models.ForeignKey(Employee, on_delete=models.CASCADE)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self) -> str:
        return f"{self.description}"


class PolicyMultipleFile(HorillaModel):
    """
    PoliciesMultipleFile model
    """

    attachment = models.FileField(upload_to="employee/policies")


class Policy(HorillaModel):
    """
    Policies model
    """

    title = models.CharField(max_length=50)
    body = models.TextField()
    is_visible_to_all = models.BooleanField(default=True)
    specific_employees = models.ManyToManyField(Employee, blank=True, editable=False)
    attachments = models.ManyToManyField(PolicyMultipleFile, blank=True)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.attachments.all().delete()


class BonusPoint(HorillaModel):
    """
    Model representing bonus points for employees with associated conditions.
    """

    CONDITIONS = [
        ("==", _("equals")),
        (">", _("grater than")),
        ("<", _("less than")),
        (">=", _("greater than or equal")),
        ("<=", _("less than or equal")),
    ]
    employee_id = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="bonus_point",
    )
    points = models.IntegerField(
        default=0, help_text="Use negative numbers to reduce points."
    )
    encashment_condition = models.CharField(
        max_length=100, choices=CONDITIONS, blank=True, null=True
    )
    redeeming_points = models.IntegerField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True, max_length=255)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self):
        return f"{self.employee_id} - {self.points} Points"

    def tracking(self):
        """
        This method is used to return the tracked history of the instance
        """
        return get_diff(self)

    @receiver(post_save, sender=Employee)
    def bonus_post_save(sender, instance, **_kwargs):
        """
        Creates a BonusPoint instance for a newly created Employee if one doesn't already exist.

        Args:
            sender (Employee): The model class (Employee) sending the signal.
            instance (Employee): The instance of the Employee model triggering the
                                post-save signal.
            **_kwargs: Additional keyword arguments passed by the signal.
        """
        if not BonusPoint.objects.filter(employee_id__id=instance.id).exists():
            BonusPoint.objects.create(employee_id=instance)


class Actiontype(HorillaModel):
    """
    Action type model
    """

    choice_actions = [
        ("warning", trans("Warning")),
        ("suspension", trans("Suspension")),
        ("dismissal", trans("Dismissal")),
    ]

    title = models.CharField(max_length=50)
    action_type = models.CharField(max_length=30, choices=choice_actions)
    block_option = models.BooleanField(
        default=False,
        verbose_name=_("Enable login block :"),
        help_text="If is enabled, employees log in will be blocked based on period of suspension or dismissal.",
    )

    def __str__(self) -> str:
        return f"{self.title}"


class DisciplinaryAction(HorillaModel):
    """
    Disciplinary model
    """

    choices = [("days", _("Days")), ("hours", _("Hours"))]
    employee_id = models.ManyToManyField(Employee, verbose_name=_("Employees"))
    action = models.ForeignKey(Actiontype, on_delete=models.CASCADE)
    description = models.TextField(max_length=255)
    unit_in = models.CharField(max_length=10, choices=choices, default="days")
    days = models.IntegerField(null=True, default=1)
    hours = models.CharField(
        max_length=6,
        default="00:00",
        null=True,
        validators=[validate_time_format],
    )
    start_date = models.DateField(null=True)
    attachment = models.FileField(
        upload_to="employee/discipline", null=True, blank=True
    )
    company_id = models.ManyToManyField(Company, blank=True)

    objects = HorillaCompanyManager()

    def __str__(self) -> str:
        return f"{self.action}"

    class Meta:
        ordering = ["-id"]


class EmployeeGeneralSetting(HorillaModel):
    """
    EmployeeGeneralSetting
    """

    badge_id_prefix = models.CharField(max_length=5, default="PEP")
    objects = models.Manager()
    company_id = models.ForeignKey(Company, null=True, on_delete=models.CASCADE)
