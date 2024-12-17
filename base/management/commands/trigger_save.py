from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Save all instances of the specified model"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label", type=str, help="App label of the model (e.g., attendance)"
        )
        parser.add_argument(
            "model_name",
            type=str,
            help="Name of the model to save instances for (e.g., Attendance)",
        )

    def handle(self, *args, **kwargs):
        app_label = kwargs["app_label"]
        model_name = kwargs["model_name"]

        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            raise CommandError(
                f"Model '{model_name}' not found in the app '{app_label}'."
            )

        try:
            instances = model.objects.all()
            print(
                f"Saving {len(instances)} instances of '{model_name}' in app '{app_label}'. Please wait....."
            )
            for instance in instances:
                instance.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"All instances of '{model_name}' in app '{app_label}' have been saved."
                )
            )
        except Exception as e:
            raise CommandError(
                f"An error occurred while saving instances of '{model_name}' in app '{app_label}': {e}"
            )
