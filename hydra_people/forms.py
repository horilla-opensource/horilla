from django import forms
from django.utils.translation import gettext_lazy as _

from hydra_people.models import Person, phone_validator
from hydra_people.selectors import people_for_user
from hydra_people.recruitment_selectors import (
    conversion_candidates_for_user,
    recruitments_for_user,
    unlinked_candidates_for_user,
)
from base.models import JobPosition
from recruitment.models import Candidate, Recruitment


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = (
            "passport_name",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "citizenship",
            "preferred_language",
            "phone",
            "whatsapp_viber",
            "email",
            "lifecycle_state",
            "is_active",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "oh-switch__checkbox"
            elif isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class


class EmployeeConversionForm(forms.Form):
    candidate = forms.ModelChoiceField(
        label=_("Hired recruitment application"),
        queryset=Candidate._base_manager.none(),
    )
    work_email = forms.EmailField(
        label=_("Employee / account email"),
        help_text=_("The account is created inactive with an unusable password."),
    )
    phone = forms.CharField(
        label=_("Employee phone"),
        max_length=25,
        validators=(phone_validator,),
    )
    joining_date = forms.DateField(
        label=_("Joining date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    confirmation = forms.BooleanField(
        label=_(
            "I confirm the application is hired and these values should create/link "
            "the Horilla employee."
        ),
    )

    def __init__(self, *args, actor, person, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.person = person
        candidates = conversion_candidates_for_user(user=actor, person=person)
        self.fields["candidate"].queryset = candidates

        selected_id = self.data.get("candidate") or self.initial.get("candidate")
        selected = candidates.filter(pk=selected_id).first()
        if selected is None and candidates.count() == 1:
            selected = candidates.first()
            self.initial["candidate"] = selected.pk

        existing_employee = selected.converted_employee_id if selected else person.employee
        existing_work_info = (
            getattr(existing_employee, "employee_work_info", None)
            if existing_employee
            else None
        )
        if existing_employee:
            self.initial.setdefault("work_email", existing_employee.email)
            self.initial.setdefault("phone", existing_employee.phone)
        elif selected:
            self.initial.setdefault("work_email", person.email or selected.email)
            self.initial.setdefault("phone", person.phone or selected.mobile)
        else:
            self.initial.setdefault("work_email", person.email)
            self.initial.setdefault("phone", person.phone)
        if existing_work_info and existing_work_info.date_joining:
            self.initial.setdefault("joining_date", existing_work_info.date_joining)
        elif selected and selected.joining_date:
            self.initial.setdefault("joining_date", selected.joining_date)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "oh-switch__checkbox"
            elif isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean_work_email(self):
        return self.cleaned_data["work_email"].strip().lower()

    def clean_phone(self):
        return " ".join(self.cleaned_data["phone"].split())


class CandidateLinkForm(forms.Form):
    candidate = forms.ModelChoiceField(
        label=_("Recruitment application"),
        queryset=Candidate.objects.none(),
        widget=forms.Select(attrs={"class": "oh-select oh-select-2 w-100"}),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["candidate"].queryset = unlinked_candidates_for_user(user=actor)


class HydraCandidateApplicationForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = (
            "recruitment_id",
            "job_position_id",
            "email",
            "mobile",
            "portfolio",
            "source",
            "address",
            "country",
            "state",
            "city",
            "zip",
            "resume",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, actor, person, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.person = person
        allowed_recruitments = recruitments_for_user(
            user=actor, permission="view_recruitment"
        ).filter(closed=False, is_active=True)
        self.fields["recruitment_id"].queryset = allowed_recruitments
        self.fields["job_position_id"].queryset = (
            JobPosition._base_manager.filter(open_positions__in=allowed_recruitments)
            .distinct()
            .order_by("job_position", "pk")
        )
        recruitment_id = self.data.get("recruitment_id") or getattr(
            self.instance, "recruitment_id_id", None
        )
        try:
            recruitment = self.fields["recruitment_id"].queryset.get(
                pk=recruitment_id
            )
        except (Recruitment.DoesNotExist, TypeError, ValueError):
            recruitment = None
        if recruitment:
            self.fields["job_position_id"].queryset = recruitment.open_positions.all()

        self.fields["email"].initial = person.email
        self.fields["source"].initial = "software"
        self.fields["resume"].required = False
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean(self):
        cleaned_data = super().clean()
        recruitment = cleaned_data.get("recruitment_id")
        job_position = cleaned_data.get("job_position_id")
        resume = cleaned_data.get("resume")
        if recruitment and job_position and not recruitment.open_positions.filter(
            pk=job_position.pk
        ).exists():
            self.add_error(
                "job_position_id", _("Choose a position from this recruitment.")
            )
        if recruitment and not resume and not recruitment.optional_resume:
            self.add_error("resume", _("This field is required."))
        return cleaned_data


class CandidatePersonLinkForm(forms.Form):
    person = forms.ModelChoiceField(
        label=_("Hydra person"),
        queryset=Person.objects.none(),
        widget=forms.Select(attrs={"class": "oh-select oh-select-2 w-100"}),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = people_for_user(
            user=actor, permission="change_person"
        )
