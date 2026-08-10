"""
Module for registering LeaveType, LeaveRequest, AvailableLeave
models with the Django admin site.
"""

from django.apps import apps
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from leave.forms import LeaveTypeAdminForm

from .models import (
    AvailableLeave,
    LeaveAllocationRequest,
    LeaveallocationrequestComment,
    LeaveGeneralSetting,
    LeaveRequest,
    LeaverequestComment,
    LeaveRequestConditionApproval,
    LeaveType,
    RestrictLeave,
    UnpaidLeave,
    UnauthorizedExtension,
    EmployeeCategory,
    LeaveAccrualAuditLog,
    LeaveAccrualConfiguration,
    EmployeeServiceAdjustment,
)


class LeaveTypeAdmin(admin.ModelAdmin):
    form = LeaveTypeAdminForm


# Register your models here.
admin.site.register(LeaveType, LeaveTypeAdmin)
admin.site.register(LeaveRequest)
admin.site.register(AvailableLeave)
admin.site.register(LeaveAllocationRequest, SimpleHistoryAdmin)
admin.site.register(LeaveRequestConditionApproval)
admin.site.register(LeaverequestComment)
admin.site.register(LeaveallocationrequestComment)
admin.site.register(RestrictLeave)
admin.site.register(LeaveGeneralSetting)

# Royal Falcon Security - Leave Accrual Policy Models
admin.site.register(EmployeeCategory)
admin.site.register(LeaveAccrualConfiguration)
admin.site.register(UnpaidLeave, SimpleHistoryAdmin)
admin.site.register(UnauthorizedExtension, SimpleHistoryAdmin)
admin.site.register(LeaveAccrualAuditLog)
admin.site.register(EmployeeServiceAdjustment)
if apps.is_installed("attendance"):
    from .models import CompensatoryLeaveRequest

    admin.site.register(CompensatoryLeaveRequest)
