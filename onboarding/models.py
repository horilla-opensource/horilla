"""
models.py

This module is used to register models for onboarding app

"""
from datetime import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from recruitment.models import Recruitment, Candidate
from employee.models import Employee
from base.horilla_company_manager import HorillaCompanyManager


class OnboardingStage(models.Model):
    """
    OnboardingStage models
    """

    stage_title = models.CharField(max_length=200)
    recruitment_id = models.ManyToManyField(Recruitment)
    employee_id = models.ManyToManyField(Employee)
    sequence = models.IntegerField(null=True)
    is_final_stage = models.BooleanField(default=False)
    objects = HorillaCompanyManager("recruitment_id__company_id")

    def __str__(self):
        return f"{self.stage_title}"

    class Meta:
        """
        Meta class for additional options
        """

        ordering = ["sequence"]


class OnboardingTask(models.Model):
    """
    OnboardingTask models
    """

    task_title = models.CharField(max_length=200)
    recruitment_id = models.ManyToManyField(Recruitment, related_name="onboarding_task")
    employee_id = models.ManyToManyField(Employee)
    objects = HorillaCompanyManager("recruitment_id__company_id")


    def __str__(self):
        return f"{self.task_title}"


class CandidateStage(models.Model):
    """
    CandidateStage model
    """

    candidate_id = models.OneToOneField(
        Candidate, on_delete=models.PROTECT, related_name="onboarding_stage"
    )
    onboarding_stage_id = models.ForeignKey(
        OnboardingStage, on_delete=models.PROTECT, related_name="candidate"
    )
    onboarding_end_date = models.DateField(blank=True, null=True)
    sequence = models.IntegerField(null=True, default=0)
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")


    def __str__(self):
        return f"{self.candidate_id}  |  {self.onboarding_stage_id}"

    def save(self, *args, **kwargs):
        if self.onboarding_stage_id.is_final_stage:
            self.onboarding_end_date = datetime.today()
        super(CandidateStage, self).save(*args, **kwargs)

    class Meta:
        """
        Meta class for additional options
        """

        verbose_name = _("Candidate Onboarding stage")
        ordering = ["sequence"]


class CandidateTask(models.Model):
    """
    CandidateTask model
    """

    choice = (
        ("", ""),
        ("todo", _("Todo")),
        ("scheduled", _("Scheduled")),
        ("ongoing", _("Ongoing")),
        ("stuck", _("Stuck")),
        ("done", _("Done")),
    )
    candidate_id = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, related_name="candidate_task"
    )
    status = models.CharField(max_length=50, choices=choice, blank=True, null=True)
    onboarding_task_id = models.ForeignKey(OnboardingTask, on_delete=models.PROTECT)
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")


    def __str__(self):
        return f"{self.candidate_id} | {self.onboarding_task_id} | {self.status}"

    class Meta:
        """
        Meta class to add some additional options
        """

        verbose_name = _("Candidate onboarding task")
        unique_together = ("candidate_id", "onboarding_task_id")


class OnboardingPortal(models.Model):
    """
    OnboardingPortal model
    """

    candidate_id = models.OneToOneField(
        Candidate, on_delete=models.PROTECT, related_name="onboarding_portal"
    )
    token = models.CharField(max_length=200)
    used = models.BooleanField(default=False)
    count = models.IntegerField(default=0)
    objects = HorillaCompanyManager("candidate_id__recruitment_id__company_id")


    def __str__(self):
        return f"{self.candidate_id} | {self.token}"
