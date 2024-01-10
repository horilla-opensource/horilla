"""
admin.py

Used to register models on admin site
"""
from django.contrib import admin
from payroll.models.models import (
    Allowance,
    Deduction,
    FilingStatus,
    Payslip,
    WorkRecord,
    LoanAccount,
)
from payroll.models.tax_models import (
    PayrollSettings,
    TaxBracket,
)
from payroll.models.models import Contract

# Register your models here.
admin.site.register(FilingStatus)
admin.site.register(TaxBracket)
admin.site.register([Contract, WorkRecord])
admin.site.register(Allowance)
admin.site.register(Deduction)
admin.site.register(Payslip)
admin.site.register(PayrollSettings)
admin.site.register(LoanAccount)
