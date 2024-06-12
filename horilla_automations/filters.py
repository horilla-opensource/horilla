"""
horilla_automations/filters.py
"""

from horilla.filters import HorillaFilterSet, django_filters
from horilla_automations.models import MailAutomation


class AutomationFilter(HorillaFilterSet):
    """
    AutomationFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = MailAutomation
        fields = "__all__"
