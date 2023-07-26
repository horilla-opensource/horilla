"""
context_processor.py

This module is used to register context processor`
"""
from payroll.models import tax_models as models


def default_currency(request):
    """
    This method will return the currency
    """
    if models.PayrollSettings.objects.first() is None:
        settings = models.PayrollSettings()
        settings.currency_symbol = "$"
        settings.save()
    symbol = models.PayrollSettings.objects.first().currency_symbol
    return {"currency": request.session.get("currency", symbol)}
