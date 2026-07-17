from django.core.management.base import BaseCommand

from hydra_people.duplicate_services import refresh_duplicate_suggestions_for_person
from hydra_people.models import Person, PersonDuplicateSuggestion


class Command(BaseCommand):
    help = "Refresh deterministic Hydra Person duplicate suggestions."

    def add_arguments(self, parser):
        parser.add_argument("--person-id", type=int)

    def handle(self, *args, **options):
        people = Person.objects.order_by("pk").values_list("pk", flat=True)
        if options["person_id"]:
            people = people.filter(pk=options["person_id"])
        processed = 0
        for person_id in people.iterator(chunk_size=500):
            refresh_duplicate_suggestions_for_person(person_id=person_id)
            processed += 1
        open_count = PersonDuplicateSuggestion.objects.filter(
            state=PersonDuplicateSuggestion.State.OPEN
        ).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Refreshed {processed} Person records; {open_count} open suggestions."
            )
        )
