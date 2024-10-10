from django.http import QueryDict
from employee.models import Employee
from rest_framework.pagination import PageNumberPagination
from base.models import *
from employee.models import *


def get_next_badge_id():
    """
    This method is used to generate badge id
    """
    try:
        highest_badge_id = Employee.objects.filter(
            badge_id__isnull=False).order_by('-badge_id').first().badge_id
    except AttributeError:
        highest_badge_id = None

    # Increment the badge_id if it exists, otherwise start from '1'
    if highest_badge_id:
        if '#' in highest_badge_id:
            prefix, number = highest_badge_id.split(
                '#')  # Split prefix and number
            # Increment the number
            new_number = str(int(number) + 1).zfill(len(number))
            new_badge_id = f"{prefix}#{new_number}"
        else:
            # Add number to existing prefix
            new_badge_id = f"{highest_badge_id}#001"
    else:
        new_badge_id = "EMP#001"  # Default start badge ID if no employees exist
    return new_badge_id
