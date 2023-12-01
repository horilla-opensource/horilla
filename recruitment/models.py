"""
models.py

This module is used to register models for recruitment app

"""
import re
import os
import json
from django import forms
import django
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from horilla_audit.models import HorillaAuditLog, HorillaAuditInfo
from horilla_audit.methods import get_diff
from employee.models import Employee
from base.models import JobPosition, Company
from django.core.files.storage import default_storage
from base.horilla_company_manager import HorillaCompanyManager


# Create your models here.


def validate_mobile(value):
    """
    This method is used to validate the mobile number using regular expression
    """
    pattern = r"^\+[0-9 ]+$|^[0-9 ]+$"

    if re.match(pattern, value) is None:
        if "+" in value:
            raise forms.ValidationError(
                "Invalid input: Plus symbol (+) should only appear at the beginning \
                    or no other characters allowed."
            )
        raise forms.ValidationError(
            "Invalid input: Only digits and spaces are allowed."
        )


def validate_pdf(value):
    """
    This method is used to validate pdf
    """
    ext = os.path.splitext(value.name)[1]  # Get file extension
    if ext.lower() != ".pdf":
        raise ValidationError(_("File must be a PDF."))


def validate_image(value):
    """
    This method is used to validate the image
    """
    return value


class Recruitment(models.Model):
    """
    Recruitment model
    """

    title = models.CharField(max_length=30, null=True, blank=True)
    description = models.TextField(null=True)
    is_event_based = models.BooleanField(
        default=False,
        help_text=_("To start bulk recruitment form multiple job positions"),
    )
    closed = models.BooleanField(
        default=False,
        help_text=_(
            "To close the recruitment, If closed then not visible on pipeline view."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "To archive and un-archive a recruitment, if active is false then it \
            will not appear on recruitment list view."
        ),
    )
    open_positions = models.ManyToManyField(
        JobPosition, related_name="open_positions", blank=True
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="recruitment",
        verbose_name=_("Job Position"),
    )
    vacancy = models.IntegerField(blank=True, null=True)
    recruitment_managers = models.ManyToManyField(Employee)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    start_date = models.DateField(default=django.utils.timezone.now)
    end_date = models.DateField(blank=True, null=True)
    objects = HorillaCompanyManager()

    class Meta:
        """
        Meta class to add the additional info
        """

        unique_together = [
            (
                "job_position_id",
                "start_date",
            ),
            ("job_position_id", "start_date", "company_id"),
        ]
        permissions = (("archive_recruitment", "Archive Recruitment"),)

    def __str__(self):
        title = (
            f"{self.job_position_id.job_position} {self.start_date}"
            if self.title is None and self.job_position_id
            else self.title
        )

        if not self.is_event_based and self.job_position_id is not None:
            self.open_positions.add(self.job_position_id)

        return title

    def clean(self):
        if self.title is None:
            raise ValidationError({"title": _("This field is required")})
        if self.end_date is not None and (
            self.start_date is not None and self.start_date > self.end_date
        ):
            raise ValidationError(
                {"end_date": _("End date cannot be less than start date.")}
            )
        if not self.is_event_based and self.job_position_id is None:
            raise ValidationError({"job_position_id": _("This field is required")})
        return super().clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the Recruitment instance first
        if self.is_event_based and self.open_positions is None:
            raise ValidationError({"open_positions": _("This field is required")})


@receiver(post_save, sender=Recruitment)
def create_initial_stage(sender, instance, created, **kwargs):
    """
    This is post save method, used to create initial stage for the recruitment
    """
    if created:
        initial_stage = Stage()
        initial_stage.sequence = 0
        initial_stage.recruitment_id = instance
        initial_stage.stage = "Initial"
        initial_stage.stage_type = "initial"
        initial_stage.save()


class Stage(models.Model):
    """
    Stage model
    """

    stage_types = [
        ("initial", _("Initial")),
        ("test", _("Test")),
        ("interview", _("Interview")),
        ("hired", _("Hired")),
    ]
    recruitment_id = models.ForeignKey(
        Recruitment,
        on_delete=models.CASCADE,
        related_name="stage_set",
        verbose_name=_("Recruitment"),
    )
    stage_managers = models.ManyToManyField(Employee)
    stage = models.CharField(max_length=50)
    stage_type = models.CharField(
        max_length=20, choices=stage_types, default="interview"
    )
    sequence = models.IntegerField(null=True, default=0)
    is_active = models.BooleanField(default=True)
    objects = HorillaCompanyManager(related_company_field="recruitment_id__company_id")

    def __str__(self):
        return f"{self.stage}"

    class Meta:
        """
        Meta class to add the additional info
        """

        permissions = (("archive_Stage", "Archive Stage"),)
        unique_together = ["recruitment_id", "stage"]
        ordering = ["sequence"]

    def active_candidates(self):
        """
        This method is used to get all the active candidate like related objects
        """
        return {
            "all": Candidate.objects.filter(
                stage_id=self, canceled=False, is_active=True
            )
        }


class Candidate(models.Model):
    """
    Candidate model
    """

    choices = [("male", _("Male")), ("female", _("Female")), ("other", _("Other"))]
    name = models.CharField(max_length=100, null=True, verbose_name=_("Name"))
    profile = models.ImageField(upload_to="recruitment/profile", null=True)
    portfolio = models.URLField(max_length=200, blank=True)
    recruitment_id = models.ForeignKey(
        Recruitment,
        on_delete=models.PROTECT,
        null=True,
        related_name="candidate",
        verbose_name=_("Recruitment"),
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Job Position"),
    )
    stage_id = models.ForeignKey(
        Stage,
        on_delete=models.PROTECT,
        null=True,
        verbose_name=_("Stage"),
    )
    schedule_date = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Schedule date")
    )
    email = models.EmailField(max_length=254, unique=True, verbose_name=_("Email"))
    mobile = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            validate_mobile,
        ],
        verbose_name=_("Phone"),
    )
    resume = models.FileField(
        upload_to="recruitment/resume",
        validators=[
            validate_pdf,
        ],
    )
    referral = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="candidate_referral",
        verbose_name=_("Referral"),
    )
    address = models.TextField(null=True, blank=True, verbose_name=_("Address"))
    country = models.CharField(
        max_length=30, null=True, blank=True, verbose_name=_("Country")
    )
    dob = models.DateField(null=True, blank=True, verbose_name=_("Date of Birth"))
    state = models.CharField(
        max_length=30, null=True, blank=True, verbose_name=_("State")
    )
    city = models.CharField(
        max_length=30, null=True, blank=True, verbose_name=_("City")
    )
    zip = models.CharField(
        max_length=30, null=True, blank=True, verbose_name=_("Zip Code")
    )
    gender = models.CharField(
        max_length=15, choices=choices, null=True, verbose_name=_("Gender")
    )
    start_onboard = models.BooleanField(default=False, verbose_name=_("Start Onboard"))
    hired = models.BooleanField(default=False, verbose_name=_("Hired"))
    canceled = models.BooleanField(default=False, verbose_name=_("Canceled"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    joining_date = models.DateField(
        blank=True, null=True, verbose_name=_("Joining Date")
    )
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    sequence = models.IntegerField(null=True, default=0)
    objects = HorillaCompanyManager(related_company_field="recruitment_id__company_id")

    def __str__(self):
        return f"{self.name}"

    def get_full_name(self):
        """
        Method will return employee full name
        """
        return str(self.name)

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = (
            f"https://ui-avatars.com/api/?name={self.get_full_name()}&background=random"
        )
        if self.profile:
            full_filename = settings.MEDIA_ROOT + self.profile.name

            if default_storage.exists(full_filename):
                url = self.profile.url

        return url

    def tracking(self):
        """
        This method is used to return the tracked history of the instance
        """
        return get_diff(self)

    def save(self, *args, **kwargs):
        # Check if the 'stage_id' attribute is not None
        if self.stage_id is not None:
            # Check if the stage type is 'hired'
            if self.stage_id.stage_type == "hired":
                self.hired = True
        if not self.recruitment_id.is_event_based and self.job_position_id is None:
            self.job_position_id = self.recruitment_id.job_position_id
        if self.job_position_id not in self.recruitment_id.open_positions.all():
            raise ValidationError({"job_position_id": _("Choose valid choice")})
        if self.recruitment_id.is_event_based and self.job_position_id is None:
            raise ValidationError({"job_position_id": _("This field is required.")})
        super().save(*args, **kwargs)

    class Meta:
        """
        Meta class to add the additional info
        """

        unique_together = (
            "email",
            "recruitment_id",
        )
        permissions = (
            ("view_history", "View Candidate History"),
            ("archive_candidate", "Archive Candidate"),
        )
        ordering = ["sequence"]


class StageNote(models.Model):
    """
    StageNote model
    """

    candidate_id = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    title = models.CharField(max_length=50, null=True, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    stage_id = models.ForeignKey(Stage, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(Employee, on_delete=models.CASCADE)
    objects = HorillaCompanyManager(related_company_field="candidate_id__recruitment_id__company_id")

    def __str__(self) -> str:
        return f"{self.description}"


class RecruitmentSurvey(models.Model):
    """
    RecruitmentSurvey model
    """

    question_types = [
        ("checkbox", _("Yes/No")),
        ("options", _("Choices")),
        ("multiple", _("Multiple Choice")),
        ("text", _("Text")),
        ("number", _("Number")),
        ("percentage", _("Percentage")),
        ("date", _("Date")),
        ("textarea", _("Textarea")),
        ("file", _("File Upload")),
        ("rating", _("Rating")),
    ]
    question = models.TextField(null=False)
    recruitment_ids = models.ManyToManyField(
        Recruitment,
        verbose_name=_("Recruitment"),
    )
    job_position_ids = models.ManyToManyField(
        JobPosition,
        verbose_name=_("Job Positions"),
    )
    sequence = models.IntegerField(null=True, default=0)
    type = models.CharField(
        max_length=15,
        choices=question_types,
    )
    options = models.TextField(
        null=True, default="", help_text=_("Separate choices by ',  '")
    )
    is_mandatory = models.BooleanField(default=False)
    objects = HorillaCompanyManager(related_company_field="recruitment_ids__company_id")

    def __str__(self) -> str:
        return str(self.question)

    def choices(self):
        """
        Used to split the choices
        """
        return self.options.split(", ")


class RecruitmentSurveyAnswer(models.Model):
    """
    RecruitmentSurveyAnswer
    """

    candidate_id = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    recruitment_id = models.ForeignKey(
        Recruitment,
        on_delete=models.PROTECT,
        verbose_name=_("Recruitment"),
        null=True,
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.PROTECT,
        verbose_name=_("Job Position"),
        null=True,
    )
    answer_json = models.JSONField()
    attachment = models.FileField(
        upload_to="recruitment_attachment", null=True, blank=True
    )
    objects = HorillaCompanyManager(related_company_field="recruitment_id__company_id")

    @property
    def answer(self):
        """
        Used to convert the json to dict
        """
        # Convert the JSON data to a dictionary
        try:
            return json.loads(self.answer_json)
        except json.JSONDecodeError:
            return {}  # Return an empty dictionary if JSON is invalid or empty

    def __str__(self) -> str:
        return f"{self.candidate_id.name}-{self.recruitment_id}"
