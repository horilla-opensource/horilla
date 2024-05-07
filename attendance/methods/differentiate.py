"""
differentiate.py

This module is used write custom methods
"""

from datetime import datetime

from django.db import models


def get_diff_obj(first_instance, other_instance, exclude_fields=None):
    """
    Compare the fields of two instances and identify the changes.

    Args:
        first_instance: The first instance to compare.
        other_instance: The second instance to compare.
        exclude_fields: A list of field names to exclude from comparison (optional).

    Returns:
        A dictionary of changed fields with their old and new values.
    """
    difference = {}

    fields_to_compare = first_instance._meta.fields

    if exclude_fields:
        fields_to_compare = [
            field for field in fields_to_compare if field.name not in exclude_fields
        ]

    for field in fields_to_compare:
        old_value = getattr(first_instance, field.name)
        new_value = getattr(other_instance, field.name)

        if old_value != new_value:
            difference[field.name] = (old_value, new_value)

    return difference


def get_diff_dict(first_dict, other_dict, model=None):
    """
    Compare two dictionaries and identify differing key-value pairs.

    Args:
        first_dict: The first dictionary to compare.
        other_dict: The second dictionary to compare.
        model: The model class

    Returns:
        A dictionary of differing keys with their old and new values.
    """
    # model is passed as argument if any need of verbose name instead of field name
    difference = {}
    if model is None:
        for key in first_dict:
            if first_dict[key] != other_dict[key]:
                # get the verbose name of the field
                difference[key] = (first_dict[key], other_dict[key])
        return difference
    for key in first_dict:
        if first_dict[key] != other_dict[key]:
            # get the verbose name of the field
            field = model._meta.get_field(key)
            verb_key = field.verbose_name
            value = first_dict[key]
            other_value = other_dict[key]
            if isinstance(field, models.DateField):
                if value is not None and value != "None":
                    value = datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
                if other_value is not None and other_value != "None":
                    other_value = datetime.strptime(other_value, "%Y-%m-%d").strftime(
                        "%d %b %Y"
                    )
            elif isinstance(field, models.TimeField):
                if value is not None and value != "None":
                    if len(value.split(":")) == 2:
                        value = value + ":00"
                    value = datetime.strptime(value, "%H:%M:%S").strftime("%I:%M %p")
                if other_value is not None and value != "None":
                    if len(other_value.split(":")) == 2:
                        other_value = other_value + ":00"
                    if other_value != "None":
                        other_value = datetime.strptime(
                            other_value, "%H:%M:%S"
                        ).strftime("%I:%M %p")
                    else:
                        other_value = "None"
            elif isinstance(field, models.ForeignKey):
                if value is not None and len(str(value)):
                    value = field.related_model.objects.get(id=value)
                if other_value is not None and len(str(other_value)):
                    other_value = field.related_model.objects.get(id=other_value)
            difference[verb_key] = (value, other_value)
    return difference
