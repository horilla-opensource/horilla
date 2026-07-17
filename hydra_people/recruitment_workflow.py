"""Controlled, scope-safe recruitment-stage transitions for linked applications."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from hydra_people.models import (
    CandidateStageTransition,
    RecruitmentStageTransitionRule,
)
from recruitment.models import Candidate, Stage


TRANSITION_PERMISSIONS = (
    "hydra_people.view_person",
    "recruitment.view_candidate",
    "recruitment.change_candidate",
)


def default_transition_rule_values(*, from_stage, to_stage):
    """Preserve legacy flexibility while making risky moves explicitly reasoned."""

    from_sequence = from_stage.sequence if from_stage.sequence is not None else 0
    to_sequence = to_stage.sequence if to_stage.sequence is not None else 0
    is_backward_or_skip = to_sequence <= from_sequence or abs(to_sequence - from_sequence) > 1
    return {
        "requires_reason": to_stage.stage_type == "cancelled" or is_backward_or_skip,
        "requires_schedule_date": False,
        "requires_joining_date": to_stage.stage_type == "hired",
        "allow_override": True,
    }


def create_default_transition_rules_for_stage(*, stage):
    """Create directed defaults for a new stage without overwriting configured rules."""

    other_stages = list(
        Stage._base_manager.filter(
            recruitment_id_id=stage.recruitment_id_id,
            is_active=True,
        ).exclude(pk=stage.pk)
    )
    for other_stage in other_stages:
        for from_stage, to_stage in ((stage, other_stage), (other_stage, stage)):
            RecruitmentStageTransitionRule.objects.get_or_create(
                recruitment_id=stage.recruitment_id_id,
                from_stage=from_stage,
                to_stage=to_stage,
                defaults=default_transition_rule_values(
                    from_stage=from_stage,
                    to_stage=to_stage,
                ),
            )


def transition_rules_for_candidate(*, candidate):
    if not candidate.stage_id_id or not candidate.recruitment_id_id:
        return RecruitmentStageTransitionRule.objects.none()
    return RecruitmentStageTransitionRule.objects.filter(
        recruitment_id=candidate.recruitment_id_id,
        from_stage_id=candidate.stage_id_id,
        is_active=True,
        to_stage__is_active=True,
    ).select_related("to_stage")


def _require_transition_scope(*, actor, candidate):
    if not actor.is_authenticated or not actor.has_perms(TRANSITION_PERMISSIONS):
        raise PermissionDenied
    if actor.is_superuser:
        return

    from hydra_people.recruitment_selectors import linked_candidates_for_user

    if not linked_candidates_for_user(user=actor).filter(pk=candidate.pk).exists():
        raise PermissionDenied


def _validation_for_requirements(
    *, rule, reason, joining_date, schedule_date, override, actor
):
    errors = {}
    if rule.requires_reason and not reason:
        errors["reason"] = "This transition requires a reason."

    missing_optional_requirements = {}
    if rule.requires_joining_date and not joining_date:
        missing_optional_requirements["joining_date"] = (
            "This transition requires a joining date."
        )
    if rule.requires_schedule_date and not schedule_date:
        missing_optional_requirements["schedule_date"] = (
            "This transition requires a schedule date."
        )

    if override:
        if not rule.allow_override:
            errors["override"] = "This transition rule does not allow overrides."
        elif not actor.has_perm("hydra_people.override_recruitment_transition"):
            errors["override"] = "You do not have permission to override requirements."
        if not reason:
            errors["reason"] = "An override requires a reason."
    else:
        errors.update(missing_optional_requirements)

    if errors:
        raise ValidationError(errors)


@transaction.atomic
def transition_candidate(
    *,
    candidate,
    target_stage,
    actor,
    reason="",
    schedule_date=None,
    joining_date=None,
    override=False,
    source=CandidateStageTransition.Source.HYDRA,
):
    """Apply one configured transition and write immutable evidence atomically."""

    locked_candidate = Candidate._base_manager.select_for_update().get(
        pk=candidate.pk
    )
    _require_transition_scope(actor=actor, candidate=locked_candidate)

    if not locked_candidate.is_active or locked_candidate.recruitment_id is None:
        raise ValidationError({"target_stage": "Choose an active application."})
    if locked_candidate.recruitment_id.closed or not locked_candidate.recruitment_id.is_active:
        raise ValidationError(
            {"target_stage": "A closed or inactive recruitment cannot be changed."}
        )
    if not locked_candidate.stage_id_id:
        raise ValidationError({"target_stage": "The application has no current stage."})

    locked_target = (
        Stage._base_manager.select_for_update()
        .filter(
            pk=target_stage.pk,
            recruitment_id_id=locked_candidate.recruitment_id_id,
            is_active=True,
        )
        .first()
    )
    if locked_target is None:
        raise ValidationError(
            {"target_stage": "Choose an active stage from this recruitment."}
        )
    if locked_target.pk == locked_candidate.stage_id_id:
        raise ValidationError({"target_stage": "Choose a different stage."})

    rule = (
        RecruitmentStageTransitionRule.objects.select_for_update()
        .filter(
            recruitment_id=locked_candidate.recruitment_id_id,
            from_stage_id=locked_candidate.stage_id_id,
            to_stage=locked_target,
            is_active=True,
        )
        .first()
    )
    if rule is None:
        raise ValidationError(
            {"target_stage": "This recruitment transition is not enabled."}
        )

    normalized_reason = " ".join(reason.split())
    effective_schedule_date = schedule_date or locked_candidate.schedule_date
    effective_joining_date = joining_date or locked_candidate.joining_date
    _validation_for_requirements(
        rule=rule,
        reason=normalized_reason,
        joining_date=effective_joining_date,
        schedule_date=effective_schedule_date,
        override=bool(override),
        actor=actor,
    )

    from_stage = locked_candidate.stage_id
    locked_candidate.stage_id = locked_target
    locked_candidate.hired = locked_target.stage_type == "hired"
    locked_candidate.canceled = locked_target.stage_type == "cancelled"
    locked_candidate.start_onboard = False
    locked_candidate.schedule_date = effective_schedule_date
    locked_candidate.joining_date = effective_joining_date
    locked_candidate.modified_by = actor
    locked_candidate._hydra_stage_transition_authorized = True
    try:
        locked_candidate.save(
            update_fields=(
                "stage_id",
                "hired",
                "canceled",
                "start_onboard",
                "schedule_date",
                "joining_date",
                "modified_by",
            )
        )
    finally:
        del locked_candidate._hydra_stage_transition_authorized

    event = CandidateStageTransition(
        candidate=locked_candidate,
        from_stage=from_stage,
        to_stage=locked_target,
        rule=rule,
        actor=actor,
        source=source,
        reason=normalized_reason,
        override=bool(override),
        requirements_snapshot={
            "rule_id": rule.pk,
            "requires_reason": rule.requires_reason,
            "requires_schedule_date": rule.requires_schedule_date,
            "requires_joining_date": rule.requires_joining_date,
            "allow_override": rule.allow_override,
            "override_used": bool(override),
            "schedule_date_present": bool(effective_schedule_date),
            "joining_date_present": bool(effective_joining_date),
        },
    )
    event.full_clean()
    event.save()
    return locked_candidate, event
