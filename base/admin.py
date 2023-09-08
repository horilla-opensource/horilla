"""
admin.py

This page is used to register base models with admins site.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from base.models import (
    Company,
    Department,
    JobPosition,
    JobRole,
    EmployeeShiftSchedule,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeType,
    WorkType,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    RotatingShift,
    RotatingShiftAssign,
    ShiftRequest,
    WorkTypeRequest,
)

# Register your models here.

admin.site.register(Company)
admin.site.register(Department, SimpleHistoryAdmin)
admin.site.register(JobPosition)
admin.site.register(JobRole)
admin.site.register(EmployeeShift)
admin.site.register(EmployeeShiftSchedule)
admin.site.register(EmployeeShiftDay)
admin.site.register(EmployeeType)
admin.site.register(WorkType)
admin.site.register(RotatingWorkType)
admin.site.register(RotatingWorkTypeAssign)
admin.site.register(RotatingShift)
admin.site.register(RotatingShiftAssign)
admin.site.register(ShiftRequest)
admin.site.register(WorkTypeRequest)
