from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from onboarding.models import (
    CandidateStage,
    CandidateTask,
    OnboardingStage,
    OnboardingTask,
)
from recruitment.models import Candidate


@transaction.atomic
def ensure_candidate_onboarding(*, candidate, actor=None):
    """Create the reused Horilla onboarding rows exactly once.

    Callers are responsible for authorization. Locking the Candidate makes the
    check/create sequence safe for concurrent Hydra and Horilla entry points.
    Existing duplicate task rows are reported instead of being silently
    deleted or merged.
    """

    locked_candidate = (
        Candidate._base_manager.select_for_update(of=("self",))
        .select_related("recruitment_id")
        .get(pk=candidate.pk)
    )
    if locked_candidate.recruitment_id_id is None:
        raise ValidationError(
            {"candidate": _("The candidate has no recruitment.")}
        )

    stages = OnboardingStage._base_manager.select_for_update().filter(
        recruitment_id=locked_candidate.recruitment_id_id
    )
    initial_stage = stages.order_by("sequence", "pk").first()
    if initial_stage is None:
        raise ValidationError(
            {"candidate": _("Configure an onboarding stage for this recruitment first.")}
        )

    candidate_stage = (
        CandidateStage._base_manager.select_for_update()
        .filter(candidate_id=locked_candidate)
        .first()
    )
    if candidate_stage is None:
        candidate_stage = CandidateStage.objects.create(
            candidate_id=locked_candidate,
            onboarding_stage_id=initial_stage,
            sequence=initial_stage.sequence or 0,
        )
    elif (
        candidate_stage.onboarding_stage_id.recruitment_id_id
        != locked_candidate.recruitment_id_id
    ):
        raise ValidationError(
            {"candidate": _("The existing onboarding stage belongs to another recruitment.")}
        )

    created_tasks = []
    configured_tasks = list(
        OnboardingTask._base_manager.select_for_update()
        .select_related("stage_id")
        .filter(stage_id__recruitment_id=locked_candidate.recruitment_id_id)
        .order_by("stage_id__sequence", "pk")
    )
    for task in configured_tasks:
        existing_rows = list(
            CandidateTask._base_manager.select_for_update()
            .filter(
                candidate_id=locked_candidate,
                onboarding_task_id=task,
            )
            .order_by("pk")[:2]
        )
        if len(existing_rows) > 1:
            raise ValidationError(
                {
                    "candidate": _(
                        "Duplicate onboarding task assignments require an integrity review."
                    )
                }
            )
        if existing_rows:
            candidate_task = existing_rows[0]
            if candidate_task.stage_id_id is None:
                candidate_task.stage_id = task.stage_id
                candidate_task.save(update_fields=("stage_id",))
            elif candidate_task.stage_id_id != task.stage_id_id:
                raise ValidationError(
                    {
                        "candidate": _(
                            "An onboarding task is linked to an inconsistent stage."
                        )
                    }
                )
        else:
            candidate_task = CandidateTask.objects.create(
                candidate_id=locked_candidate,
                stage_id=task.stage_id,
                onboarding_task_id=task,
            )
            created_tasks.append(candidate_task)
        task.candidates.add(locked_candidate)

    update_fields = ["start_onboard"]
    locked_candidate.start_onboard = True
    if actor is not None and hasattr(locked_candidate, "modified_by_id"):
        locked_candidate.modified_by = actor
        update_fields.append("modified_by")
    locked_candidate.save(update_fields=tuple(update_fields))
    return candidate_stage, tuple(created_tasks)
