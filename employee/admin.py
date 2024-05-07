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

admin.site.register(Employee)
admin.site.register(EmployeeBankDetails)
admin.site.register(EmployeeWorkInformation, SimpleHistoryAdmin)
admin.site.register([EmployeeNote, EmployeeTag, PolicyMultipleFile, Policy, BonusPoint])
admin.site.register([DisciplinaryAction, Actiontype])
