import django
from django.db import models
from django.contrib.auth.models import User
from employee.models import Employee
from base.models import JobPosition,Company
from simple_history.models import HistoricalRecords
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Create your models here.
import os

def validate_pdf(value):
    """
    This method is used to validate pdf
    """
    ext = os.path.splitext(value.name)[1]  # Get file extension
    if ext.lower() != '.pdf':
        raise ValidationError('File must be a PDF.')

def validate_image(value):
    return

class Recruitment(models.Model):
    description = models.TextField(null=True)
    job_position_id = models.ForeignKey(
        JobPosition, on_delete=models.CASCADE,  null=False, db_constraint=False, related_name='recruitment')
    vacancy = models.IntegerField(blank=True, null=True)
    recruitment_managers = models.ManyToManyField(Employee)
    company_id = models.ForeignKey(Company,on_delete=models.DO_NOTHING,null=True,blank=True)
    start_date = models.DateField(default=django.utils.timezone.now)
    end_date = models.DateField(blank=True, null=True)
    closed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    class Meta:
        unique_together = ('job_position_id','start_date',)
    def __str__(self):
        return f'{self.job_position_id.job_position} {self.start_date}'
    class Meta:
        permissions = (('archive_recruitment','Archive Recruitment'),)
        unique_together = ('job_position_id','start_date','company_id')
        unique_together = ('job_position_id','start_date',)
        

class Stage(models.Model):
    stage_types = [
        ('initial',_('Initial')),
        ('test',_('Test')),
        ('interview',_('Interview')),
        ('hired',_('Hired')),
    ]
    recruitment_id= models.ForeignKey(
        Recruitment, on_delete=models.CASCADE,related_name='stage_set')
    stage_managers= models.ManyToManyField(Employee,blank=True)
    stage = models.CharField(max_length=50 )
    stage_type = models.CharField(max_length=20,choices=stage_types,default='interview')
    sequence = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.stage
    
    class Meta:
        permissions = (('archive_Stage','Archive Stage'),)
        unique_together = ['recruitment_id','stage']
        
        
class Candidate(models.Model):
    choices = [('male',_('Male')),('female',_('Female')),('other',_('Other'))]
    name = models.CharField(max_length=100,null=True)
    profile = models.ImageField(upload_to='recruitment/profile',null=True,validators=[validate_image,])
    portfolio = models.URLField(max_length=200,blank=True)
    recruitment_id = models.ForeignKey(Recruitment, on_delete=models.CASCADE, blank=True, null=True,related_name='candidate')
    stage_id = models.ForeignKey(Stage,on_delete=models.CASCADE,null=True)
    schedule_date = models.DateTimeField(blank=True,null=True)
    email = models.EmailField(max_length=254,)
    mobile = models.CharField(max_length=15, blank=True)
    resume = models.FileField(upload_to='recruitment/resume',validators = [validate_pdf,])
    referral = models.ForeignKey(Employee, on_delete= models.CASCADE, null= True, blank=True,related_name='candidate_referral')
    address = models.TextField(null=True,blank=True)
    country = models.CharField(max_length=30,null=True,blank=True)
    dob = models.DateField(null=True,blank=True)
    state = models.CharField(max_length=30,null=True,blank=True)
    city = models.CharField(max_length=30,null=True,blank=True)
    zip = models.CharField(max_length=30,null=True,blank=True)
    gender =models.CharField(max_length=15,choices=choices,null=True)
    start_onboard = models.BooleanField(default=False)
    hired = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    joining_date = models.DateField(blank=True,null=True)
    history = HistoricalRecords(
        related_name='candidate_history',
    )


    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
            if self.stage_id is not None:
                if self.stage_id.stage_type == 'hired':
                    self.hired = True
            super().save(*args, **kwargs)
            
    class Meta:
        unique_together = ('email','recruitment_id',)
        permissions = (('view_history','View Candidate History'),('archive_candidate','Archive Candidate'))






class StageNote(models.Model):
    candidate_id = models.ForeignKey(Candidate,on_delete=models.CASCADE)
    title = models.CharField(max_length=50,null=True)
    description = models.TextField()
    stage_id = models.ForeignKey(Stage,on_delete=models.CASCADE)
    updated_by = models.ForeignKey(Employee,on_delete=models.CASCADE)
    
    def __str__(self) -> str:
        return self.description


