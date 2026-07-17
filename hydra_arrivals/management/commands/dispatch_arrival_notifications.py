from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from hydra_arrivals.automation import (
    dispatch_arrival_automation_event,
    dispatch_pending_arrival_notifications,
)
from hydra_arrivals.models import ArrivalAutomationEvent


class Command(BaseCommand):
    help = "Retry pending/failed arrival automation notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--event-uuid", type=UUID)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > 1000:
            raise CommandError("--limit must be between 1 and 1000")
        event_uuid = options["event_uuid"]
        if event_uuid:
            event = ArrivalAutomationEvent.objects.filter(uuid=event_uuid).first()
            if event is None:
                raise CommandError("arrival automation event was not found")
            if not dispatch_arrival_automation_event(event.pk):
                raise CommandError("event notification delivery failed")
            self.stdout.write(self.style.SUCCESS("Event notification dispatched."))
            return
        sent, failed, selected = dispatch_pending_arrival_notifications(limit=limit)
        summary = f"Dispatched: {sent}; failed: {failed}; selected: {selected}."
        if failed:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
