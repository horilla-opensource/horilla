from django import forms
from django.utils.translation import gettext_lazy as _
from .models import *
from payroll.forms.forms import ModelForm
from django.template.loader import render_to_string


class ProjectForm(ModelForm):
    """
    Form for Project model
    """
    class Meta:
        """
        Meta class to add the additional info
        """

        model = Project
        fields = "__all__"
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ProjectTimeSheetForm(ModelForm):
    """
    Form for Project model in Time sheet form
    """
    def __init__(self, *args, **kwargs):
        super(ProjectTimeSheetForm, self).__init__(*args, **kwargs)
        self.fields["status"].widget.attrs.update(
            {
                "style": "width: 100%; height: 47px;",
                "class": "oh-select",
            }
        )
    def __init__(self, *args, request=None, **kwargs):
        super(ProjectTimeSheetForm, self).__init__(*args, **kwargs)
        self.fields["manager"].widget.attrs.update({"id":"manager_id"})
        self.fields["status"].widget.attrs.update({"id":"status_id"})
        self.fields["members"].widget.attrs.update({"id":"members_id"})
        self.fields['title'].widget.attrs.update({'id':'id_project'})

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Project
        fields = "__all__"
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }



class TaskForm(ModelForm):
    """
    Form for Task model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"
        # exclude = ("project_id",)

        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "project":forms.HiddenInput(),
            "stage":forms.HiddenInput(),
            "sequence":forms.HiddenInput()
            }
        
class TaskFormCreate(ModelForm):
    
    """
    Form for Task model in create button inside task view
    """
    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"
        # exclude = ("project_id",)

        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "project":forms.HiddenInput(),
            "sequence":forms.HiddenInput(),
            "stage": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                    "onchange": "keyResultChange($(this))",
                }
            ),
            }
        
    def __init__(self, *args, request=None, **kwargs):
        super(TaskFormCreate, self).__init__(*args, **kwargs)
        self.fields["stage"].widget.attrs.update({"id":"project_stage"})

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html
        
class TaskAllForm(ModelForm):
    """
    Form for Task model in task all view
    """
    class Meta:
        """
        Meta class to add the additional info
        """
        model = Task
        fields = "__all__"

        widgets= {
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "sequence":forms.HiddenInput()
        }
    def __init__(self, *args, request=None, **kwargs):
        super(TaskAllForm, self).__init__(*args, **kwargs)
        self.fields["project"].choices = list(self.fields["project"].choices)
        self.fields["project"].choices.append(
                ("create_new_project", "Create a new project")
            )
        # Remove the select2 class from the "project" field
        # self.fields["project"].widget.attrs.pop("class", None)
        # self.fields["stage"].widget.attrs.pop("class", None)
        self.fields["stage"].widget.attrs.update({"id":"project_stage"})



class TimeSheetForm(ModelForm):
    """
    Form for Time Sheet model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = TimeSheet
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, request=None, **kwargs):
        super(TimeSheetForm, self).__init__(*args, **kwargs)
        if request:
            if not request.user.has_perm("project.add_timesheet"):
                employee = Employee.objects.filter(employee_user_id=request.user)
                employee_list = Employee.objects.filter(employee_work_info__reporting_manager_id=employee.first())
                self.fields["employee_id"].queryset = employee_list | employee
                if len(employee_list) == 0:
                    self.fields["employee_id"].widget = forms.HiddenInput()
            self.fields['project_id'].widget.attrs.update({'id':'id_project'})
            self.fields["project_id"].choices = list(self.fields["project_id"].choices)
            self.fields["project_id"].choices.append(
                ("create_new_project", "Create a new project")
            )

class TimesheetInTaskForm(ModelForm):
    class Meta:
        """
        Meta class to add the additional info
        """
        model = TimeSheet
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "project_id":forms.HiddenInput(),
            "task_id":forms.HiddenInput(),
        }

class ProjectStageForm(ModelForm):
    """
    Form for Project stage model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = ProjectStage
        fields = "__all__"
        # exclude = ("project",)

        widgets = {
            "project":forms.HiddenInput(),
            'sequence':forms.HiddenInput()
            }
        
class TaskTimeSheetForm(ModelForm):
    """
    Form for Task model in timesheet form
    """
    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"
        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "project": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(TaskTimeSheetForm, self).__init__(*args, **kwargs)
        # Add style to the start_date and end_date fields
        # self.fields["stage"].choices.append(
        #         ("create_new_project", "Create a new project")
        #     )
        self.fields["status"].widget.attrs.update(
            {
                "style": "width: 100%; height: 47px;",
                "class": "oh-select",
                
            }
        )
        self.fields["description"].widget.attrs.update(
            {
                "style": "width: 100%; height: 130px;",
                "class": "oh-select",
            }
        )
        self.fields["description"].widget.attrs.update(
            {
                "style": "width: 100%; height: 130px;",
                "class": "oh-select",
            }
        )
        
        self.fields["stage"].widget.attrs.update(
            {
                "id":'project_stage'
            }
        )



    
        
