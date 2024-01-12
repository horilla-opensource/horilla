"""
forms.py

This module contains the form classes used in the application.

Each form represents a specific functionality or data input in the 
application. They are responsible for validating
and processing user input data.

Classes:
- YourForm: Represents a form for handling specific data input.

Usage:
from django import forms

class YourForm(forms.Form):
    field_name = forms.CharField()

    def clean_field_name(self):
        # Custom validation logic goes here
        pass
"""
from base.forms import ModelForm
from base.models import Department, JobPosition
from employee.models import Employee
from helpdesk.models import Attachment, DepartmentManager, TicketType, FAQ,Ticket, FAQCategory, Comment
from django import forms
from django.template.loader import render_to_string


class TicketTypeForm(ModelForm):

    class Meta:
        model = TicketType
        fields = "__all__"


class FAQForm(ModelForm):
    class Meta:
        model = FAQ
        fields = "__all__"  
        widgets={
            'category':forms.HiddenInput(),            
            'tags': forms.SelectMultiple(attrs={
                'class': 'oh-select oh-select-2 select2-hidden-accessible',
                'onchange': 'updateTag()',
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes the Ticket tag form instance.
        If an instance is provided, sets the initial value for the form's .
        """
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = list(self.fields["tags"].choices)
        self.fields["tags"].choices.append(("create_new_tag", "Create new tag"))
        

class TicketForm(ModelForm):
    deadline = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Ticket
        fields = ["id","title", "employee_id","description", "ticket_type", "priority", "assigning_type" ,"raised_on", "deadline", "status", "tags",]
        widgets = {
        'raised_on': forms.Select(attrs={"class": "oh-select oh-select-2", "required": "true"}),
        }
    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

# def get_updated_choices(assigning_type):
#     new_choices =[
#             ('', '---------'),
#         ]
#     if assigning_type:
#         if assigning_type == 'department':
#             # Retrieve data from the Department model and format it as a list of dictionaries
#             departments = Department.objects.values('id', 'department')
#             raised_on = [{'id': dept['id'], 'name': dept['department']} for dept in departments]
#         elif assigning_type == 'job_position':
#             jobpositions = JobPosition.objects.values('id','job_position')
#             raised_on = [{'id': job['id'], 'name': job['job_position']} for job in jobpositions]
#         elif assigning_type == 'individual':
#             employees = Employee.objects.values('id','employee_first_name','employee_last_name')
#             raised_on = [{'id': employee['id'], 'name': f"{employee['employee_first_name']} {employee['employee_last_name']}"} for employee in employees]

#         new_choices = [
#             (choice['id'], choice['name']) for choice in raised_on
#             ]
#         return new_choices

class TicketTagForm(ModelForm):
    class Meta:
        model = Ticket
        fields = ["tags",]
        widgets = {
            'tags': forms.SelectMultiple(attrs={
                'class': 'oh-select oh-select-2 select2-hidden-accessible',
                'onchange': 'updateTag()',
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes the Ticket tag form instance.
        If an instance is provided, sets the initial value for the form's .
        """
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = list(self.fields["tags"].choices)
        self.fields["tags"].choices.append(("create_new_tag", "Create new tag"))
        

class TicketRaisedOnForm(ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "assigning_type",
            'raised_on'
        ]
        widgets = {
            "raised_on":forms.Select(
                attrs={"class": "oh-select oh-select-2", "required": "true"},
            ),       
        }

class TicketAssigneesForm(ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "assigned_to",
        ]


class FAQCategoryForm(ModelForm):
    class Meta:
        model = FAQCategory
        fields = "__all__"  

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = [
            'comment',
        ]
        widgets = {
            "employee_id":forms.HiddenInput()
            
        }

class AttachmentForm(forms.ModelForm):
    file = forms.FileField(widget = forms.TextInput(attrs={
            "name": "file",
            "type": "File",
            "class": "form-control",
            "multiple": "True",
        }), label = "")
    class Meta:
        model = Attachment
        fields = ['file','comment','ticket']


class DepartmentManagerCreateForm(ModelForm):
    class Meta:
        model = DepartmentManager
        fields = ["department", "manager"]
