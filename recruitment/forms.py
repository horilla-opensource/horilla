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

import uuid
from ast import Dict
from datetime import date, datetime
from typing import Any

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base import thread_local_middleware
from base.forms import Form
from base.methods import reload_queryset
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla.decorators import logger
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from recruitment import widgets
from recruitment.models import (
    Candidate,
    InterviewSchedule,
    JobPosition,
    Recruitment,
    RecruitmentMailTemplate,
    RecruitmentSurvey,
    RejectedCandidate,
    RejectReason,
    SkillZone,
    SkillZoneCandidate,
    Stage,
    StageFiles,
    StageNote,
    SurveyTemplate,
)


class ModelForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(thread_local_middleware._thread_locals, "request", None)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.DateInput)):
                field.initial = date.today()

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

            try:
                self.fields["employee_id"].initial = request.user.employee_get
            except:
                pass

            try:
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


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

    # survey_templates = forms.ModelMultipleChoiceField(
    #     queryset=SurveyTemplate.objects.all(),
    #     widget=forms.SelectMultiple(),
    #     label=_("Survey Templates"),
    #     required=False,
    # )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Recruitment
        fields = "__all__"
        exclude = ["is_active"]
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
                queryset=Employee.objects.filter(is_active=True),
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
        exclude = ["sequence", "is_active"]
        labels = {
            "stage": _("Stage"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        if not self.instance.pk:
            self.fields["stage_managers"] = HorillaMultiSelectField(
                queryset=Employee.objects.filter(is_active=True),
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
        exclude = [
            "confirmation",
            "scheduled_for",
            "schedule_date",
            "joining_date",
            "sequence",
            "stage_id",
            "offerletter_status",
        ]
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
        job_id = self.data.get("job_position_id")
        if job_id:
            job_position = JobPosition.objects.get(id=job_id)
            self.instance.job_position_id = job_position
        return super().save(commit)

    def clean(self):
        if self.instance.name is not None:
            self.errors.pop("job_position_id", None)
            if (
                self.instance.job_position_id is None
                or self.data.get("job_position_id") == ""
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
    active_recruitment = Recruitment.objects.filter(
        is_active=True, closed=False, is_published=True
    )
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


class AddCandidateForm(ModelForm):
    """
    Form for Candidate model
    """

    verbose_name = "Add Candidate"

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Candidate
        fields = [
            "profile",
            "resume",
            "name",
            "email",
            "mobile",
            "gender",
            "stage_id",
            "job_position_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = kwargs["initial"].get("stage_id")
        if initial:
            recruitment = Stage.objects.get(id=initial).recruitment_id
            self.instance.recruitment_id = recruitment
            self.fields["stage_id"].queryset = self.fields["stage_id"].queryset.filter(
                recruitment_id=recruitment
            )
            self.fields["job_position_id"].queryset = recruitment.open_positions
        self.fields["gender"].empty_label = None
        self.fields["job_position_id"].empty_label = None
        self.fields["stage_id"].empty_label = None

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


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
        exclude = ["sequence", "is_active"]
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


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [
                single_file_clean(data, initial),
            ]
        return result[0] if result else []


class StageNoteForm(ModelForm):
    """
    Form for StageNote model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = StageNote
        # exclude = (
        #     "updated_by",
        #     "stage_id",
        # )
        fields = ["description"]
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # field = self.fields["candidate_id"]
        # field.widget = field.hidden_widget()
        self.fields["stage_files"] = MultipleFileField(label="files")
        self.fields["stage_files"].required = False

    def save(self, commit: bool = ...) -> Any:
        attachment = []
        multiple_attachment_ids = []
        attachments = None
        if self.files.getlist("stage_files"):
            attachments = self.files.getlist("stage_files")
            self.instance.attachement = attachments[0]
            multiple_attachment_ids = []

            for attachment in attachments:
                file_instance = StageFiles()
                file_instance.files = attachment
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.stage_files.add(*multiple_attachment_ids)
        return instance, multiple_attachment_ids


class StageNoteUpdateForm(ModelForm):
    class Meta:
        """
        Meta class to add the additional info
        """

        model = StageNote
        exclude = ["updated_by", "stage_id", "stage_files", "is_active"]
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["candidate_id"]
        field.widget = field.hidden_widget()


class QuestionForm(ModelForm):
    """
    QuestionForm
    """

    verbose_name = "Survey Questions"

    recruitment = forms.ModelMultipleChoiceField(
        queryset=Recruitment.objects.filter(is_active=True),
        required=False,
        label=_("Recruitment"),
    )
    # job_positions = forms.ModelMultipleChoiceField(
    #     queryset=JobPosition.objects.all(), required=False, label=_("Job Positions")
    # )

    class Meta:
        """
        Class Meta for additional options
        """

        model = RecruitmentSurvey
        fields = "__all__"
        exclude = [
            "recruitment_ids",
            "job_position_ids",
            "is_active",
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
        # jobs = self.cleaned_data["job_positions"]
        qtype = self.cleaned_data["type"]
        options = self.cleaned_data["options"]
        if not recruitment.exists():  # or jobs.exists()):
            raise ValidationError(
                "Choose any recruitment or job positions to apply this question"
            )
        self.recruitment = recruitment
        # self.job_positions = jobs

        if qtype in ["options", "multiple"] and (options is None or options == ""):
            raise ValidationError({"options": "Options field is required"})

        return

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance", None)
        if instance:
            self.fields["recruitment"].initial = instance.recruitment_ids.all()
            # self.fields["job_positions"].initial = instance.job_position_ids.all()
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


class TemplateForm(ModelForm):
    """
    TemplateForm
    """

    verbose_name = "Template"

    class Meta:
        model = SurveyTemplate
        fields = "__all__"
        exclude = ["is_active"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class AddQuestionForm(Form):
    """
    AddQuestionForm
    """

    verbose_name = "Add Question"
    question_ids = forms.ModelMultipleChoiceField(
        queryset=RecruitmentSurvey.objects.all(), label="Questions"
    )
    template_ids = forms.ModelMultipleChoiceField(
        queryset=SurveyTemplate.objects.all(), label="Templates"
    )

    def save(self):
        """
        Manual save/adding of questions to the templates
        """
        for question in self.cleaned_data["question_ids"]:
            question.template_id.add(*self.data["template_ids"])

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


exclude_fields = ["id", "profile", "portfolio", "resume", "sequence"]


class CandidateExportForm(forms.Form):
    model_fields = Candidate._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name.capitalize())
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in exclude_fields
    ]
    field_choices = field_choices + [
        ("rejected_candidate__description", "Rejected Description"),
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
        # exclude = ["is_active"]
        widgets = {
            "body": forms.Textarea(
                attrs={"data-summernote": "", "style": "display:none;"}
            ),
        }

    def get_template_language(self):
        mail_data = {
            "Receiver|Full name": "instance.get_full_name",
            "Sender|Full name": "self.get_full_name",
            "Receiver|Recruitment": "instance.recruitment_id",
            "Sender|Recruitment": "self.recruitment_id",
            "Receiver|Company": "instance.get_company",
            "Sender|Company": "self.get_company",
            "Receiver|Job position": "instance.get_job_position",
            "Sender|Job position": "self.get_job_position",
            "Receiver|Email": "instance.get_mail",
            "Sender|Email": "self.get_mail",
            "Receiver|Employee Type": "instance.get_employee_type",
            "Sender|Employee Type": "self.get_employee_type",
            "Receiver|Work Type": "instance.get_work_type",
            "Sender|Work Type": "self.get_work_type",
            "Candidate|Full name": "instance.get_full_name",
            "Candidate|Recruitment": "instance.recruitment_id",
            "Candidate|Company": "instance.get_company",
            "Candidate|Job position": "instance.get_job_position",
            "Candidate|Email": "instance.get_email",
            "Candidate|Interview Table": "instance.get_interview|safe",
        }
        return mail_data


class SkillZoneCreateForm(ModelForm):
    verbose_name = "Skill Zone"

    class Meta:
        """
        Class Meta for additional options
        """

        model = SkillZone
        fields = "__all__"
        exclude = ["is_active"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class SkillZoneCandidateForm(ModelForm):
    verbose_name = "Skill Zone Candidate"
    candidate_id = forms.ModelMultipleChoiceField(
        queryset=Candidate.objects.all(),
        widget=forms.SelectMultiple,
        label=_("Candidate"),
    )

    class Meta:
        """
        Class Meta for additional options
        """

        model = SkillZoneCandidate
        fields = "__all__"
        exclude = [
            "added_on",
            "is_active",
        ]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean_candidate_id(self):
        selected_candidates = self.cleaned_data["candidate_id"]

        # Ensure all selected candidates are instances of the Candidate model
        for candidate in selected_candidates:
            if not isinstance(candidate, Candidate):
                raise forms.ValidationError("Invalid candidate selected.")

        return selected_candidates.first()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["candidate_id"].empty_label = None
        if self.instance.pk:
            self.verbose_name = (
                self.instance.candidate_id.name
                + " / "
                + self.instance.skill_zone_id.title
            )

    def save(self, commit: bool = ...) -> Any:
        super().save(commit)
        other_candidates = list(
            set(self.data.getlist("candidate_id"))
            - {
                str(self.instance.candidate_id.id),
            }
        )
        if commit:
            cand = self.instance
            for id in other_candidates:
                cand.pk = None
                cand.id = None
                cand.candidate_id = Candidate.objects.get(id=id)
                try:
                    super(SkillZoneCandidate, cand).save()
                except Exception as e:
                    logger.error(e)

        return other_candidates


class ToSkillZoneForm(ModelForm):
    verbose_name = "Add To Skill Zone"
    skill_zone_ids = forms.ModelMultipleChoiceField(
        queryset=SkillZone.objects.all(), label=_("Skill Zones")
    )

    class Meta:
        """
        Class Meta for additional options
        """

        model = SkillZoneCandidate
        fields = "__all__"
        exclude = [
            "skill_zone_id",
            "is_active",
            "candidate_id",
        ]
        error_messages = {
            NON_FIELD_ERRORS: {
                "unique_together": "This candidate alreay exist in this skill zone",
            }
        }

    def clean(self):
        cleaned_data = super().clean()
        candidate = cleaned_data.get("candidate_id")
        skill_zones = cleaned_data.get("skill_zone_ids")
        skill_zone_list = []
        for skill_zone in skill_zones:
            # Check for the unique together constraint manually
            if SkillZoneCandidate.objects.filter(
                candidate_id=candidate, skill_zone_id=skill_zone
            ).exists():
                # Raise a ValidationError with a custom error message
                skill_zone_list.append(skill_zone)
        if len(skill_zone_list) > 0:
            skill_zones_str = ", ".join(
                str(skill_zone) for skill_zone in skill_zone_list
            )
            raise ValidationError(f"{candidate} already exists in {skill_zones_str}.")

            # cleaned_data['skill_zone_id'] =skill_zone
        return cleaned_data

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class RejectReasonForm(ModelForm):
    """
    RejectReasonForm
    """

    verbose_name = "Reject Reason"

    class Meta:
        model = RejectReason
        fields = "__all__"
        exclude = ["is_active"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class RejectedCandidateForm(ModelForm):
    """
    RejectedCandidateForm
    """

    verbose_name = "Rejected Candidate"

    class Meta:
        model = RejectedCandidate
        fields = "__all__"
        exclude = ["is_active"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reject_reason_id"].empty_label = None
        self.fields["candidate_id"].widget = self.fields["candidate_id"].hidden_widget()


class ScheduleInterviewForm(ModelForm):
    """
    ScheduleInterviewForm
    """

    verbose_name = "Schedule Interview"

    class Meta:
        model = InterviewSchedule
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["interview_date"].widget = forms.DateInput(
            attrs={"type": "date", "class": "oh-input w-100"}
        )
        self.fields["interview_time"].widget = forms.TimeInput(
            attrs={"type": "time", "class": "oh-input w-100"}
        )

    def clean(self):
        instance = self.instance
        cleaned_data = super().clean()
        interview_date = cleaned_data.get("interview_date")
        interview_time = cleaned_data.get("interview_time")

        if not instance.pk and interview_date and interview_date < date.today():
            self.add_error("interview_date", _("Interview date cannot be in the past."))

        if not instance.pk and interview_time:
            now = datetime.now().time()
            if (
                not instance.pk
                and interview_date == date.today()
                and interview_time < now
            ):
                self.add_error(
                    "interview_time", _("Interview time cannot be in the past.")
                )

        return cleaned_data

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html
