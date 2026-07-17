import json

from django.core.management.base import BaseCommand, CommandError

from hydra_ops.maintenance import maintenance_health


class Command(BaseCommand):
    help = "Fail unless the Hydra maintenance heartbeat and failure state are healthy."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        ok, detail = maintenance_health()
        if options["json"]:
            self.stdout.write(json.dumps({"status": "healthy" if ok else "unhealthy"}))
        elif ok:
            self.stdout.write(self.style.SUCCESS(detail))
        if not ok:
            raise CommandError(detail)
