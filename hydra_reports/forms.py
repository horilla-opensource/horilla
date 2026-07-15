from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.models import Location, Team
from hydra_coordination.selectors import locations_for_user, teams_for_user
from hydra_legalization.models import LegalizationCase
from hydra_people.models import Person


class OperationalReportFilterForm(forms.Form):
    ATTENTION_CHOICES = (
        ("", _("All records")),
        ("any", _("Any attention item")),
        ("arrival", _("Arrival attention")),
        ("legalization", _("Legalization attention")),
        ("unassigned", _("No current team assignment")),
    )

    q = forms.CharField(label=_("Search"), required=False, max_length=120)
    lifecycle = forms.ChoiceField(
        label=_("Lifecycle"),
        required=False,
        choices=(("", _("All lifecycle states")),) + tuple(Person.LifecycleState.choices),
    )
    location = forms.ModelChoiceField(
        label=_("Location"),
        required=False,
        queryset=Location._base_manager.none(),
        empty_label=_("All locations in my scope"),
    )
    team = forms.ModelChoiceField(
        label=_("Team"),
        required=False,
        queryset=Team._base_manager.none(),
        empty_label=_("All teams in my scope"),
    )
    arrival_status = forms.ChoiceField(
        label=_("Arrival status"),
        required=False,
        choices=(("", _("All arrival statuses")),) + tuple(ArrivalPlan.Status.choices),
    )
    legalization_status = forms.ChoiceField(
        label=_("Legalization status"),
        required=False,
        choices=(("", _("All legalization statuses")),)
        + tuple(LegalizationCase.Status.choices),
    )
    attention = forms.ChoiceField(
        label=_("Attention"),
        required=False,
        choices=ATTENTION_CHOICES,
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["location"].queryset = locations_for_user(
            user=actor
        ).filter(is_active=True)
        self.fields["team"].queryset = teams_for_user(user=actor).filter(
            is_active=True
        )
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "oh-select oh-select-2 w-100"
            else:
                field.widget.attrs["class"] = "oh-input w-100"

    def clean(self):
        cleaned = super().clean()
        location = cleaned.get("location")
        team = cleaned.get("team")
        if location and team and team.section.location_id != location.pk:
            raise ValidationError(_("The selected Team is outside the selected Location."))
        return cleaned
