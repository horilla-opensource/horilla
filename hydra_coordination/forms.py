from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company, Department
from hydra_coordination.models import (
    Location,
    PersonAssignment,
    ScopeGrant,
    Section,
    Team,
)
from hydra_coordination.selectors import (
    active_grants_for_user,
    departments_for_user,
    locations_for_user,
    sections_for_user,
    teams_for_user,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "oh-switch__checkbox"
            elif isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class


class LocationForm(StyledModelForm):
    class Meta:
        model = Location
        fields = ("company", "name", "code", "address", "is_active")

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        if actor.is_superuser:
            queryset = Company.objects.all()
        else:
            company_ids = active_grants_for_user(user=actor).filter(
                company__isnull=False
            ).values_list("company_id", flat=True)
            queryset = Company.objects.filter(pk__in=company_ids)
        self.fields["company"].queryset = queryset.order_by("company")


class SectionForm(StyledModelForm):
    class Meta:
        model = Section
        fields = ("location", "department", "name", "code", "is_active")

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = locations_for_user(
            user=actor, permission="add_section"
        )
        self.fields["department"].queryset = departments_for_user(user=actor)


class TeamForm(StyledModelForm):
    class Meta:
        model = Team
        fields = ("section", "name", "code", "is_active")

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = sections_for_user(
            user=actor, permission="add_team"
        )


class ScopeGrantForm(StyledModelForm):
    class Meta:
        model = ScopeGrant
        fields = (
            "user",
            "company",
            "department",
            "location",
            "section",
            "team",
            "valid_from",
            "valid_until",
            "is_active",
        )
        widgets = {
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(is_active=True).order_by(
            "username"
        )
        if actor.is_superuser:
            self.fields["company"].queryset = Company.objects.order_by("company")
            self.fields["department"].queryset = Department._base_manager.order_by(
                "department"
            )
            self.fields["location"].queryset = Location.objects.order_by(
                "company__company", "name"
            )
            self.fields["section"].queryset = Section.objects.order_by(
                "location__name", "name"
            )
            self.fields["team"].queryset = Team.objects.order_by(
                "section__name", "name"
            )
        else:
            company_ids = active_grants_for_user(user=actor).filter(
                company__isnull=False
            ).values_list("company_id", flat=True)
            self.fields["company"].queryset = Company.objects.filter(
                pk__in=company_ids
            )
            self.fields["department"].queryset = departments_for_user(user=actor)
            self.fields["location"].queryset = locations_for_user(
                user=actor, permission="add_scopegrant"
            )
            self.fields["section"].queryset = sections_for_user(
                user=actor, permission="add_scopegrant"
            )
            self.fields["team"].queryset = teams_for_user(
                user=actor, permission="add_scopegrant"
            )

    def clean(self):
        cleaned_data = super().clean()
        targets = [
            cleaned_data.get(name)
            for name in ("company", "department", "location", "section", "team")
            if cleaned_data.get(name)
        ]
        if len(targets) != 1:
            raise ValidationError(_("Choose exactly one organization scope target."))
        return cleaned_data


class PersonAssignmentForm(StyledModelForm):
    class Meta:
        model = PersonAssignment
        fields = (
            "team",
            "department",
            "valid_from",
            "valid_until",
            "is_primary",
            "is_active",
        )
        widgets = {
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = teams_for_user(
            user=actor, permission="add_personassignment"
        )
        self.fields["department"].queryset = departments_for_user(user=actor)


class EmployeeTeamAssignmentForm(forms.Form):
    team = forms.ModelChoiceField(queryset=Team.objects.none(), label=_("Team"))
    valid_from = forms.DateField(
        label=_("Effective from"),
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = teams_for_user(
            user=actor, permission="add_personassignment"
        ).filter(
            is_active=True,
            section__is_active=True,
            section__location__is_active=True,
            section__department__isnull=False,
        )
        self.fields["team"].widget.attrs["class"] = "oh-select oh-select-2 w-100"
        self.fields["valid_from"].widget.attrs.update(
            {"class": "oh-input w-100", "max": timezone.localdate().isoformat()}
        )

    def clean_valid_from(self):
        valid_from = self.cleaned_data["valid_from"]
        if valid_from > timezone.localdate():
            raise ValidationError(
                _("Employee team assignment cannot start in the future.")
            )
        return valid_from


class OrganizationAccessEndForm(forms.Form):
    action = forms.ChoiceField(
        label=_("End mode"),
        choices=(
            ("schedule", _("Schedule a last day")),
            ("immediate", _("Revoke immediately")),
        ),
    )
    last_day = forms.DateField(
        label=_("Last day of access"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_("Required for a scheduled end; the date is inclusive."),
    )
    reason = forms.CharField(
        label=_("Reason"),
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["action"].widget.attrs["class"] = "oh-select oh-select-2 w-100"
        self.fields["last_day"].widget.attrs.update(
            {"class": "oh-input w-100", "min": timezone.localdate().isoformat()}
        )
        self.fields["reason"].widget.attrs["class"] = "oh-input w-100"

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        last_day = cleaned_data.get("last_day")
        if action == "schedule" and last_day is None:
            self.add_error("last_day", _("Choose the last day of access."))
        if last_day is not None and last_day < timezone.localdate():
            self.add_error("last_day", _("The last day cannot be in the past."))
        if action == "immediate":
            cleaned_data["last_day"] = None
        cleaned_data["reason"] = " ".join(cleaned_data.get("reason", "").split())
        return cleaned_data
