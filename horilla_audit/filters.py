"""
filters.py

This page is used to register filter for horilla audit  models

"""

import django_filters

from base.filters import FilterSet
from horilla_audit.models import AuditTag


class AudiTagFilter(FilterSet):
    """
    filter class for audit tag model
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = AuditTag
        fields = ["title", "highlight"]
