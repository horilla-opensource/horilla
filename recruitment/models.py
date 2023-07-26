"""
models.py

This module is used to register models for recruitment app

"""
import os
import django
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from employee.models import Employee
from base.models import JobPosition, Company

# Create your models here.


def validate_pdf(value):
    """
    This method is used to validate pdf
    """
    ext = os.path.splitext(value.name)[1]  # Get file extension
    if ext.lower() != ".pdf":
        raise ValidationError("File must be a PDF.")


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
    is_event_based = models.BooleanField(default=False)
    open_positions = models.ManyToManyField(
        JobPosition, related_name="open_positions", blank=True
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="recruitment",
        verbose_name="Job Position",
    )
    vacancy = models.IntegerField(blank=True, null=True)
    recruitment_managers = models.ManyToManyField(Employee)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name="Company",
    )
    start_date = models.DateField(default=django.utils.timezone.now)
    end_date = models.DateField(blank=True, null=True)
    closed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    objects = models.Manager()

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
            raise ValidationError({"title": "This field is required"})
        if not self.is_event_based and self.job_position_id is None:
            raise ValidationError({"job_position_id": "This field is required"})
        return super().clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the Recruitment instance first
        if self.is_event_based and self.open_positions is None:
            raise ValidationError({"open_positions": "This field is required"})


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
        verbose_name="Recruitment",
    )
    stage_managers = models.ManyToManyField(Employee, blank=True)
    stage = models.CharField(max_length=50)
    stage_type = models.CharField(
        max_length=20, choices=stage_types, default="interview"
    )
    sequence = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.stage}"

    class Meta:
        """
        Meta class to add the additional info
        """

        permissions = (("archive_Stage", "Archive Stage"),)
        unique_together = ["recruitment_id", "stage"]


class Candidate(models.Model):
    """
    Candidate model
    """

    choices = [("male", _("Male")), ("female", _("Female")), ("other", _("Other"))]
    name = models.CharField(max_length=100, null=True)
    profile = models.ImageField(
        upload_to="recruitment/profile",
        null=True,
    )
    portfolio = models.URLField(max_length=200, blank=True)
    recruitment_id = models.ForeignKey(
        Recruitment,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="candidate",
        verbose_name="Recruitment",
    )
    job_position_id = models.ForeignKey(
        JobPosition, on_delete=models.CASCADE, null=True, blank=True
    )
    stage_id = models.ForeignKey(
        Stage, on_delete=models.CASCADE, null=True, verbose_name="Stage"
    )
    schedule_date = models.DateTimeField(blank=True, null=True)
    email = models.EmailField(
        max_length=254,
        unique=True,
    )
    mobile = models.CharField(max_length=15, blank=True)
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
    )
    address = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=30, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=30, null=True, blank=True)
    city = models.CharField(max_length=30, null=True, blank=True)
    zip = models.CharField(max_length=30, null=True, blank=True)
    gender = models.CharField(max_length=15, choices=choices, null=True)
    start_onboard = models.BooleanField(default=False)
    hired = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    joining_date = models.DateField(blank=True, null=True)
    history = HistoricalRecords(
        related_name="candidate_history",
    )
    sequence = models.IntegerField(null=True,default=0)
    objects = models.Manager()

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        # Check if the 'stage_id' attribute is not None
        if self.stage_id is not None:
            # Check if the stage type is 'hired'
            if self.stage_id.stage_type == "hired":
                self.hired = True
        if not self.recruitment_id.is_event_based and self.job_position_id is None:
            self.job_position_id = self.recruitment_id.job_position_id
        if self.job_position_id not in self.recruitment_id.open_positions.all():
            raise ValidationError({"job_position_id": "Choose valid choice"})
        if self.recruitment_id.is_event_based and self.job_position_id is None:
            raise ValidationError({"job_position_id": "This field is required."})
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
    title = models.CharField(max_length=50, null=True)
    description = models.TextField()
    stage_id = models.ForeignKey(Stage, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(Employee, on_delete=models.CASCADE)
    objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.description}"
