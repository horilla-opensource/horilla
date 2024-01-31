"""
payroll/settings.py

This module is used to write settings contents related to payroll app
"""

from horilla.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "payroll.context_processors.default_currency",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "payroll.context_processors.get_deductions",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "payroll.context_processors.get_active_employees",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "payroll.context_processors.host",
)
