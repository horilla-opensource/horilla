from django.apps import AppConfig

from horilla_automations.signals import start_automation


class HorillaAutomationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_automations"

    def ready(self) -> None:
        ready = super().ready()
        try:
            from employee.models import Employee
            from horilla_automations.methods.methods import get_related_models
            from horilla_automations.models import MODEL_CHOICES
            from recruitment.models import Candidate

            main_models = [Candidate, Employee]
            for main_model in main_models:
                related_models = get_related_models(main_model)

                for model in related_models:
                    path = f"{model.__module__}.{model.__name__}"
                    MODEL_CHOICES.append((path, model.__name__))
            MODEL_CHOICES.append(("employee.models.Employee", "Employee"))
            MODEL_CHOICES = list(set(MODEL_CHOICES))
            try:
                start_automation()
            except:
                """
                Migrations are not affected yet
                """
        except:
            """
            Models not ready yet
            """
        return ready
