from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_coordination.models import Location
from hydra_housing.models import (
    HousingAssignment,
    HousingBed,
    HousingBuilding,
    HousingFacility,
    HousingFloor,
    HousingRoom,
)
from hydra_housing.selectors import (
    eligible_people_for_housing_period,
    housing_beds_for_user,
    housing_floors_for_user,
    housing_locations_for_user,
)


def _style_fields(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.Select):
            field.widget.attrs["class"] = "oh-select oh-select-2 w-100"
        else:
            field.widget.attrs["class"] = "oh-input w-100"


class HousingFacilityForm(forms.ModelForm):
    class Meta:
        model = HousingFacility
        fields = ("location", "name", "address", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = housing_locations_for_user(user=actor)
        _style_fields(self)


class HousingBuildingForm(forms.ModelForm):
    class Meta:
        model = HousingBuilding
        fields = ("name", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class HousingFloorForm(forms.ModelForm):
    class Meta:
        model = HousingFloor
        fields = ("name", "sort_order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class HousingRoomForm(forms.ModelForm):
    class Meta:
        model = HousingRoom
        fields = ("name", "floor_unit")

    def __init__(self, *args, actor, facility, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["floor_unit"].queryset = housing_floors_for_user(user=actor).filter(
            building__facility=facility,
            building__is_active=True,
            is_active=True,
        )
        self.fields["floor_unit"].required = False
        _style_fields(self)


class HousingBedForm(forms.ModelForm):
    class Meta:
        model = HousingBed
        fields = ("label",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class HousingAssignmentForm(forms.ModelForm):
    class Meta:
        model = HousingAssignment
        fields = (
            "bed",
            "valid_from",
            "valid_until",
            "reservation_expires_at",
            "notes",
        )
        widgets = {
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "reservation_expires_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, actor, person, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.person = person
        self.fields["reservation_expires_at"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["bed"].queryset = housing_beds_for_user(user=actor).filter(
            is_active=True,
            room__is_active=True,
            room__facility__is_active=True,
        )
        _style_fields(self)

    def clean(self):
        cleaned = super().clean()
        bed = cleaned.get("bed")
        valid_from = cleaned.get("valid_from")
        if bed and valid_from and not eligible_people_for_housing_period(
            user=self.actor,
            location=bed.room.facility.location,
            valid_from=valid_from,
            allow_planned_arrival=valid_from > timezone.localdate(),
        ).filter(pk=self.person.pk).exists():
            self.add_error(
                "bed",
                _(
                    "Choose housing at the Person's effective Team, confirmed-arrival, "
                    "or eligible planned-arrival Location."
                ),
            )
        return cleaned


class HousingEndForm(forms.Form):
    valid_until = forms.DateField(
        label=_("End date"),
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input w-100"}),
    )
    reason = forms.CharField(
        label=_("Reason"),
        max_length=255,
        widget=forms.TextInput(attrs={"class": "oh-input w-100"}),
    )


class HousingReservationCancelForm(forms.Form):
    reason = forms.CharField(
        label=_("Reason"),
        max_length=255,
        widget=forms.TextInput(attrs={"class": "oh-input w-100"}),
    )


class HousingReservationRenewForm(forms.Form):
    reservation_expires_at = forms.DateTimeField(
        label=_("New expiry"),
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "oh-input w-100"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    reason = forms.CharField(
        label=_("Reason"),
        max_length=255,
        widget=forms.TextInput(attrs={"class": "oh-input w-100"}),
    )


class HousingReservationConfirmForm(forms.Form):
    reason = forms.CharField(
        label=_("Reason"),
        max_length=255,
        widget=forms.TextInput(attrs={"class": "oh-input w-100"}),
    )


class HousingMoveForm(forms.Form):
    destination_bed = forms.ModelChoiceField(
        label=_("Destination bed"),
        queryset=HousingBed._base_manager.none(),
    )
    effective_on = forms.DateField(
        label=_("Move date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    reason = forms.CharField(label=_("Reason"), max_length=255)

    def __init__(self, *args, actor, assignment, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.assignment = assignment
        self.fields["destination_bed"].queryset = housing_beds_for_user(user=actor).filter(
            is_active=True,
            room__is_active=True,
            room__facility__is_active=True,
        ).exclude(pk=assignment.bed_id)
        self.fields["effective_on"].initial = (
            assignment.valid_from if assignment.is_reservation else timezone.localdate()
        )
        _style_fields(self)

    def clean(self):
        cleaned = super().clean()
        bed = cleaned.get("destination_bed")
        effective_on = cleaned.get("effective_on")
        if effective_on and effective_on < timezone.localdate():
            self.add_error("effective_on", _("A move cannot be backdated."))
        if bed and effective_on and not eligible_people_for_housing_period(
            user=self.actor,
            location=bed.room.facility.location,
            valid_from=effective_on,
            allow_planned_arrival=effective_on > timezone.localdate(),
        ).filter(pk=self.assignment.person_id).exists():
            self.add_error(
                "destination_bed",
                _("The Person is not eligible for housing at the destination Location."),
            )
        return cleaned


class HousingFilterForm(forms.Form):
    q = forms.CharField(label=_("Search"), required=False, max_length=120)
    location = forms.ModelChoiceField(
        label=_("Location"),
        required=False,
        queryset=Location._base_manager.none(),
        empty_label=_("All locations in my scope"),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = housing_locations_for_user(user=actor)
        _style_fields(self)
