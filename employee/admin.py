"""
admin.py

This page is used to register the model with admins site.
"""
from django.contrib import admin
from employee.models import Employee, EmployeeWorkInformation, EmployeeBankDetails
from simple_history.admin import SimpleHistoryAdmin


# Register your models here.

admin.site.register(Employee)
admin.site.register(EmployeeBankDetails)
admin.site.register(EmployeeWorkInformation, SimpleHistoryAdmin)
