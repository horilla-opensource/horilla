"""
admin.py

This page is used to register the model with admins site.
"""

from django.contrib import admin
from employee.models import (
    BonusPoint,
    Employee,
    EmployeeWorkInformation,
    EmployeeBankDetails,
    EmployeeNote,
    EmployeeTag,
    PolicyMultipleFile,
    Policy,
    DisciplinaryAction,
    Actiontype,
)
from simple_history.admin import SimpleHistoryAdmin


# Register your models here.

admin.site.register(Employee)
admin.site.register(EmployeeBankDetails)
admin.site.register(EmployeeWorkInformation, SimpleHistoryAdmin)
admin.site.register([EmployeeNote, EmployeeTag, PolicyMultipleFile, Policy, BonusPoint])
admin.site.register([DisciplinaryAction, Actiontype])
