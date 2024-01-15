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

from ast import Dict
from typing import Any
import uuid
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from recruitment.models import (
    SkillZone,
    SkillZoneCandidate,
    Stage,
    Recruitment,
    Candidate,
    StageNote,
    JobPosition,
    RecruitmentSurvey,
    RecruitmentMailTemplate,
)
from recruitment import widgets
from base.methods import reload_queryset
from django.core.exceptions import NON_FIELD_ERRORS




class ModelForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget,
                (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput),
            ):
                label = _(field.label)
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, forms.URLInput):
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": field.label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.empty_label = _("---Choose {label}---").format(
                    label=_(field.label)
                )
                self.fields[field_name].widget.attrs.update(
                    {
                        "id": uuid.uuid4,
                        "class": "oh-select oh-select-2 w-100",
                        "style": "height:50px;",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                label = _(field.label)
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox "})


class RegistrationForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = _(field.label)
                field.empty_label = _("---Choose {label}---").format(label=label)
                self.fields[field_name].widget.attrs.update(
                    {"id": uuid.uuid4, "class": "oh-select-2 oh-select--sm w-100"}
                )
            elif isinstance(widget, (forms.TextInput)):
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox "})


class DropDownForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget,
                (
                    forms.NumberInput,
                    forms.EmailInput,
                    forms.TextInput,
                    forms.FileInput,
                    forms.URLInput,
                ),
            ):
                if field.label is not None:
                    label = _(field.label)
                    field.widget.attrs.update(
                        {
                            "class": "oh-input oh-input--small oh-table__add-new-row d-block w-100",
                            "placeholder": label,
                        }
                    )
            elif isinstance(widget, (forms.Select,)):
                self.fields[field_name].widget.attrs.update(
                    {
                        "class": "oh-select-2 oh-select--xs-forced ",
                        "id": uuid.uuid4(),
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                if field.label is not None:
                    label = _(field.label)
                    field.widget.attrs.update(
                        {
                            "class": "oh-input oh-input--small oh-input--textarea",
                            "placeholder": label,
                            "rows": 1,
                            "cols": 40,
                        }
                    )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox "})


class RecruitmentCreationForm(ModelForm):
    """
    Form for Recruitment model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Recruitment
        fields = "__all__"
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"data-summernote": ""}),
        }
        labels = {"description": _("Description"), "vacancy": _("Vacancy")}

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        if not self.instance.pk:
            self.fields["recruitment_managers"] = HorillaMultiSelectField(
                queryset=Employee.objects.filter(is_active = True),
                widget=HorillaMultiSelectWidget(
                    filter_route_name="employee-widget-filter",
                    filter_class=EmployeeFilter,
                    filter_instance_contex_name="f",
                    filter_template_path="employee_filters.html",
                    required=True,
                ),
                label="Employee",
            )

    def clean(self):
        if isinstance(self.fields["recruitment_managers"], HorillaMultiSelectField):
            ids = self.data.getlist("recruitment_managers")
            if ids:
                self.errors.pop("recruitment_managers", None)
        super().clean()


class StageCreationForm(ModelForm):
    """
    Form for Stage model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Stage
        fields = "__all__"
        exclude = ("sequence",)
        labels = {
            "stage": _("Stage"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        if not self.instance.pk:
            self.fields["stage_managers"] = HorillaMultiSelectField(
                queryset=Employee.objects.filter(is_active = True),
                widget=HorillaMultiSelectWidget(
                    filter_route_name="employee-widget-filter",
                    filter_class=EmployeeFilter,
                    filter_instance_contex_name="f",
                    filter_template_path="employee_filters.html",
                    required=True,
                ),
                label="Employee",
            )

    def clean(self):
        if isinstance(self.fields["stage_managers"], HorillaMultiSelectField):
            ids = self.data.getlist("stage_managers")
            if ids:
                self.errors.pop("stage_managers", None)
        super().clean()


class CandidateCreationForm(ModelForm):
    """
    Form for Candidate model
    """

    load = forms.CharField(widget=widgets.RecruitmentAjaxWidget, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.recruitment_id is not None:
            if self.instance is not None:
                self.fields["job_position_id"] = forms.ModelChoiceField(
                    queryset=self.instance.recruitment_id.open_positions.all(),
                    # additional field options
                )
        self.fields["recruitment_id"].widget.attrs = {"data-widget": "ajax-widget"}
        self.fields["job_position_id"].widget.attrs = {"data-widget": "ajax-widget"}

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Candidate
        fields = "__all__"
        exclude = (
            "confirmation",
            "scheduled_for",
            "schedule_date",
            "joining_date",
            "sequence",
            "stage_id",
            "offerletter_status",
        )
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "dob": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "name": _("Name"),
            "email": _("Email"),
            "mobile": _("Mobile"),
            "address": _("Address"),
            "zip": _("Zip"),
        }

    def save(self, commit: bool = ...):
        candidate = self.instance
        recruitment = candidate.recruitment_id
        stage = candidate.stage_id
        candidate.hired = False
        candidate.start_onboard = False
        if stage is not None:
            if stage.stage_type == "hired" and candidate.canceled is False:
                candidate.hired = True
                candidate.start_onboard = True
        candidate.recruitment_id = recruitment
        candidate.stage_id = stage
        job_id = self.data["job_position_id"]
        job_position = JobPosition.objects.get(id=job_id)
        self.instance.job_position_id = job_position
        return super().save(commit)

    def clean(self):
        if self.instance.name is not None:
            self.errors.pop("job_position_id", None)
            if (
                self.instance.job_position_id is None
                or self.data["job_position_id"] == ""
            ):
                raise forms.ValidationError(
                    {"job_position_id": "This field is required"}
                )
            if (
                self.instance.job_position_id
                not in self.instance.recruitment_id.open_positions.all()
            ):
                raise forms.ValidationError({"job_position_id": "Choose valid choice"})
        return super().clean()


class ApplicationForm(RegistrationForm):
    """
    Form for create Candidate
    """

    load = forms.CharField(widget=widgets.RecruitmentAjaxWidget, required=False)
    active_recruitment = Recruitment.objects.filter(is_active=True, closed=False)
    recruitment_id = forms.ModelChoiceField(queryset=active_recruitment)

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Candidate
        exclude = (
            "stage_id",
            "schedule_date",
            "referral",
            "start_onboard",
            "hired",
            "is_active",
            "canceled",
            "joining_date",
            "sequence",
            "offerletter_status",
            "source",
        )
        widgets = {
            "recruitment_id": forms.TextInput(
                attrs={
                    "required": "required",
                }
            ),
            "dob": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recruitment_id"].widget.attrs = {"data-widget": "ajax-widget"}
        self.fields["job_position_id"].widget.attrs = {"data-widget": "ajax-widget"}


class RecruitmentDropDownForm(DropDownForm):
    """
    Form for Recruitment model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = "__all__"
        model = Recruitment
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"data-summernote": ""}),
        }
        labels = {"description": _("Description"), "vacancy": _("Vacancy")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["job_position_id"].widget.attrs.update({"id": uuid.uuid4})
        self.fields["recruitment_managers"].widget.attrs.update({"id": uuid.uuid4})
        field = self.fields["is_active"]
        field.widget = field.hidden_widget()


class CandidateDropDownForm(DropDownForm):
    """
    Form for Candidate model
    """

    profile = forms.FileField(required=False)

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Candidate
        fields = [
            "name",
            "email",
            "mobile",
            "resume",
            "stage_id",
            "recruitment_id",
            "job_position_id",
            "profile",
        ]
        labels = {
            "name": _("Name"),
            "email": _("Email"),
            "mobile": _("Mobile"),
            "job_position_id": _("Job Position"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recruitment_id"].widget.attrs.update({"id": uuid.uuid4})
        self.fields["stage_id"].widget.attrs.update({"id": uuid.uuid4})


class StageDropDownForm(DropDownForm):
    """
    Form for Stage model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Stage
        fields = "__all__"
        exclude = [
            "sequence",
        ]
        labels = {
            "stage": _("Stage"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stage = Stage.objects.last()
        if stage is not None and stage.sequence is not None:
            self.instance.sequence = stage.sequence + 1
        else:
            self.instance.sequence = 1


class StageNoteForm(ModelForm):
    """
    Form for StageNote model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = StageNote
        exclude = (
            "updated_by",
            "stage_id",
        )
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["candidate_id"]
        field.widget = field.hidden_widget()


class QuestionForm(ModelForm):
    """
    QuestionForm
    """

    recruitment = forms.ModelMultipleChoiceField(
        queryset=Recruitment.objects.filter(is_active=True),
        required=False,
        label=_("Recruitment"),
    )
    job_positions = forms.ModelMultipleChoiceField(
        queryset=JobPosition.objects.all(), required=False, label=_("Job Positions")
    )

    class Meta:
        """
        Class Meta for additional options
        """

        model = RecruitmentSurvey
        fields = "__all__"
        exclude = [
            "recruitment_ids",
            "job_position_ids",
        ]
        labels = {
            "question": _("Question"),
            "sequence": _("Sequence"),
            "type": _("Type"),
            "options": _("Options"),
            "is_mandatory": _("Is Mandatory"),
        }

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string(
            "survey/question_template_organized_form.html", context
        )
        return table_html

    def clean(self):
        super().clean()
        recruitment = self.cleaned_data["recruitment"]
        jobs = self.cleaned_data["job_positions"]
        qtype = self.cleaned_data["type"]
        options = self.cleaned_data["options"]
        if not (recruitment.exists() or jobs.exists()):
            raise ValidationError(
                "Choose any recruitment or job positions to apply this question"
            )
        self.recruitment = recruitment
        self.job_positions = jobs

        if qtype in ["options", "multiple"] and (options is None or options == ""):
            raise ValidationError({"options": "Options field is required"})

        return

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)
        if instance:
            self.fields["recruitment"].initial = instance.recruitment_ids.all()
            self.fields["job_positions"].initial = instance.job_position_ids.all()
        self.fields["type"].widget.attrs.update(
            {"class": " w-100", "style": "border:solid 1px #6c757d52;height:50px;"}
        )
        self.fields["options"].required = False


class SurveyForm(forms.Form):
    """
    SurveyTemplateForm
    """

    def __init__(self, recruitment, *args, **kwargs) -> None:
        super().__init__(recruitment, *args, **kwargs)
        questions = recruitment.recruitmentsurvey_set.all()
        context = {"form": self, "questions": questions}
        form = render_to_string("survey_form.html", context)
        self.form = form
        return
        # for question in questions:
        # self


exclude_fields = ["id", "profile", "portfolio", "resume", "sequence"]


class CandidateExportForm(forms.Form):
    model_fields = Candidate._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in exclude_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "name",
            "recruitment_id",
            "job_position_id",
            "stage_id",
            "schedule_date",
            "email",
            "mobile",
            "hired",
            "joining_date",
        ],
    )


class OfferLetterForm(ModelForm):
    """
    OfferLetterForm
    """

    class Meta:
        model = RecruitmentMailTemplate
        fields = "__all__"
        widgets = {
            "body": forms.Textarea(
                attrs={"data-summernote": "", "style": "display:none;"}
            ),
        }
           
        
class SkillZoneCreateForm(forms.ModelForm):
    class Meta:
        """
        Class Meta for additional options
        """
        model = SkillZone
        fields = "__all__"        
        exclude = [
            "created_on",
            "objects",
            "company_id",
        ]

    
class SkillZoneCandidateForm(ModelForm):
    class Meta:
        """
        Class Meta for additional options
        """
        model = SkillZoneCandidate
        fields = "__all__"
        exclude = [
            "added_on",
        ]
        widgets = {
            "skill_zone_id": forms.HiddenInput(),
        }
        

class ToSkillZoneForm(ModelForm):

    skill_zone_ids = forms.ModelMultipleChoiceField(
        queryset=SkillZone.objects.all(), 
        label=_("Skill Zones")
    )
    class Meta:
        """
        Class Meta for additional options
        """
        model = SkillZoneCandidate
        fields = "__all__"
        exclude = [
            "skill_zone_id",
        ]
        widgets = {
            "candidate_id": forms.HiddenInput(),
            # 'skill_zone_id':forms.MultiValueField()
        }
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "This candidate alreay exist in this skill zone",
            }
        }

    def clean(self):
        cleaned_data = super().clean()
        candidate = cleaned_data.get('candidate_id')
        skill_zones = cleaned_data.get('skill_zone_ids')
        skill_zone_list=[]
        for skill_zone in skill_zones:
            print(skill_zone,candidate)
            # Check for the unique together constraint manually
            if SkillZoneCandidate.objects.filter(candidate_id=candidate, skill_zone_id=skill_zone).exists():
                # Raise a ValidationError with a custom error message
                skill_zone_list.append(skill_zone)
        if len(skill_zone_list) > 0 :
            skill_zones_str = ', '.join(str(skill_zone) for skill_zone in skill_zone_list)       
            raise ValidationError(f"{candidate} already exists in {skill_zones_str}.")

            # cleaned_data['skill_zone_id'] =skill_zone
        return cleaned_data
    
