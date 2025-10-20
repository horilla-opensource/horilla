"""
App configuration for the Horilla Automations app.
Initializes model choices and starts automation when the server runs.
"""

import os
import sys

from django.apps import AppConfig


class HorillaAutomationConfig(AppConfig):
    """Configuration class for the Horilla Automations Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_automations"

    def ready(self) -> None:
        ready = super().ready()
        if not (
            len(sys.argv) >= 2
            and sys.argv[1] == "runserver"
            and os.environ.get("RUN_MAIN") == "true"
        ):
            return ready
        try:

            from base.templatetags.horillafilters import app_installed
            from employee.models import Employee
            from horilla_automations.methods.methods import get_related_models
            from horilla_automations.models import MODEL_CHOICES

            recruitment_installed = False
            if app_installed("recruitment"):
                recruitment_installed = True

            models = [Employee]
            if recruitment_installed:
                from recruitment.models import Candidate

                models.append(Candidate)

            main_models = models
            for main_model in main_models:
                related_models = get_related_models(main_model)

                for model in related_models:
                    path = f"{model.__module__}.{model.__name__}"
                    MODEL_CHOICES.append((path, model.__name__))
            MODEL_CHOICES.append(("employee.models.Employee", "Employee"))
            MODEL_CHOICES.append(
                ("pms.models.EmployeeKeyResult", "Employee Key Results")
            )

            MODEL_CHOICES = list(set(MODEL_CHOICES))
            try:
                from horilla_automations.signals import start_automation

                start_automation()
            except Exception as e:
                print(e)
                """
                Migrations are not affected yet
                """
        except:
            """
            Models not ready yet
            """
        return ready
