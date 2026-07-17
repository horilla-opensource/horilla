from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from hydra_legalization.services import adopt_legacy_legalization_case_policy


class Command(BaseCommand):
    help = (
        "Adopt approved authorities into one unresolved legacy legalization case "
        "and append an immutable audit event."
    )

    def add_arguments(self, parser):
        parser.add_argument("--case", required=True, type=UUID, dest="case_uuid")
        parser.add_argument(
            "--authority",
            required=True,
            action="append",
            type=UUID,
            dest="authority_uuids",
        )
        parser.add_argument("--actor", required=True)
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        actor = get_user_model().objects.filter(username=options["actor"]).first()
        if actor is None:
            raise CommandError("--actor user was not found")
        try:
            case, event = adopt_legacy_legalization_case_policy(
                case_uuid=options["case_uuid"],
                authority_uuids=options["authority_uuids"],
                reason=options["reason"],
                actor=actor,
            )
        except (PermissionDenied, ValidationError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Adopted authority policy for case {case.uuid}; audit event {event.uuid}."
            )
        )
