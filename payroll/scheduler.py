"""
scheduler.py

This module is used to register scheduled tasks
"""

from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from .models.models import Contract


def expire_contract():
    """
    Finds all active contracts whose end date is earlier than the current date
    and updates their status to "expired".
    """
    Contract.objects.filter(
        contract_status="active", contract_end_date__lt=date.today()
    ).update(contract_status="expired")
    return


scheduler = BackgroundScheduler()
scheduler.add_job(expire_contract, "interval", hours=4)
scheduler.start()
