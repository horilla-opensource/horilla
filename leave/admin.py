"""
Module for registering LeaveType, LeaveRequest, AvailableLeave, Holiday, and CompanyLeave
models with the Django admin site.
"""

from django.contrib import admin
from .models import (
    LeaveRequestConditionApproval,
    LeaveType,
    LeaveRequest,
    AvailableLeave,
    Holiday,
    CompanyLeave,
    LeaveAllocationRequest,
    LeaveallocationrequestComment,
    LeaverequestComment,
    RestrictLeave
)
from simple_history.admin import SimpleHistoryAdmin


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
