from datetime import date, timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from base.models import Company
from hydra_coordination.models import Location
from hydra_housing.models import (
    HousingAssignment,
    HousingBed,
    HousingFacility,
    HousingRoom,
)
from hydra_people.models import Person


class HousingAssignmentEventMigrationTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = ("hydra_housing", "0001_initial")
    migrate_to = (
        "hydra_housing",
        "0004_housing_reservation_event_constraints",
    )

    def test_existing_assignment_receives_exactly_one_system_origin(self):
        company = Company.objects.create(
            company="Housing migration company",
            address="Migration Street 1",
            country="PL",
            state="Dolnoslaskie",
            city="Siechnice",
            zip="55-011",
            icon="images/ui/company.png",
        )
        location = Location.objects.create(
            company=company,
            name="Migration location",
            code="MIG-HOUSE",
        )
        person = Person.objects.create(
            passport_name="MIGRATION PERSON",
            first_name="Migration",
            last_name="Person",
            date_of_birth=date(1990, 1, 1),
            gender=Person.Gender.UNSPECIFIED,
            citizenship="UA",
            preferred_language=Person.PreferredLanguage.UKRAINIAN,
        )
        facility = HousingFacility.objects.create(
            location=location,
            name="Migration house",
            address="Migration Street 2",
        )
        room = HousingRoom.objects.create(
            facility=facility,
            name="Room 1",
            floor="2",
        )
        bed = HousingBed.objects.create(room=room, label="Bed 1")
        assignment = HousingAssignment.objects.create(
            person=person,
            bed=bed,
            valid_from=timezone.localdate() + timedelta(days=5),
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([self.migrate_to])
        finally:
            # Keep the schema at the current leaf even if a later assertion fails.
            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])

        apps = executor.loader.project_state([self.migrate_to]).apps
        Event = apps.get_model("hydra_housing", "HousingAssignmentEvent")
        MigratedRoom = apps.get_model("hydra_housing", "HousingRoom")
        events = list(Event.objects.filter(assignment_id=assignment.pk))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "reserved")
        self.assertEqual(events[0].source, "system")
        self.assertIsNone(events[0].actor_id)
        self.assertEqual(events[0].effective_on, assignment.valid_from)
        migrated_room = MigratedRoom.objects.select_related(
            "floor_unit__building"
        ).get(pk=room.pk)
        self.assertEqual(migrated_room.floor_unit.name, "2")
        self.assertEqual(
            migrated_room.floor_unit.building.name,
            "Legacy building",
        )
        self.assertEqual(
            migrated_room.floor_unit.building.facility_id,
            facility.pk,
        )
