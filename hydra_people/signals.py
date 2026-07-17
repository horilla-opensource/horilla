"""Guards and defaults that close legacy recruitment mutation paths."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from django.db.models.signals import post_save
from django.dispatch import receiver

from horilla.signals import pre_bulk_update
from hydra_people.models import Person
from hydra_people.recruitment_workflow import create_default_transition_rules_for_stage
from recruitment.models import Candidate, Stage


@receiver(post_save, sender=Person)
def refresh_person_duplicate_suggestions(sender, instance, **kwargs):
    person_id = instance.pk

    def refresh_after_commit():
        from hydra_people.duplicate_services import (
            refresh_duplicate_suggestions_for_person,
        )

        try:
            refresh_duplicate_suggestions_for_person(person_id=person_id)
        except (OperationalError, ProgrammingError):
            # Fingerprints may be saved while the duplicate tables are migrating.
            return

    transaction.on_commit(refresh_after_commit)


@receiver(post_save, sender=Stage)
def create_transition_rules_for_new_stage(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        create_default_transition_rules_for_stage(stage=instance)
    except (OperationalError, ProgrammingError):
        # The rule table does not exist while the schema migration is running.
        return


@receiver(pre_bulk_update, sender=Candidate)
def block_linked_candidate_stage_bulk_update(sender, queryset, kwargs, **signal_kwargs):
    if not {"stage_id", "stage_id_id"}.intersection(kwargs):
        return
    if queryset.filter(hydra_person_link__isnull=False).exists():
        raise ValidationError(
            {"stage_id": "Use the controlled Hydra recruitment transition."}
        )
