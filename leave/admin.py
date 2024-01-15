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
    LeaverequestComment,
)


# Register your models here.
admin.site.register(LeaveType)
admin.site.register(LeaveRequest)
admin.site.register(AvailableLeave)
admin.site.register(Holiday)
admin.site.register(CompanyLeave)
admin.site.register(LeaveAllocationRequest)
admin.site.register(LeaveRequestConditionApproval)
admin.site.register(LeaverequestComment)
