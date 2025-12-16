"""
models.py

This module is used to register models for recruitment app

"""

import json
import os
import re
from uuid import uuid4

import django
import requests
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, JobPosition
from employee.models import Employee
from horilla.models import HorillaModel, upload_path
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from horilla_views.cbv_methods import render_template

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


def candidate_photo_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{instance.name.replace(' ', '_')}_{filename}_{uuid4()}.{ext}"
    return os.path.join("recruitment/profile/", filename)


class SurveyTemplate(HorillaModel):
    """
    SurveyTemplate Model
    """

    title = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    is_general_template = models.BooleanField(default=False, editable=False)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    objects = HorillaCompanyManager("company_id")

    def __str__(self) -> str:
        return self.title

    class Meta:
        verbose_name = _("Survey Template")
        verbose_name_plural = _("Survey Templates")


class Skill(HorillaModel):
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        title = self.title
        self.title = title.capitalize()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")


class Recruitment(HorillaModel):
    """
    Recruitment model
    """

    title = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Title")
    )
    description = models.TextField(null=True, verbose_name=_("Description"))
    is_event_based = models.BooleanField(
        default=False,
        help_text=_("To start recruitment for multiple job positions"),
    )
    closed = models.BooleanField(
        default=False,
        help_text=_(
            "To close the recruitment, If closed then not visible on pipeline view."
        ),
        verbose_name=_("Closed"),
    )
    is_published = models.BooleanField(
        default=True,
        help_text=_(
            "To publish a recruitment in website, if false then it \
            will not appear on open recruitment page."
        ),
        verbose_name=_("Is Published"),
    )
    open_positions = models.ManyToManyField(
        JobPosition,
        related_name="open_positions",
        blank=True,
        verbose_name=_("Job Position"),
    )
    job_position_id = models.ForeignKey(
        JobPosition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="recruitment",
        verbose_name=_("Job Position"),
        editable=False,
    )
    vacancy = models.IntegerField(default=0, null=True, verbose_name=_("Vacancy"))
    recruitment_managers = models.ManyToManyField(Employee, verbose_name=_("Managers"))
    survey_templates = models.ManyToManyField(
        SurveyTemplate, blank=True, verbose_name=_("Survey Templates")
    )
    company_id = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    start_date = models.DateField(
        default=django.utils.timezone.now, verbose_name=_("Start Date")
    )
    end_date = models.DateField(blank=True, null=True, verbose_name=_("End Date"))
    skills = models.ManyToManyField(Skill, blank=True, verbose_name=_("Skills"))
    linkedin_account_id = models.ForeignKey(
        "recruitment.LinkedInAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("LinkedIn Account"),
    )
    linkedin_post_id = models.CharField(max_length=150, null=True, blank=True)
    publish_in_linkedin = models.BooleanField(
        default=True,
        help_text=_(
            "To publish a recruitment in Linkedin, if active is false then it \
            will not post on LinkedIn."
        ),
        verbose_name=_("Post on LinkedIn"),
    )
    objects = HorillaCompanyManager()
    default = models.manager.Manager()
    optional_profile_image = models.BooleanField(
        default=False,
        help_text=_("Profile image not mandatory for candidate creation"),
        verbose_name=_("Optional Profile Image"),
    )
    optional_resume = models.BooleanField(
        default=False,
        help_text=_("Resume not mandatory for candidate creation"),
        verbose_name=_("Optional Resume"),
    )

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
        verbose_name = _("Recruitment")
        verbose_name_plural = _("Recruitments")

    def total_hires(self):
        """
        This method is used to get the count of
        hired candidates
        """
        return self.candidate.filter(hired=True).count()

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
        if self.is_published:
            if self.vacancy <= 0:
                raise ValidationError(
                    _(
                        "Vacancy must be greater than zero if the recruitment is publishing."
                    )
                )

        if self.end_date is not None and (
            self.start_date is not None and self.start_date > self.end_date
        ):
            raise ValidationError(
                {"end_date": _("End date cannot be less than start date.")}
            )
        return super().clean()

    def save(self, *args, **kwargs):
        if not self.publish_in_linkedin:
            self.linkedin_account_id = None
            self.linkedin_post_id = None
        super().save(*args, **kwargs)  # Save the Recruitment instance first
        if self.is_event_based and self.open_positions is None:
            raise ValidationError({"open_positions": _("This field is required")})

    def ordered_stages(self):
        """
        This method will returns all the stage respectively to the ascending order of stages
        """
        return self.stage_set.order_by("sequence")

    def is_vacancy_filled(self):
        """
        This method is used to check wether the vaccancy for the recruitment is completed or not
        """
        hired_stage = Stage.objects.filter(
            recruitment_id=self, stage_type="hired"
        ).first()
        if hired_stage:
            hired_candidate = hired_stage.candidate_set.all().exclude(canceled=True)
            if len(hired_candidate) >= self.vacancy:
                return True


class Stage(HorillaModel):
    """
    Stage model
    """

    stage_types = [
        ("initial", _("Initial")),
        ("applied", _("Applied")),
        ("test", _("Test")),
        ("interview", _("Interview")),
        ("cancelled", _("Cancelled")),
        ("hired", _("Hired")),
    ]
    recruitment_id = models.ForeignKey(
        Recruitment,
        on_delete=models.CASCADE,
        related_name="stage_set",
        verbose_name=_("Recruitment"),
    )
    stage_managers = models.ManyToManyField(Employee, verbose_name=_("Stage Managers"))
    stage = models.CharField(max_length=50, verbose_name=_("Stage"))
    stage_type = models.CharField(
        max_length=20,
        choices=stage_types,
        default="interview",
        verbose_name=_("Stage Type"),
    )
    sequence = models.IntegerField(null=True, default=0)
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
        verbose_name = _("Stage")
        verbose_name_plural = _("Stages")

    def __str__(self):
        return f"{self.stage} - ({self.recruitment_id.title})"

    def active_candidates(self):
        """
        This method is used to get all the active candidate like related objects
        """
        return {
            "all": Candidate.objects.filter(
                stage_id=self, canceled=False, is_active=True
            )
        }


def candidate_upload_path(instance, filename):
    """
    Generates a unique file path for candidate profile & resume uploads.
    """
    ext = filename.split(".")[-1]
    name_slug = slugify(instance.name) or "candidate"
    unique_filename = f"{name_slug}-{uuid4().hex[:8]}.{ext}"
    return f"recruitment/{name_slug}/{unique_filename}"


class Candidate(HorillaModel):
    """
    Candidate model
    """

    choices = [("male", _("Male")), ("female", _("Female")), ("other", _("Other"))]
    offer_letter_statuses = [
        ("not_sent", _("Not Sent")),
        ("sent", _("Sent")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        ("joined", _("Joined")),
    ]
    source_choices = [
        ("application", _("Application Form")),
        ("software", _("Inside software")),
        ("other", _("Other")),
    ]
    name = models.CharField(max_length=100, null=True, verbose_name=_("Name"))
    profile = models.ImageField(upload_to=upload_path, null=True)  # 853
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
    converted_employee_id = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="candidate_get",
        verbose_name=_("Employee"),
    )
    schedule_date = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Schedule date")
    )
    email = models.EmailField(max_length=254, verbose_name=_("Email"))
    mobile = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            validate_mobile,
        ],
        verbose_name=_("Mobile"),
    )
    resume = models.FileField(
        upload_to=upload_path,  # 853
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
    address = models.TextField(
        null=True, blank=True, verbose_name=_("Address"), max_length=255
    )
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
        max_length=15,
        choices=choices,
        null=True,
        default="male",
        verbose_name=_("Gender"),
    )
    source = models.CharField(
        max_length=20,
        choices=source_choices,
        null=True,
        blank=True,
        verbose_name=_("Source"),
    )
    start_onboard = models.BooleanField(default=False, verbose_name=_("Start Onboard"))
    hired = models.BooleanField(default=False, verbose_name=_("Hired"))
    canceled = models.BooleanField(default=False, verbose_name=_("Canceled"))
    converted = models.BooleanField(default=False, verbose_name=_("Converted"))
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

    probation_end = models.DateField(null=True, editable=False)
    offer_letter_status = models.CharField(
        max_length=10,
        choices=offer_letter_statuses,
        default="not_sent",
        editable=False,
        verbose_name=_("Offer Letter Status"),
    )
    objects = HorillaCompanyManager(related_company_field="recruitment_id__company_id")
    last_updated = models.DateField(null=True, auto_now=True)

    converted_employee_id.exclude_from_automation = True
    mail_to_related_fields = [
        ("stage_id__stage_managers__get_mail", "Stage Managers"),
        ("recruitment_id__recruitment_managers__get_mail", "Recruitment Managers"),
    ]
    hired_date = models.DateField(null=True, blank=True, editable=False)

    def __str__(self):
        return f"{self.name}"

    def is_offer_rejected(self):
        """
        Is offer rejected checking method
        """
        first = RejectedCandidate.objects.filter(candidate_id=self).first()
        if first:
            return first.reject_reason_id.count() > 0
        return first

    def get_full_name(self):
        """
        Method will return employee full name
        """
        return str(self.name)

    def get_avatar(self):
        """
        Method will rerun the api to the avatar or path to the profile image
        """
        if self.profile and default_storage.exists(self.profile.name):
            return self.profile.url
        return static("images/ui/default_avatar.jpg")

    def get_company(self):
        """
        This method is used to return the company
        """
        return getattr(
            getattr(getattr(self, "recruitment_id", None), "company_id", None),
            "company",
            None,
        )

    def get_job_position(self):
        """
        This method is used to return the job position of the candidate
        """
        return self.job_position_id.job_position

    def get_email(self):
        """
        Return email
        """
        return self.email

    def get_mail(self):
        """ """
        return self.get_email()

    def phone(self):
        return self.mobile

    def tracking(self):
        """
        This method is used to return the tracked history of the instance
        """
        return get_diff(self)

    def get_last_sent_mail(self):
        """
        This method is used to get last send mail
        """
        from base.models import EmailLog

        return (
            EmailLog.objects.filter(to__icontains=self.email)
            .order_by("-created_at")
            .first()
        )

    def get_interview(self):
        """
        This method is used to get the interview dates and times
        for the candidate for the mail templates
        """

        interviews = InterviewSchedule.objects.filter(candidate_id=self.id)
        if interviews:
            interview_info = "<table>"
            interview_info += "<tr><th>Sl No.</th><th>Date</th><th>Time</th><th>Is Completed</th></tr>"
            for index, interview in enumerate(interviews, start=1):
                interview_info += f"<tr><td>{index}</td>"
                interview_info += (
                    f"<td class='dateformat_changer'>{interview.interview_date}</td>"
                )
                interview_info += (
                    f"<td class='timeformat_changer'>{interview.interview_time}</td>"
                )
                interview_info += (
                    f"<td>{'Yes' if interview.completed else 'No'}</td></tr>"
                )
            interview_info += "</table>"
            return interview_info
        else:
            return ""

    def save(self, *args, **kwargs):
        if self.stage_id is not None:
            self.hired = self.stage_id.stage_type == "hired"

        if not self.recruitment_id.is_event_based and self.job_position_id is None:
            self.job_position_id = self.recruitment_id.job_position_id
        if self.job_position_id not in self.recruitment_id.open_positions.all():
            raise ValidationError({"job_position_id": _("Choose valid choice")})
        if self.recruitment_id.is_event_based and self.job_position_id is None:
            raise ValidationError({"job_position_id": _("This field is required.")})
        if self.stage_id and self.stage_id.stage_type == "cancelled":
            self.canceled = True
        if self.canceled:
            cancelled_stage = Stage.objects.filter(
                recruitment_id=self.recruitment_id, stage_type="cancelled"
            ).first()
            if not cancelled_stage:
                cancelled_stage = Stage.objects.create(
                    recruitment_id=self.recruitment_id,
                    stage="Cancelled Candidates",
                    stage_type="cancelled",
                    sequence=50,
                )
            self.stage_id = cancelled_stage
        if (
            self.converted_employee_id
            and Candidate.objects.filter(
                converted_employee_id=self.converted_employee_id
            )
            .exclude(id=self.id)
            .exists()
        ):
            raise ValidationError(_("Employee is uniques for candidate"))

        if self.converted:
            self.hired = False
            self.canceled = False

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
        verbose_name = _("Candidate")
        verbose_name_plural = _("Candidates")


class RejectReason(HorillaModel):
    """
    RejectReason
    """

    title = models.CharField(
        max_length=50,
    )
    description = models.TextField(null=True, blank=True, max_length=255)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    objects = HorillaCompanyManager()

    def __str__(self) -> str:
        return self.title

    class Meta:
        verbose_name = _("Reject Reason")
        verbose_name_plural = _("Reject Reasons")


class RejectedCandidate(HorillaModel):
    """
    RejectedCandidate
    """

    candidate_id = models.OneToOneField(
        Candidate,
        on_delete=models.PROTECT,
        verbose_name="Candidate",
        related_name="rejected_candidate",
    )
    reject_reason_id = models.ManyToManyField(
        RejectReason, verbose_name="Reject reason", blank=True
    )
    description = models.TextField(max_length=255)
    objects = HorillaCompanyManager(
        related_company_field="candidate_id__recruitment_id__company_id"
    )
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )

    class Meta:
        verbose_name = _("Rejected Candidate")
        verbose_name_plural = _("Rejected Candidates")

    def __str__(self) -> str:
        reasons = ", ".join(self.reject_reason_id.values_list("title", flat=True))
        return f"{self.candidate_id} - {reasons if reasons else 'No Reason'}"


class StageFiles(HorillaModel):
    files = models.FileField(upload_to=upload_path, blank=True, null=True)

    def __str__(self):
        return self.files.name.split("/")[-1]


class StageNote(HorillaModel):
    """
    StageNote model
    """

    candidate_id = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    description = models.TextField(verbose_name=_("Description"))  # 905
    stage_id = models.ForeignKey(Stage, on_delete=models.CASCADE)
    stage_files = models.ManyToManyField(StageFiles, blank=True)
    updated_by = models.ForeignKey(
        Employee, on_delete=models.CASCADE, null=True, blank=True
    )
    candidate_can_view = models.BooleanField(default=False)
    objects = HorillaCompanyManager(
        related_company_field="candidate_id__recruitment_id__company_id"
    )

    def __str__(self) -> str:
        return f"{self.description}"

    def updated_user(self):
        if self.updated_by:
            return self.updated_by
        else:
            return self.candidate_id


class RecruitmentSurvey(HorillaModel):
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
    question = models.TextField(null=False, max_length=255)
    template_id = models.ManyToManyField(
        SurveyTemplate, verbose_name="Template", blank=True
    )
    is_mandatory = models.BooleanField(default=False)
    recruitment_ids = models.ManyToManyField(
        Recruitment,
        verbose_name=_("Recruitment"),
    )
    question = models.TextField(null=False)
    job_position_ids = models.ManyToManyField(
        JobPosition, verbose_name=_("Job Positions"), editable=False
    )
    sequence = models.IntegerField(null=True, default=0)
    type = models.CharField(
        max_length=15,
        choices=question_types,
    )
    options = models.TextField(
        null=True, default="", help_text=_("Separate choices by ',  '"), max_length=255
    )
    objects = HorillaCompanyManager(related_company_field="recruitment_ids__company_id")

    def __str__(self) -> str:
        return str(self.question)

    def choices(self):
        """
        Used to split the choices
        """
        return self.options.split(", ")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.template_id is None:
            general_template = SurveyTemplate.objects.filter(
                is_general_template=True
            ).first()
            if general_template:
                self.template_id.add(general_template)
                super().save(*args, **kwargs)

    class Meta:
        ordering = [
            "sequence",
        ]


class QuestionOrdering(HorillaModel):
    """
    Survey Template model
    """

    question_id = models.ForeignKey(RecruitmentSurvey, on_delete=models.CASCADE)
    recruitment_id = models.ForeignKey(Recruitment, on_delete=models.CASCADE)
    sequence = models.IntegerField(default=0)
    objects = HorillaCompanyManager(related_company_field="recruitment_ids__company_id")


class RecruitmentSurveyAnswer(HorillaModel):
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
    attachment = models.FileField(upload_to=upload_path, null=True, blank=True)
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


class SkillZone(HorillaModel):
    """ "
    Model for talent pool
    """

    title = models.CharField(max_length=50, verbose_name="Skill Zone")
    description = models.TextField(verbose_name=_("Description"), max_length=255)
    company_id = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Company"),
    )
    objects = HorillaCompanyManager()

    class Meta:
        verbose_name = _("Skill Zone")
        verbose_name_plural = _("Skill Zones")

    def get_active(self):
        return SkillZoneCandidate.objects.filter(is_active=True, skill_zone_id=self)

    def __str__(self) -> str:
        return self.title


class SkillZoneCandidate(HorillaModel):
    """
    Model for saving candidate data's for future recruitment
    """

    skill_zone_id = models.ForeignKey(
        SkillZone,
        verbose_name=_("Skill Zone"),
        related_name="skillzonecandidate_set",
        on_delete=models.PROTECT,
        null=True,
    )
    candidate_id = models.ForeignKey(
        Candidate,
        on_delete=models.PROTECT,
        null=True,
        related_name="skillzonecandidate_set",
        verbose_name=_("Candidate"),
    )
    # job_position_id=models.ForeignKey(
    #     JobPosition,
    #     on_delete=models.PROTECT,
    #     null=True,
    #     related_name="talent_pool",
    #     verbose_name=_("Job Position")
    # )

    reason = models.CharField(max_length=200, verbose_name=_("Reason"))
    added_on = models.DateField(auto_now_add=True)
    objects = HorillaCompanyManager(
        related_company_field="candidate_id__recruitment_id__company_id"
    )

    def clean(self):
        # Check for duplicate entries in the database
        duplicate_exists = (
            SkillZoneCandidate.objects.filter(
                candidate_id=self.candidate_id, skill_zone_id=self.skill_zone_id
            )
            .exclude(pk=self.pk)
            .exists()
        )

        if duplicate_exists:
            raise ValidationError(
                _(
                    f"Candidate {self.candidate_id} already exists in Skill Zone {self.skill_zone_id}."
                )
            )

        super().clean()

    def __str__(self) -> str:
        return str(self.candidate_id.get_full_name())


class CandidateRating(HorillaModel):
    employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="candidate_rating"
    )
    candidate_id = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, related_name="candidate_rating"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    class Meta:
        unique_together = ["employee_id", "candidate_id"]

    def __str__(self) -> str:
        return f"{self.employee_id} - {self.candidate_id} rating {self.rating}"


class RecruitmentGeneralSetting(HorillaModel):
    """
    RecruitmentGeneralSettings model
    """

    candidate_self_tracking = models.BooleanField(default=False)
    show_overall_rating = models.BooleanField(default=False)
    company_id = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)


class InterviewSchedule(HorillaModel):
    """
    Interview Scheduling Model
    """

    candidate_id = models.ForeignKey(
        Candidate,
        verbose_name=_("Candidate"),
        related_name="candidate_interview",
        on_delete=models.CASCADE,
    )
    employee_id = models.ManyToManyField(Employee, verbose_name=_("Interviewer"))
    interview_date = models.DateField(verbose_name=_("Interview Date"))
    interview_time = models.TimeField(verbose_name=_("Interview Time"))
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
    )
    completed = models.BooleanField(
        default=False, verbose_name=_("Is Interview Completed")
    )
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")

    def __str__(self) -> str:
        return f"{self.candidate_id} -Interview."

    class Meta:
        verbose_name = _("Schedule Interview")
        verbose_name_plural = _("Schedule Interviews")


class Resume(models.Model):
    file = models.FileField(
        upload_to=upload_path,
        validators=[
            validate_pdf,
        ],
    )
    recruitment_id = models.ForeignKey(
        Recruitment, on_delete=models.CASCADE, related_name="resume"
    )
    is_candidate = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.recruitment_id} - Resume {self.pk}"


STATUS = [
    ("requested", "Requested"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]

FORMATS = [
    ("any", "Any"),
    ("pdf", "PDF"),
    ("txt", "TXT"),
    ("docx", "DOCX"),
    ("xlsx", "XLSX"),
    ("jpg", "JPG"),
    ("png", "PNG"),
    ("jpeg", "JPEG"),
]


class CandidateDocumentRequest(HorillaModel):
    title = models.CharField(max_length=100)
    candidate_id = models.ManyToManyField(Candidate)
    format = models.CharField(choices=FORMATS, max_length=10)
    max_size = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self):
        return self.title


class CandidateDocument(HorillaModel):
    title = models.CharField(max_length=250)
    candidate_id = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, verbose_name="Candidate"
    )
    document_request_id = models.ForeignKey(
        CandidateDocumentRequest, on_delete=models.PROTECT, null=True
    )
    document = models.FileField(upload_to=upload_path, null=True)
    status = models.CharField(choices=STATUS, max_length=10, default="requested")
    reject_reason = models.TextField(blank=True, null=True, max_length=255)

    def __str__(self):
        return f"{self.candidate_id} - {self.title}"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        file = self.document

        if len(self.title) < 3:
            raise ValidationError({"title": _("Title must be at least 3 characters")})

        if file and self.document_request_id:
            format = self.document_request_id.format
            max_size = self.document_request_id.max_size
            if max_size:
                if file.size > max_size * 1024 * 1024:
                    raise ValidationError(
                        {"document": _("File size exceeds the limit")}
                    )

            ext = file.name.split(".")[1].lower()
            if format == "any":
                pass
            elif ext != format:
                raise ValidationError(
                    {"document": _("Please upload {} file only.").format(format)}
                )


class LinkedInAccount(HorillaModel):
    username = models.CharField(max_length=250, verbose_name=_("App Name"))
    email = models.EmailField(max_length=254, verbose_name=_("Email"))
    api_token = models.CharField(max_length=500, verbose_name=_("API Token"))
    sub_id = models.CharField(max_length=250, unique=True)
    company_id = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, verbose_name=_("Company")
    )

    class Meta:
        verbose_name = _("LinkedIn Account")
        verbose_name_plural = _("LinkedIn Accounts")

    def __str__(self):
        return str(self.username)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if not data["email"] == self.email:
                raise ValidationError({"email": _("Email mismatched.")})
            self.sub_id = response.json()["sub"]
        else:
            raise ValidationError(_("Check the credentials"))

    def action_template(self):
        """
        This method for get custom column for managers.
        """
        return render_template(
            path="linkedin/linkedin_action.html",
            context={"instance": self},
        )

    def is_active_toggle(self):
        """
        For toggle is_active field
        """
        url = f"update-isactive-linkedin-account/{self.id}"
        return render_template(
            path="is_active_toggle.html",
            context={"instance": self, "url": url},
        )
