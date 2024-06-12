"""
attendancefilters.py

This module is used to write custom template filters.

"""

import re, types
from django import template
from django.template.defaultfilters import register
from django.conf import settings


register = template.Library()


numeric_test = re.compile("^\d+$")


@register.filter(name="getattribute")
def getattribute(value, attr: str):
    """
    Gets an attribute of an object dynamically from a string name
    """
    result = ""
    attrs = attr.split("__")
    for attr in attrs:
        if hasattr(value, str(attr)):
            result = getattr(value, attr)
            if isinstance(result, types.MethodType):
                result = result()
            value = result

    return result


@register.filter(name="format")
def format(string: str, instance: object):
    """
    format
    """
    attr_placeholder_regex = r"{([^}]*)}"
    attr_placeholders = re.findall(attr_placeholder_regex, string)

    if not attr_placeholders:
        return string
    flag = instance
    format_context = {}
    for attr_placeholder in attr_placeholders:
        attr_name: str = attr_placeholder
        attrs = attr_name.split("__")
        for attr in attrs:
            value = getattr(instance, attr, "")
            if isinstance(value, types.MethodType):
                value = value()
            instance = value
            format_context[attr_name] = value
        instance = flag
    formatted_string = string.format(**format_context)

    return formatted_string
