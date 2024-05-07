"""
Module for Import-Export Resources

This module defines resources for exporting and importing data using the django-import-export library.
"""

from import_export import resources

from .models import Holiday


class HolidayResource(resources.ModelResource):
    class Meta:
        model = Holiday
