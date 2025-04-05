from django.db import models
from employee.models import Employee
from django.utils.translation import gettext_lazy as _
#by sambhav this project app
class Project(models.Model):
    name = models.CharField(max_length=255 , blank=False, null=False)
    # description = models.TextField(blank=True)
    start_date = models.DateField(blank=False, null=False)
    end_date = models.DateField(blank=True, null=True)
    status_choices = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='planning')
    project_owner = models.ForeignKey(Employee, on_delete=models.CASCADE,blank=True, null=True, related_name='managed_projects')
    team_members = models.ManyToManyField(Employee, related_name='assigned_projects')
    description1 = models.TextField(max_length=255, blank=False, null=False)
    # Financial fields hai yeh
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=False, null=False)
    attachment = models.FileField(upload_to='project_attachments/',blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return self.name

