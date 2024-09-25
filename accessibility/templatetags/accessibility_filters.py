"""
accessibility/templatestags/accessibility_filters.py
"""

from django import template

from accessibility.methods import check_is_accessible

register = template.Library()


@register.filter(name="feature_is_accessible")
def feature_is_accessible(feature, request):
    """
    template
    """
    return check_is_accessible(
        feature, request.session.session_key, request.user.employee_get
    )
