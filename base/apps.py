"""
This module contains the configuration for the 'base' app.
"""

from django.apps import AppConfig


class BaseConfig(AppConfig):
    """
    Configuration class for the 'base' app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "base"

    def ready(self) -> None:
        ready = super().ready()
        try:
            from base.models import EmployeeShiftDay

            if len(EmployeeShiftDay.objects.all()) == 0:
                days = (
                    ("monday", "Monday"),
                    ("tuesday", "Tuesday"),
                    ("wednesday", "Wednesday"),
                    ("thursday", "Thursday"),
                    ("friday", "Friday"),
                    ("saturday", "Saturday"),
                    ("sunday", "Sunday"),
                )
                for day in days:
                    shift_day = EmployeeShiftDay()
                    shift_day.day = day[0]
                    shift_day.save()
        except Exception as e:
            pass
        return ready
