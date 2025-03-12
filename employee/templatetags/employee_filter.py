from datetime import timedelta

from django import template

register = template.Library()


@register.filter(name="add_days")
def add_days(value, days):
    # Check if value is not None before adding days
    if value is not None:
        return value + timedelta(days=days)
    else:
        return None


@register.filter(name="edit_accessibility")
def edit_accessibility(emp):
    return emp.default_accessibility.filter(feature="profile_edit").exists()
