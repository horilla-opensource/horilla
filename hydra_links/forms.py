from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from hydra_coordination.models import Location
from hydra_links.models import PublicHydraLink
from hydra_links.selectors import public_link_location_ids_for_user


class PublicHydraLinkForm(forms.ModelForm):
    class Meta:
        model = PublicHydraLink
        fields = ("kind", "location", "label", "base_url", "order", "is_active")

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["location"].queryset = Location._base_manager.filter(
            pk__in=public_link_location_ids_for_user(user=actor)
        ).select_related("company").order_by("company__company", "name")
        if not actor.has_perm("hydra_links.manage_global_publichydralink"):
            self.fields["kind"].choices = (
                (
                    PublicHydraLink.Kind.LOCATION_TRAINING,
                    PublicHydraLink.Kind.LOCATION_TRAINING.label,
                ),
            )
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "oh-switch__checkbox"
            elif isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("kind") == PublicHydraLink.Kind.ARRIVAL_GUIDANCE
            and not self.actor.has_perm("hydra_links.manage_global_publichydralink")
        ):
            raise ValidationError(_("You cannot manage global public links."))
        return cleaned_data
