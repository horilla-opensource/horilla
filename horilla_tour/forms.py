"""
Model forms for authoring tours and steps from the Settings UI.

Both extend ``base.forms.ModelForm`` so fields automatically receive Horilla's
``oh-*`` styling / Select2 widgets, consistent with the rest of the product.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm
from horilla_tour.models import Tour, TourStep


class TourForm(ModelForm):
    """Create / edit a tour (the parent record)."""

    class Meta:
        model = Tour
        fields = [
            "title",
            "slug",
            "description",
            "page_match",
            "match_type",
            "audience",
            "trigger",
            "priority",
            "icon",
            "show_progress",
            "allow_close",
            "is_published",
            "company_id",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class TourStepForm(ModelForm):
    """Create / edit a single step. ``tour`` is injected by the view."""

    class Meta:
        model = TourStep
        fields = [
            "sequence",
            "title",
            "description",
            "element_selector",
            "side",
            "align",
            "page_match",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
