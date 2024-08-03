"""
Module for registering LeaveType, LeaveRequest, AvailableLeave, Holiday, and CompanyLeave
models with the Django admin site.
"""

from django.apps import apps
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    AvailableLeave,
    CompanyLeave,
    Holiday,
    LeaveAllocationRequest,
    LeaveallocationrequestComment,
    LeaveGeneralSetting,
    LeaveRequest,
    LeaverequestComment,
    LeaveRequestConditionApproval,
    LeaveType,
    RestrictLeave,
)

# Register your models here.
admin.site.register(LeaveType)
admin.site.register(LeaveRequest)
admin.site.register(AvailableLeave)
admin.site.register(Holiday)
admin.site.register(CompanyLeave)
admin.site.register(LeaveAllocationRequest, SimpleHistoryAdmin)
admin.site.register(LeaveRequestConditionApproval)
admin.site.register(LeaverequestComment)
admin.site.register(LeaveallocationrequestComment)
admin.site.register(RestrictLeave)
admin.site.register(LeaveGeneralSetting)
if apps.is_installed("attendance"):
    from .models import CompensatoryLeaveRequest

    admin.site.register(CompensatoryLeaveRequest)
