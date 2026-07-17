from django.core.management.base import BaseCommand, CommandError
from uuid import UUID

from hydra_coordination.models import OrganizationAccessEvent
from hydra_coordination.services import dispatch_organization_access_event
from hydra_coordination.services import dispatch_pending_organization_notifications


class Command(BaseCommand):
    help = "Retry pending/failed notifications for organization access events."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--event-uuid", type=UUID)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > 1000:
            raise CommandError("--limit must be between 1 and 1000")
        event_uuid = options["event_uuid"]
        if event_uuid:
            event = OrganizationAccessEvent.objects.filter(uuid=event_uuid).first()
            if event is None:
                raise CommandError("organization access event was not found")
            if not dispatch_organization_access_event(event.pk):
                raise CommandError("event notification delivery failed")
            self.stdout.write(self.style.SUCCESS("Event notification dispatched."))
            return
        sent, failed, selected = dispatch_pending_organization_notifications(
            limit=limit
        )
        summary = f"Dispatched: {sent}; failed: {failed}; selected: {selected}."
        if failed:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
