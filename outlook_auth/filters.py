"""
outlook_auth/filters.py
"""

import django_filters

from outlook_auth import models


class AzureApiFilter(django_filters.FilterSet):
    """
    AzureApiFilter
    """

    search = django_filters.CharFilter(
        field_name="outlook_email", lookup_expr="icontains"
    )

    class Meta:
        """
        Meta class for additional options"""

        fields = [
            "search",
        ]
        model = models.AzureApi
