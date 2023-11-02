"""
Module for registering LeaveType, LeaveRequest, AvailableLeave, Holiday, and CompanyLeave
models with the Django admin site.
"""
from django.contrib import admin
from .models import LeaveType, LeaveRequest, AvailableLeave, Holiday, CompanyLeave,LeaveAllocationRequest


# Register your models here.
admin.site.register(LeaveType)
admin.site.register(LeaveRequest)
admin.site.register(AvailableLeave)
admin.site.register(Holiday)
admin.site.register(CompanyLeave)
admin.site.register(LeaveAllocationRequest)
