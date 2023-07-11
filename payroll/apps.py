"""
App configuration for the 'payroll' app.
"""
from django.apps import AppConfig


class PayrollConfig(AppConfig):
    """
    AppConfig for the 'payroll' app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payroll'
