"""
Module for defining filters related to biometric devices.

This module contains the definition of the BiometricDeviceFilter class,
which is used to filter instances of BiometricDevices
"""

import django_filters

from base.filters import FilterSet
from biometric.models import BiometricDevices


class BiometricDeviceFilter(FilterSet):
    """
    Filter class for querying biometric devices.

    This class defines filters for querying instances of BiometricDevices
    based on various criteria such as name, machine type, and activity status.
    """

    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        """
        Meta class to add additional options
        """

        model = BiometricDevices
        fields = [
            "name",
            "machine_type",
            "is_active",
            "is_scheduler",
            "is_live",
        ]
