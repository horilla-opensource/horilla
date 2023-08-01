"""
forms.py

This module is used to register the forms for pms models
"""
import uuid
from django.core.exceptions import ValidationError
from django import forms
from django.utils.translation import gettext_lazy as _
from django import forms
from employee.models import Department, JobPosition
from pms.models import (
    Question,
    EmployeeObjective,
    EmployeeKeyResult,
    Feedback,
    Period,
    Comment,
    QuestionOptions,
    Employee,
    QuestionTemplate,
)


def validate_date(start_date, end_date):
    if start_date and end_date and start_date > end_date:
        raise forms.ValidationError("The start date must be before the end date.")


def set_date_field_initial(instance):
    """this is used to update change the date value format"""
    initial = {}
    if instance.start_date is not None:
        initial["start_date"] = instance.start_date.strftime("%Y-%m-%d")
    if instance.end_date is not None:
        initial["end_date"] = instance.end_date.strftime("%Y-%m-%d")
    return initial


class ObjectiveForm(forms.ModelForm):
    """
    A form to create or update instances of the EmployeeObjective model.
    """

    OBJECTIVE_TYPES = (
        ("none", "----------"),
        ("individual", _("Individual")),
        ("job_position", _("Job position")),
        ("department", _("Department")),
    )

    objective_type = forms.ChoiceField(
        choices=OBJECTIVE_TYPES,
        widget=forms.Select(
            attrs={
                "class": " oh-input-objective-type-choices oh-input",
                "style": "width:100%",
            }
        ),
        required=False,
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select--lg oh-select-no-search w-100 oh-input-objective-type-choices",
                "style": "width:100%; display:none;",
            }
        ),
        required=False,
    )
    job_position = forms.ModelChoiceField(
        queryset=JobPosition.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select--lg oh-select-no-search w-100 oh-input-objective-type-choices",
                "style": "width:100%; display:none;",
            }
        ),
        required=False,
    )
    period = forms.ModelChoiceField(
        queryset=Period.objects.all(),
        empty_label="",
        widget=forms.Select(
            attrs={
                "class": " oh-select--period-change",
                "style": "width:100%; display:none;",
            }
        ),
        required=False,
    )
    employee_id = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select-2 ",
                "style": "width:100%; display:none;",
            }
        ),
        required=False,
    )

    class Meta:
        model = EmployeeObjective
        exclude = ["status"]
        widgets = {
            "objective": forms.TextInput(
                attrs={"class": "oh-input oh-input--block", "placeholder": "Objective"}
            ),
            "objective_description": forms.Textarea(
                attrs={
                    "class": "oh-input oh-input--textarea oh-input--block",
                    "placeholder": "Objective description goes here.",
                    "rows": 3,
                    "cols": 40,
                }
            ),
            "start_date": forms.DateInput(
                attrs={"class": "oh-input w-100", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "oh-input w-100", "type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Constructor for ObjectiveForm. If an instance is provided, set initial values for date fields
        """
        if instance := kwargs.get("instance"):
            kwargs["initial"] = set_date_field_initial(instance)

        employee = kwargs.pop(
            "employee", None
        )  # access the logged-in user's information
        super(ObjectiveForm, self).__init__(*args, **kwargs)
        if employee and Employee.objects.filter(
            employee_work_info__reporting_manager_id=employee
        ):
            # manager level access
            department = employee.employee_work_info.department_id
            employees = Employee.objects.filter(
                employee_work_info__department_id=department
            )
            self.fields["employee_id"].queryset = employees
            self.fields["department"].queryset = Department.objects.filter(
                id=department.id
            )
            self.fields["job_position"].queryset = department.job_position.all()

        # Set unique IDs for employee_id fields to prevent conflicts with other forms on the same page
        self.fields["employee_id"].widget.attrs.update({"id": str(uuid.uuid4())})

    def clean(self):
        """
        Validates form fields and raises a validation error if any fields are invalid
        """
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        objective_type = cleaned_data.get("objective_type")
        department = cleaned_data.get("department")
        job_position = cleaned_data.get("job_position")
        employee_id = cleaned_data.get("employee_id")

        # Check that start date is before end date
        validate_date(start_date, end_date)

        # Check that employee ID is provided for individual objective type
        if objective_type == "individual" and not employee_id:
            self.add_error(
                "employee_id",
                "Employee field is required for individual objective type.",
            )

        # Check that job position is provided for job position objective type
        if objective_type == "job_position" and not job_position:
            self.add_error(
                "job_position",
                "Job position field is required for job position objective type.",
            )

        # Check that department is provided for department objective type
        if objective_type == "department" and not department:
            self.add_error(
                "department",
                "Department field is required for department objective type.",
            )

        # Check that an objective type is selected
        if objective_type == "none":
            self.add_error("objective_type", "Please fill the objective type.")

        return cleaned_data


class KeyResultForm(forms.ModelForm):
    """
    A form used for creating and updating EmployeeKeyResult objects.

    Includes fields for title, description, current value, target value,
    start date, end date, progress type, and the associated period and employee.

    Excludes fields for status, progress_boolean, progress_integer,
    employee_objective_id, and start value.

    """

    period = forms.ModelChoiceField(
        queryset=Period.objects.all(),
        empty_label="",
        widget=forms.Select(attrs={"style": "width:100%; display:none;"}),
        required=False,
    )

    class Meta:
        model = EmployeeKeyResult
        fields = "__all__"
        exclude = [
            "status",
            "progress_boolean",
            "progress_integer",
            "employee_objective_id",
            "start_value",
        ]

        widgets = {
            "key_result": forms.TextInput(
                attrs={
                    "placeholder": "Enter a title",
                    "class": "oh-input w-100",
                    "required": True,
                }
            ),
            "key_result_description": forms.Textarea(
                attrs={
                    "placeholder": "Enter a description",
                    "class": "oh-input oh-input--textarea w-100",
                    "required": True,
                    "rows": 3,
                    "cols": 40,
                }
            ),
            "employee_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                    "style": "display:none;",
                }
            ),
            "current_value": forms.NumberInput(
                attrs={"class": "oh-input w-100", "required": True}
            ),
            "target_value": forms.NumberInput(
                attrs={"class": "oh-input w-100", "required": True}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input w-100", "required": True}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input w-100", "required": True}
            ),
            "progress_type": forms.Select(
                attrs={
                    "class": "oh-select oh-select--lg oh-select-no-search w-100",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance:
            kwargs["initial"] = set_date_field_initial(instance)
        employee = kwargs.pop(
            "employee", None
        )  # access the logged-in user's information
        super().__init__(*args, **kwargs)
        employees = Employee.objects.filter(
            employee_work_info__reporting_manager_id=employee
        )
        if employee and employees:
            # manager level access
            self.fields["employee_id"].queryset = employees

        # Set unique IDs for employee_id fields to prevent conflicts with other forms on the same page
        self.fields["employee_id"].widget.attrs.update({"id": str(uuid.uuid4())})

    def clean_value(self, value_type):
        value = self.cleaned_data.get(value_type)
        other_value = self.cleaned_data.get(
            "current_value" if value_type == "target_value" else "target_value"
        )
        if (
            value is not None
            and other_value is not None
            and value_type == "current_value"
            and value > other_value
        ):
            raise forms.ValidationError(
                "Current value cannot be greater than target value"
            )
        elif (
            value is not None
            and other_value is not None
            and value_type == "target_value"
            and value < other_value
        ):
            raise forms.ValidationError(
                "Target value cannot be less than current value"
            )
        return value

    def clean(self):
        cleaned_data = super().clean()
        employee_objective_id = self.initial.get("employee_objective_id")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        validate_date(start_date, end_date)

        if employee_objective_id and start_date and end_date:
            if start_date < employee_objective_id.start_date:
                raise ValidationError("Start date should be after Objective start date")

            if end_date > employee_objective_id.end_date:
                raise ValidationError("End date should be below Objective end date")
        else:
            raise forms.ValidationError("Employee Objective not found")

        return cleaned_data


class FeedbackForm(forms.ModelForm):
    """
    A form used for creating and updating Feedback objects.
    """

    period = forms.ModelChoiceField(
        queryset=Period.objects.all(),
        empty_label="",
        widget=forms.Select(
            attrs={
                "class": " oh-select--period-change ",
                "style": "width:100%; display:none;",
            }
        ),
        required=False,
    )

    # employee_key_results_id = forms.ModelChoiceField(queryset=EmployeeKeyResult.objects.filter(id=-8451257845215),widget=forms.SelectMultiple(attrs={"class":"oh-select oh-select-2 w-100 oh-select-2--large","multiple":"multiple"}),required=False)
    class Meta:
        model = Feedback
        fields = "__all__"
        exclude = ["status", "archive"]

        widgets = {
            "review_cycle": forms.TextInput(
                attrs={"placeholder": "Enter a title", "class": "oh-input w-100"}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "employee_id": forms.Select(
                attrs={
                    "class": " oh-select--employee-change",
                    "style": "width:100%; display:none;",
                },
            ),
            "manager_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 ",
                    "style": "width:100%; display:none;",
                },
            ),
            "colleague_id": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 w-100",
                    "multiple": "multiple",
                    "style": "width:100%; display:none;",
                }
            ),
            "subordinate_id": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 w-100",
                    "multiple": "multiple",
                    "style": "width:100%; display:none;",
                }
            ),
            "question_template_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select--lg oh-select-no-search",
                    "style": "width:100%; display:none;",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes the feedback form instance.
        If an instance is provided, sets the initial value for the form's date fields.
        """

        instance = kwargs.get("instance")
        employee = kwargs.pop(
            "employee", None
        )  # access the logged-in user's information
        if instance:
            kwargs["initial"] = set_date_field_initial(instance)
        super().__init__(*args, **kwargs)
        if instance:
            self.fields["employee_id"].widget.attrs.update(
                {"class": "oh-select oh-select-2"}
            )
        employees = Employee.objects.filter(
            employee_work_info__reporting_manager_id=employee
        )
        if employee and employees:
            department = employee.employee_work_info.department_id
            employees = Employee.objects.filter(
                employee_work_info__department_id=department
            )
            # manager level access
            self.fields["employee_id"].queryset = employees
            self.fields["manager_id"].queryset = employees
            self.fields["colleague_id"].queryset = employees
            self.fields["subordinate_id"].queryset = employees

    def clean(self):
        """
        Cleans and validates the feedback form data.
        Ensures that the start date is before the end date and validates the start date.
        """
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if "employee_key_results_id" in self.errors:
            del self.errors["employee_key_results_id"]

        self.instance
        validate_date(start_date, end_date)
        return cleaned_data


class QuestionTemplateForm(forms.ModelForm):
    """
    Form for creating or updating a question template instance
    """

    question_template = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "oh-input oh-input--small oh-input--res-height w-100",
                "placeholder": "For Developer",
            }
        )
    )

    class Meta:
        model = QuestionTemplate
        fields = "__all__"


class QuestionForm(forms.ModelForm):
    """
    Form for creating or updating a question  instance
    """

    question = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "oh-input oh-input--small oh-input--res-height w-100",
                "placeholder": "Enter question",
            }
        ),
        required=True,
    )
    options = forms.ModelChoiceField(
        queryset=QuestionOptions.objects.all(), required=False
    )
    option_a = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )
    option_b = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )
    option_c = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )
    option_d = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )

    class Meta:
        model = Question

        exclude = ["question_option_id", "template_id"]
        widgets = {
            "question_type": forms.Select(
                attrs={
                    "class": "oh-select oh-select--sm oh-select-no-search oh-select--qa-change w-100",
                    "required": True,
                }
            )
        }
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["question_type"].widget.attrs.update({"id": str(uuid.uuid4())})
        if (
            self.instance.pk
            and self.instance.question_type == "4"
            and self.instance.question_options.first()
        ):
            self.fields[
                "option_a"
            ].initial = self.instance.question_options.first().option_a
            self.fields[
                "option_b"
            ].initial = self.instance.question_options.first().option_b
            self.fields[
                "option_c"
            ].initial = self.instance.question_options.first().option_c
            self.fields[
                "option_d"
            ].initial = self.instance.question_options.first().option_d


class ObjectiveCommentForm(forms.ModelForm):
    """
    A form used to add a comment to an employee's objective.
    Excludes fields for the employee and employee objective and uses a textarea widget for the comment field.
    """

    class Meta:
        model = Comment
        exclude = ["employee_id", "employee_objective_id"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "oh-input oh-input--small oh-input--textarea",
                    "rows": "4",
                    "placeholder": _("Add a comment..."),
                }
            ),
        }


class PeriodForm(forms.ModelForm):
    """
    A form for creating or updating a Period object.
    """

    class Meta:
        model = Period
        fields = "__all__"
        widgets = {
            "period_name": forms.TextInput(
                attrs={"placeholder": "Q1.", "class": "oh-input w-100"}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            """
            django forms not showing value inside the date, time html element.
            so here overriding default forms instance method to set initial value
            """

            kwargs["initial"] = set_date_field_initial(instance)
        super(PeriodForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        validate_date(start_date, end_date)
