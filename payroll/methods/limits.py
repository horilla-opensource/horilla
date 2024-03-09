"""
limit.py

This module is used to compute the limit for allowance and deduction
"""

# from payroll.models.models import Allowance


def compute_limit(component, amount, _day_dict):
    """
    limit compute method
    """
    # day_dict = [
    #     {
    #         "month": 5,
    #         "year": 2023,
    #         "days": 31,
    #         "start_date": "2023-05-01",
    #         "end_date": "2023-05-31",
    #         "working_days_on_period": 27,
    #         "working_days_on_month": 27,
    #         "per_day_amount": 555.5555555555555,
    #     },
    #     {
    #         "month": 6,
    #         "year": 2023,
    #         "days": 30,
    #         "start_date": "2023-06-01",
    #         "end_date": "2023-06-23",
    #         "working_days_on_period": 20,
    #         "working_days_on_month": 26,
    #         "per_day_amount": 576.9230769230769,
    #     },
    # ]
    if component.has_max_limit:
        max_amount = component.maximum_amount
        amount = min(amount, max_amount)
    # if (
    #     isinstance(component, Allowance)
    #     and component.has_max_limit
    #     and not component.is_fixed
    # ):
    #     amount = min(amount, max_amount)

    # elif component.has_max_limit:
    # unit = component.maximum_unit
    # amount = 0
    # if unit == "month_working_days":
    #     for month in day_dict:
    #         working_days_on_month = month["working_days_on_month"]
    #         working_days_on_period = month["working_days_on_period"]
    #         # maximum amount for one working day
    #         max_day_amount = max_amount / working_days_on_month
    #         amount = amount + (max_day_amount * working_days_on_period)

    return amount
