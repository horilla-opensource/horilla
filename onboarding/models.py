from django.db import models
from recruitment.models import Recruitment, Candidate
from employee.models import Employee
from django.utils.translation import gettext_lazy as _

class OnboardingStage(models.Model):
    stage_title = models.CharField(max_length=200)
    recruitment_id = models.ManyToManyField(Recruitment)
    employee_id = models.ManyToManyField(Employee)
    sequence = models.IntegerField(null=True)
    def __str__(self):
        return self.stage_title


class OnboardingTask(models.Model):
    task_title = models.CharField(max_length=200)
    recruitment_id = models.ManyToManyField(Recruitment, related_name='onboarding_task')
    employee_id = models.ManyToManyField(Employee)

    def __str__(self):
        return self.task_title
     

class CandidateStage(models.Model):
    candidate_id = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name='onboarding_stage')
    onboarding_stage_id = models.ForeignKey(
        OnboardingStage, on_delete=models.CASCADE, related_name='candidate')

    def __str__(self):
        return f"{self.candidate_id}  |  {self.onboarding_stage_id}"  


class CandidateTask(models.Model): 
    Choice = (                     
        ('', ''),
        ('ongoing', _('Ongoing')),
        ('stuck', _('Stuck')),
        ('done', _('Done')),
    )
    candidate_id = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='candidate_task')
    status = models.CharField(
        max_length=50, choices=Choice, blank=True, null=True)
    onboarding_task_id = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.candidate_id} | {self.onboarding_task_id} | {self.status}"
    
    class Meta:
        unique_together = ('candidate_id','onboarding_task_id')

     
class OnboardingPortal(models.Model):  
    candidate_id = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name='onboarding_portal')
    token = models.CharField(max_length=200)
    used = models.BooleanField(default=False) 
    count = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.candidate_id} | {self.token}'
