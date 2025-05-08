"""
horilla_automation/methods/serialize.py
"""

from django import forms
from django.db import models


def get_related_model_fields(model):
    fields = []
    MODEL = model

    class _InstantModelForm(forms.ModelForm):
        class Meta:
            model = MODEL
            fields = "__all__"

    instant_form = _InstantModelForm()
    for field_name, field in instant_form.fields.items():
        field_info = {
            "name": field_name,
            "type": field.widget.__class__.__name__,
            "label": field.label,
            "required": field.required,
        }
        fields.append(field_info)
        if hasattr(field, "queryset"):
            field_info["options"] = [
                {"value": choice.pk, "label": str(choice)} for choice in field.queryset
            ]
        elif hasattr(field, "choices") and field.choices:
            field_info["options"] = [
                {"value": choice[0], "label": choice[1]} for choice in field.choices
            ]

    return fields


def serialize_form(form, prefix=""):
    """
    serialize_form
    """
    form_fields = form.fields
    form_structure = []

    for field_name, field in form_fields.items():
        field_structure = {
            "name": prefix + field_name,
            "type": field.widget.__class__.__name__,
            "label": field.label,
            "required": field.required,
        }

        # If the field is a CharField, include the max_length property
        if isinstance(field, forms.CharField):
            field_structure["max_length"] = field.max_length

        # If the field is a Select field, include the options
        if isinstance(field.widget, forms.Select) and not isinstance(
            field, forms.NullBooleanField
        ):
            field_structure["options"] = [
                {"value": str(key), "label": str(value)} for key, value in field.choices
            ]
        form_structure.append(field_structure)

        if isinstance(field, forms.ModelChoiceField):
            related_model = field.queryset.model
            related_fields = get_related_model_fields(related_model)
            related_field_structures = []
            for related_field in related_fields:
                related_field_structure = {
                    "name": prefix + field_name + "__" + related_field["name"],
                    "type": related_field["type"],
                    "label": related_field["label"].capitalize() + " | " + field.label,
                    "required": related_field["required"],
                }
                if related_field.get("options"):
                    related_field_structure["options"] = related_field["options"]
                form_structure.append(related_field_structure)
            field_structure["related_fields"] = related_field_structures

    return form_structure
