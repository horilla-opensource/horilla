"""
Register models with the Django admin site.

This section of code registers the BiometricDevices and BiometricEmployees models
with the Django admin site, allowing them to be managed via the admin interface.

"""

from django.contrib import admin

from .models import BiometricDevices, BiometricEmployees, COSECAttendanceArguments

# Register your models here.
admin.site.register(BiometricDevices)
admin.site.register(BiometricEmployees)
admin.site.register(COSECAttendanceArguments)
