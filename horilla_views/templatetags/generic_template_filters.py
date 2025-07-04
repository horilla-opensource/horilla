"""
horilla_views/templatetags/generic_template_filters.py

This module is used to write custom template filters.

"""

import datetime
import functools
import re
import types

from django import template
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.db.models.utils import AltersData
from django.template.defaultfilters import register

from horilla.config import import_method
from horilla.horilla_middlewares import _thread_locals

register = template.Library()


numeric_test = re.compile(r"^\d+$")

date_format_mapping = {
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD.MM.YYYY": "%d.%m.%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MMMM D, YYYY": "%B %d, %Y",
    "DD MMMM, YYYY": "%d %B, %Y",
    "MMM. D, YYYY": "%b. %d, %Y",
    "D MMM. YYYY": "%d %b. %Y",
    "dddd, MMMM D, YYYY": "%A, %B %d, %Y",
}

time_format_mapping = {
    "hh:mm A": "%I:%M %p",
    "HH:mm": "%H:%M",
}


@register.filter(name="selected_format")
def selected_format(date: datetime.date, company: object = None) -> str:
    if isinstance(date, datetime.date):
        format = (
            company.date_format if company and company.date_format else "MMM. D, YYYY"
        )
        strftime_format = date_format_mapping.get(format, "%b. %d, %Y")
        return date.strftime(strftime_format)
    elif isinstance(date, datetime.time):
        format = company.time_format if company and company.time_format else "hh:mm A"
        strftime_format = time_format_mapping.get(format, "%I:%M %p")
        return date.strftime(strftime_format)
    return date


@register.filter(name="getattribute")
def getattribute(value, attr: str):
    """
    Gets an attribute of an object dynamically from a string name
    """
    result = ""
    attrs = attr.split("__")
    for attr in attrs:
        if isinstance(
            value,
            AltersData,
        ) and hasattr(value, "through"):
            result = []
            queryset = value.all()
            for record in queryset:
                result.append(getattribute(record, attr))
        elif hasattr(value, str(attr)):
            result = getattr(value, attr)
            if isinstance(result, (types.MethodType, functools.partial)):
                result = result()
            value = result
        else:
            return getattr(value, attr, "")

    return result


@register.filter(name="format")
def format(string: str, instance: object):
    """
    Format a string by resolving instance attributes, including method calls like get_status_display.
    """
    attr_placeholder_regex = r"{([^}]*)}"
    attr_placeholders = re.findall(attr_placeholder_regex, string)

    if not attr_placeholders:
        return string

    original_instance = instance
    format_context = {}

    for attr_placeholder in attr_placeholders:
        instance = original_instance  # reset each time
        attrs = attr_placeholder.split("__")
        try:
            for attr in attrs:
                instance = getattr(instance, attr, "")
            # If final resolved attr is a method, call it
            if callable(instance):
                instance = instance()
        except Exception:
            instance = ""
        format_context[attr_placeholder] = instance

    return string.format(**format_context)


@register.filter("accessibility")
def accessibility(method: str, instance=None):
    if method:
        request = getattr(_thread_locals, "request")
        method = import_method(method)
        return method(
            request,
            instance,
            PermWrapper(request.user),
        )
    return True


@register.filter("col")
def col(field: object):
    """
    Method to get field col sepration
    """
    field_name = field.name
    cols = getattr(field.form, "cols", {})
    return cols.get(field_name, 6)


@register.filter("get_item")
def get_item(dictionary: dict, key: str):
    """
    get_item method to access from dictionary
    """
    if dictionary:
        return dictionary.get(key, "")
    return ""


@register.filter("get_id")
def get_id(string: str):
    """
    Generate target/id for the generic delete summary
    """
    return string.split("-")[0].lower().replace(" ", "")
