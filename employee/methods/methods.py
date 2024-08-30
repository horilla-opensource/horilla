"""
employee/methods.py
"""

import re
from itertools import groupby

from django.db import models

from base.context_processors import get_initial_prefix
from employee.models import Employee


def dynamic_prefix_sort(item):
    # Assuming the dynamic prefix length is 3
    prefix = get_initial_prefix(None)["get_initial_prefix"]

    prefix_length = len(prefix) if len(prefix) >= 3 else 3
    return item[:prefix_length]


def get_ordered_badge_ids():
    """
    This method is used to return ordered badge ids
    """
    employees = Employee.objects.all()
    data = (
        employees.exclude(badge_id=None)
        .order_by("badge_id")
        .values_list("badge_id", flat=True)
    )
    if not data.first():
        data = [
            f'{get_initial_prefix(None)["get_initial_prefix"]}0001',
        ]
    # Separate pure number strings and convert them to integers
    pure_numbers = [int(item) for item in data if item.isdigit()]

    # Remove pure number strings from the original data
    data = [item for item in data if not item.isdigit()]

    # Sort the remaining data by dynamic prefixes
    sorted_data = sorted(data, key=dynamic_prefix_sort)

    # Group the sorted data by dynamic prefixes
    grouped_data = [
        list(group) for _, group in groupby(sorted_data, key=dynamic_prefix_sort)
    ]

    # Sort each subgroup alphabetically and numerically
    for group in grouped_data:
        group.sort()
        filtered_group = [
            item for item in group if any(char.isdigit() for char in item)
        ]
        filtered_group.sort(key=lambda x: int("".join(filter(str.isdigit, x))))

    # Create a list containing the first and last items from each group
    result = [[group[0], group[-1]] for group in grouped_data]

    # Add the list of pure numbers at the beginning
    if pure_numbers:
        result.insert(0, [pure_numbers[0], pure_numbers[-1]])
    return result


def check_relationship_with_employee_model(model):
    related_fields = []
    for field in model._meta.get_fields():
        # Check if the field is a ForeignKey or ManyToManyField and related to Employee
        if isinstance(field, models.ForeignKey) and field.related_model == Employee:
            related_fields.append((field.name, "ForeignKey"))
        elif (
            isinstance(field, models.ManyToManyField)
            and field.related_model == Employee
        ):
            related_fields.append((field.name, "ManyToManyField"))
    return related_fields
