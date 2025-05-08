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
admin.site.register([EmployeeNote, EmployeeTag, PolicyMultipleFile, Policy, BonusPoint])
admin.site.register([DisciplinaryAction, Actiontype])


class EmployeeWorkInformationAdmin(SimpleHistoryAdmin):
    list_display = (
        "employee_id",
        "department_id",
        "job_position_id",
        "job_role_id",
        "reporting_manager_id",
        "shift_id",
        "work_type_id",
        "company_id",
    )
    search_fields = (
        "employee_id__employee_first_name",
        "employee_id__employee_last_name",
    )


class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "badge_id",
        "employee_first_name",
        "employee_last_name",
        "employee_user_id",
        "is_active",
    )

    search_fields = (
        "badge_id",
        "employee_user_id__username",
        "employee_first_name",
        "employee_last_name",
    )

    list_filter = ("is_active",)

    ordering = ("employee_first_name", "employee_last_name")

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context["custom_message"] = (
            "Are you sure you want to delete this item? This action cannot be undone."
        )
        return super().delete_view(request, object_id, extra_context=extra_context)


admin.site.register(Employee, EmployeeAdmin)
admin.site.register(EmployeeWorkInformation, EmployeeWorkInformationAdmin)
