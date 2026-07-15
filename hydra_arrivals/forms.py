from django import forms
from django.utils.translation import gettext_lazy as _

from hydra_arrivals.models import ArrivalPlan
from hydra_arrivals.selectors import (
    arrival_locations_for_user,
    coordinators_for_locations,
)
from hydra_people.recruitment_selectors import linked_candidates_for_user
from recruitment.models import Candidate


class ArrivalPlanForm(forms.ModelForm):
    class Meta:
        model = ArrivalPlan
        fields = (
            "candidate",
            "destination_location",
            "coordinator",
            "planned_at",
            "transport_type",
            "transport_reference",
            "pickup_point",
            "notes",
        )
        widgets = {
            "planned_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, actor, person, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.person = person
        self.fields["planned_at"].input_formats = ("%Y-%m-%dT%H:%M",)
        locations = arrival_locations_for_user(user=actor).order_by(
            "company__company", "name"
        )
        self.fields["destination_location"].queryset = locations

        if self.instance.pk:
            self.fields["candidate"].queryset = Candidate._base_manager.filter(
                pk=self.instance.candidate_id
            )
            self.fields["candidate"].disabled = True
        else:
            self.fields["candidate"].queryset = linked_candidates_for_user(
                user=actor
            ).filter(hydra_person_link__person=person)

        location_id = self.data.get("destination_location") or getattr(
            self.instance, "destination_location_id", None
        )
        selected_locations = locations.filter(pk=location_id)
        coordinator_locations = selected_locations if selected_locations.exists() else locations
        self.fields["coordinator"].queryset = coordinators_for_locations(
            locations=coordinator_locations
        )
        if not actor.has_perm("hydra_arrivals.assign_arrivalplan"):
            self.fields["coordinator"].queryset = self.fields[
                "coordinator"
            ].queryset.filter(pk=actor.pk)
            self.fields["coordinator"].initial = actor
            self.fields["coordinator"].disabled = True

        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean(self):
        cleaned_data = super().clean()
        candidate = cleaned_data.get("candidate")
        destination = cleaned_data.get("destination_location")
        if candidate and candidate.hydra_person_link.person_id != self.person.pk:
            self.add_error("candidate", _("Choose an application for this Person."))
        if candidate and destination:
            recruitment = candidate.recruitment_id
            if recruitment is None or recruitment.company_id_id != destination.company_id:
                self.add_error(
                    "destination_location",
                    _("The destination must belong to the recruitment company."),
                )
        return cleaned_data


class ArrivalTransitionForm(forms.Form):
    target_status = forms.ChoiceField(
        label=_("Outcome"),
        choices=(
            (ArrivalPlan.Status.CONFIRMED, _("Confirm arrival")),
            (ArrivalPlan.Status.NO_SHOW, _("Mark no-show")),
        ),
    )
    actual_arrived_at = forms.DateTimeField(
        label=_("Actual arrival time"),
        required=False,
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "oh-input w-100"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    reason = forms.CharField(
        label=_("Reason"),
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2, "class": "oh-input w-100"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_status"].widget.attrs["class"] = "oh-select w-100"

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("target_status") == ArrivalPlan.Status.NO_SHOW
            and not cleaned_data.get("reason", "").strip()
        ):
            self.add_error("reason", _("No-show requires a reason."))
        return cleaned_data


class ArrivalFilterForm(forms.Form):
    q = forms.CharField(label=_("Search"), required=False)
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=(("", _("All statuses")),) + tuple(ArrivalPlan.Status.choices),
    )
    day = forms.DateField(
        label=_("Planned day"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class
