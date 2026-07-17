from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from hydra_legalization.models import LegalizationWorkEvent
from hydra_legalization.workload import (
    dispatch_legalization_work_event,
    dispatch_pending_legalization_work_notifications,
)


class Command(BaseCommand):
    help = "Retry pending/failed legalization responsibility notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--event-uuid")

    def handle(self, *args, **options):
        event_uuid = options["event_uuid"]
        if event_uuid:
            try:
                parsed_uuid = UUID(event_uuid)
            except ValueError as error:
                raise CommandError("event UUID is invalid") from error
            event = LegalizationWorkEvent.objects.filter(uuid=parsed_uuid).first()
            if event is None:
                raise CommandError("legalization work event was not found")
            if not dispatch_legalization_work_event(event.pk):
                raise CommandError("event notification delivery failed")
            self.stdout.write(self.style.SUCCESS("Event notification dispatched."))
            return

        try:
            sent, failed, selected = dispatch_pending_legalization_work_notifications(
                limit=options["limit"]
            )
        except ValueError as error:
            raise CommandError(str(error)) from error
        summary = f"Dispatched: {sent}; failed: {failed}; selected: {selected}."
        if failed:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
