"""
models.py

This module is used to register models for employee app

"""
from datetime import date, datetime
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User, Permission
from django.utils.translation import gettext_lazy as trans
from django.utils.translation import gettext as _
from simple_history.models import HistoricalRecords
from base.models import (
    Company,
    JobPosition,
    WorkType,
    EmployeeType,
    JobRole,
    Department,
    EmployeeShift,
)
from base.horilla_company_manager import HorillaCompanyManager
from horilla_audit.models import HorillaAuditLog, HorillaAuditInfo
from horilla_audit.methods import get_diff
from django.core.files.storage import default_storage

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
    gender = models.CharField(max_length=10, choices=choice_gender, default="male")
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

    def __str__(self) -> str:
        last_name = (
            self.employee_last_name if self.employee_last_name is not None else ""
        )
        return f"{self.employee_first_name} {last_name}"

    class Meta:
        """
        Recruitment model
        """

        unique_together = ("employee_first_name", "employee_last_name")
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

    def save(self, *args, **kwargs):
        # your custom code here
        # ...
        # call the parent class's save method to save the object
        super().save(*args, **kwargs)
        employee = self
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
            return self.save()
        return self


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
        JobPosition, on_delete=models.PROTECT, null=True, verbose_name=_("Job Position")
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
    location = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    mobile = models.CharField(max_length=254, blank=True, null=True)
    shift_id = models.ForeignKey(
        EmployeeShift,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("Shift"),
    )
    date_joining = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(blank=True, null=True)
    basic_salary = models.IntegerField(null=True, blank=True, default=0)
    salary_hour = models.IntegerField(null=True, blank=True, default=0)
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


class EmployeeBankDetails(models.Model):
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
        max_length=50, null=False, blank=False, unique=True
    )
    branch = models.CharField(max_length=50)
    address = models.TextField(max_length=300)
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
