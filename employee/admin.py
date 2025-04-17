"""
admin.py

This page is used to register the model with admins site.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from employee.models import (
    Actiontype,
    BonusPoint,
    DisciplinaryAction,
    Employee,
    EmployeeBankDetails,
    EmployeeNote,
    EmployeeTag,
    EmployeeWorkInformation,
    Policy,
    PolicyMultipleFile,
)

# Register your models here.

# admin.site.register(Employee)
admin.site.register(EmployeeBankDetails)
admin.site.register(EmployeeWorkInformation, SimpleHistoryAdmin)
admin.site.register([EmployeeNote, EmployeeTag, PolicyMultipleFile, Policy, BonusPoint])
admin.site.register([DisciplinaryAction, Actiontype])


from django.contrib import admin


class MyModelAdmin(admin.ModelAdmin):
    def delete_view(self, request, object_id, extra_context=None):
        # Add custom context for the delete confirmation page
        extra_context = extra_context or {}
        extra_context["custom_message"] = (
            "Are you sure you want to delete this item? This action cannot be undone."
        )
        # Call the superclass's delete_view to render the page
        return super().delete_view(request, object_id, extra_context=extra_context)

    def get_deleted_objects(self, objs, request):
        response = super().get_deleted_objects(objs, request)
        return response


admin.site.register(Employee, MyModelAdmin)
