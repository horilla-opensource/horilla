"""
dynamic_fields/templatetags/hdf_tags.py
"""

from django import template

register = template.Library()


@register.filter("exclude_removed_df")
def exclude_removed_df(line: object):
    """
    Used to exclude the removed dfs from the fieldset
    """
    fields = line.fields
    rmvdf = line.form.removed_hdf
    for field in fields:
        if field in rmvdf:
            return False
    return line
