from django.db import models
from employee.models import Employee
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
#by sambhav this project app


def validate_file_extension(value):
    file_name = value.name.lower()
    allowed_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', 
        '.doc', '.docx',                          
        '.xls', '.xlsx',                          
        '.pdf',                                   
        '.ppt', '.pptx'                           
    )

    if not any(file_name.endswith(ext) for ext in allowed_extensions):
        raise ValidationError("Only image, DOC/DOCX, XLS/XLSX, PDF, and PPT/PPTX files are allowed.")
class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('fix_price', 'Fix Price Contract'),
        ('monthly_retainer', 'Monthly Retainer'),
        ('body_shopping', 'Body Shopping'),
    ]

    name = models.CharField(max_length=255 , blank=False, null=False)
    start_date = models.DateField(blank=False, null=False)
    end_date = models.DateField(blank=True, null=True)
    status_choices = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold')
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='planning')
    project_owner = models.ForeignKey(Employee, on_delete=models.CASCADE, blank=True, null=True, related_name='managed_projects')
    team_members = models.ManyToManyField(Employee, related_name='assigned_projects')
    description1 = models.TextField(max_length=255, blank=False, null=False)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=False, null=False)
    attachment = models.FileField(upload_to='project_attachments/', blank=True, null=True, validators=[validate_file_extension])
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES, default='fix_price')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
