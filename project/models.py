"""
models.py

This module is used to register models for project app

"""
from django.db import models
from django.apps import apps
from employee.models import Employee
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from employee.models import Employee
from datetime import date



# Create your models here.

def validate_time_format(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 5:
        raise ValidationError(_("Invalid format, it should be HH:MM format"))
    try:
        hour, minute = value.split(":")
        
        if len(hour) < 2 or len(minute) < 2:
            raise ValidationError(_( "Invalid format, it should be HH:MM format"))
        
        minute = int(minute)
        if len(hour) > 2 or minute not in range(60):
            raise ValidationError(_("Invalid time"))
    except ValueError as error:
        raise ValidationError(_("Invalid format")) from error



class Project(models.Model):
    PROJECT_STATUS = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("on_hold", "On Hold"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]
    title = models.CharField(max_length=200, unique=True, verbose_name="Name")
    manager = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="project_manager",
        verbose_name="Project Manager",
    )
    members = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="project_members",
        verbose_name="Project Members",
    )
    status = models.CharField(choices=PROJECT_STATUS, max_length=250, default="new")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    document = models.FileField(
        upload_to="project/files", blank=True, null=True, verbose_name="Project File"
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField()
    objects = models.Manager()

    

    def clean(self) -> None:
        # validating end date 
        if self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValidationError({"document": "End date is less than start date"})
            if self.end_date < date.today():
                self.status = "expired"

    def __str__(self):
        return self.title
    


class ProjectStage(models.Model):
    """
    ProjectStage model
    """
    title = models.CharField(max_length=200)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="project_stages",
    )
    sequence = models.IntegerField(null=True,blank=True)
    is_end_stage = models.BooleanField(default=False)
   

    def __str__(self) -> str:
        return f"{self.title}"
    
    def clean(self) -> None:
        if self.is_end_stage:
            project = self.project
            existing_end_stage = project.project_stages.filter(is_end_stage = True).exclude(id = self.id)

            if existing_end_stage:
                end_stage = project.project_stages.filter(is_end_stage = True).first()
                raise ValidationError(
                    _(f"Already exist an end stage - {end_stage.title}.")
                    )
                
                    
    class Meta:
        """
        Meta class to add the additional info
        """

        unique_together = ["project", "title"]


class Task(models.Model):
    """
    Task model
    """
    TASK_STATUS = [
        ("to_do", "To Do"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("expired", "Expired"),
    ]
    title = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null = True, blank= True)
    stage = models.ForeignKey(
            ProjectStage,
            on_delete=models.CASCADE,
            null=True,
            blank=True,
            related_name="tasks",
            verbose_name="Project Stage",
            )
    task_manager = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,  
        verbose_name="Task Manager",
    )
    task_members = models.ManyToManyField(
        Employee, blank=True, related_name="tasks", verbose_name="Task Members"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(choices=TASK_STATUS, max_length=250, default="to_do")
    document = models.FileField(
        upload_to="task/files", blank=True, null=True, verbose_name="Task File"
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField()
    sequence = models.IntegerField(default=0)
    objects = models.Manager()


    def clean(self) -> None:
        if self.end_date is not None and self.project.end_date is not None:
            if (
                self.project.end_date < self.end_date
                or self.project.start_date > self.end_date
            ):
                raise ValidationError(
                    {"status": "End date must be between project start and end dates."}
                )
            if self.end_date < date.today():
                self.status = "expired"
    class Meta:
        """
        Meta class to add the additional info
        """
        unique_together = ["project", "title"]

    def __str__(self):
        return f"{self.title}"
    




class TimeSheet(models.Model):
    """
    TimeSheet model
    """
    TIME_SHEET_STATUS = [
        ("in_Progress", "In Progress"),
        ("completed", "Completed"),
    ]
    project_id = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="project_timesheet",
        verbose_name="Project",
    )
    task_id = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="task_timesheet",
        verbose_name="Task",
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        verbose_name="Employee",
    )
    date = models.DateField(default=timezone.now)
    time_spent = models.CharField(
        null=True,
        default="00:00",
        max_length=10,
        validators=[validate_time_format],
        verbose_name="Hours Spent",
    )
    status = models.CharField(
        choices=TIME_SHEET_STATUS, max_length=250, default="in_Progress"
    )
    description = models.TextField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        ordering = ("-id",)

    def clean(self):
        if self.project_id is None:
            raise ValidationError({"project_id": "Project name is Required."})
        if self.description is None or self.description == "":
            raise ValidationError(
                {"description": "Please provide a description to your Time sheet"}
            )

    def __str__(self):
        return f"{self.project_id} {self.date} {self.time_spent}"
