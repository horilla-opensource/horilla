"""
group_by.py

This module is used to make queryset by grups
"""
from django.db import models


def group_by_queryset(queryset, group_field):
    """
    This method is used to make group by field for the queryset
    """
    fields_split = group_field.split("__")
    model = queryset.model
    is_fk_field = isinstance(getattr(model, group_field, None), models.ForeignKey)
    model_copy = model
    field_obj = None
    for field in fields_split:
        field_obj = model_copy._meta.get_field(field)
        model_copy = field_obj.__dict__["related_model"]

    if fields_split or is_fk_field:
        groupers = model_copy.objects.all()
        groups = [
            {
                "grouper": grouper,
                "instances": len(queryset.filter(**{group_field: grouper.id})),
            }
            for grouper in groupers
        ]
    else:
        groupers = set(queryset.values_list(group_field, flat=True))
        groups = [
            {
                "grouper": grouper,
                "instances": queryset.filter(**{group_field: grouper}),
            }
            for grouper in groupers
        ]
    return groups
