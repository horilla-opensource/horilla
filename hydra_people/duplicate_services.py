"""Scoped duplicate suggestions and controlled canonical Person merges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_people.identity import (
    MATCH_REASON_LABELS,
    duplicate_match_reasons,
    duplicate_match_score,
)
from hydra_people.models import (
    EmployeeConversion,
    Person,
    PersonApplication,
    PersonDuplicateSuggestion,
    PersonMergeEvent,
    PersonMergeReference,
)


REVIEW_PERMISSIONS = (
    "hydra_people.view_person",
    "hydra_people.review_person_duplicates",
)
MERGE_PERMISSIONS = REVIEW_PERMISSIONS + (
    "hydra_people.change_person",
    "hydra_people.link_candidate",
    "hydra_people.merge_person",
)
DISMISS_PERMISSIONS = REVIEW_PERMISSIONS + (
    "hydra_people.dismiss_person_duplicate",
)

MERGE_FIELDS = (
    "passport_name",
    "first_name",
    "last_name",
    "date_of_birth",
    "gender",
    "citizenship",
    "preferred_language",
    "phone",
    "whatsapp_viber",
    "email",
    "lifecycle_state",
    "is_active",
)

REFERENCE_LABELS = {
    "applications": _("Recruitment applications"),
    "arrival_plans": _("Arrival plans"),
    "onboarding_handoffs": _("Onboarding handoffs"),
    "coordination_assignments": _("Organization assignments"),
    "housing_assignments": _("Housing assignments"),
    "legalization_cases": _("Legalization cases"),
    "private_documents": _("Private documents"),
    "quarantined_uploads": _("Quarantined uploads"),
}


@dataclass(frozen=True, slots=True)
class MergeConflict:
    code: str
    message: object


def _require_permissions(actor, permissions) -> None:
    if not actor.is_authenticated or not actor.has_perms(permissions):
        raise PermissionDenied


def _pair_ids(person_a, person_b) -> tuple[int, int]:
    return tuple(sorted((person_a.pk, person_b.pk)))


def _candidate_match_query(person) -> Q:
    query = Q()
    for field_name in (
        "identity_fingerprint",
        "passport_dob_fingerprint",
        "email_fingerprint",
    ):
        value = getattr(person, field_name)
        if value:
            query |= Q(**{field_name: value})
    phone_values = {
        value
        for value in (person.phone_fingerprint, person.messenger_fingerprint)
        if value
    }
    if phone_values:
        query |= Q(phone_fingerprint__in=phone_values)
        query |= Q(messenger_fingerprint__in=phone_values)
    return query


@transaction.atomic
def refresh_duplicate_suggestions_for_person(*, person_id, actor=None):
    """Refresh every deterministic pair involving one Person.

    Dismissed decisions are retained. A stale pair reopens only when its source
    data starts matching again. No suggestion ever performs a merge.
    """

    person = Person.objects.select_for_update().filter(pk=person_id).first()
    if person is None:
        return ()
    now = timezone.now()
    involved = PersonDuplicateSuggestion.objects.select_for_update().filter(
        Q(person_low=person) | Q(person_high=person)
    )
    if person.merged_into_id:
        stale_update = {
            "state": PersonDuplicateSuggestion.State.STALE,
            "last_evaluated_at": now,
            "resolved_at": now,
            "resolved_by": None,
            "resolution_reason": "canonical_merge",
        }
        if actor is not None:
            stale_update["modified_by"] = actor
        involved.filter(state=PersonDuplicateSuggestion.State.OPEN).update(
            **stale_update
        )
        return ()

    match_query = _candidate_match_query(person)
    matched_pair_ids: set[tuple[int, int]] = set()
    refreshed = []
    if match_query:
        candidates = (
            Person.objects.filter(match_query, merged_into__isnull=True)
            .exclude(pk=person.pk)
            .order_by("pk")
        )
        for candidate in candidates:
            reasons = duplicate_match_reasons(person, candidate)
            score = duplicate_match_score(reasons)
            if not score:
                continue
            low_id, high_id = _pair_ids(person, candidate)
            pair_key = (low_id, high_id)
            matched_pair_ids.add(pair_key)
            suggestion = involved.filter(
                person_low_id=low_id,
                person_high_id=high_id,
            ).first()
            if suggestion is None:
                try:
                    with transaction.atomic():
                        suggestion = PersonDuplicateSuggestion.objects.create(
                            person_low_id=low_id,
                            person_high_id=high_id,
                            score=score,
                            match_reasons=list(reasons),
                            state=PersonDuplicateSuggestion.State.OPEN,
                            last_evaluated_at=now,
                            created_by=actor,
                            modified_by=actor,
                        )
                except IntegrityError:
                    suggestion = PersonDuplicateSuggestion.objects.select_for_update().get(
                        person_low_id=low_id,
                        person_high_id=high_id,
                    )
            fields = {
                "score": score,
                "match_reasons": list(reasons),
                "last_evaluated_at": now,
            }
            if actor is not None:
                fields["modified_by"] = actor
            if suggestion.state == PersonDuplicateSuggestion.State.STALE:
                fields.update(
                    state=PersonDuplicateSuggestion.State.OPEN,
                    resolved_at=None,
                    resolved_by=None,
                    resolution_reason="",
                )
            PersonDuplicateSuggestion.objects.filter(pk=suggestion.pk).update(**fields)
            refreshed.append(suggestion.pk)

    stale_ids = []
    for suggestion in involved.filter(state=PersonDuplicateSuggestion.State.OPEN):
        pair_key = (suggestion.person_low_id, suggestion.person_high_id)
        if pair_key not in matched_pair_ids:
            stale_ids.append(suggestion.pk)
    if stale_ids:
        stale_update = {
            "state": PersonDuplicateSuggestion.State.STALE,
            "last_evaluated_at": now,
            "resolved_at": now,
            "resolved_by": None,
            "resolution_reason": "no_longer_matches",
        }
        if actor is not None:
            stale_update["modified_by"] = actor
        PersonDuplicateSuggestion.objects.filter(pk__in=stale_ids).update(**stale_update)
    return tuple(refreshed)


def _load_references(*, person_ids, lock=False):
    from hydra_arrivals.models import ArrivalPlan, OnboardingHandoff
    from hydra_coordination.models import PersonAssignment
    from hydra_documents.models import PrivateDocument, QuarantinedUpload
    from hydra_housing.models import HousingAssignment
    from hydra_imports.models import CandidateImportRow
    from hydra_legalization.models import LegalizationCase

    def rows(queryset):
        if lock:
            queryset = queryset.select_for_update(of=("self",))
        return list(queryset.order_by("pk"))

    return {
        "applications": rows(
            PersonApplication.objects.filter(person_id__in=person_ids).select_related(
                "candidate__recruitment_id"
            )
        ),
        "arrival_plans": rows(
            ArrivalPlan._base_manager.filter(person_id__in=person_ids).select_related(
                "candidate"
            )
        ),
        "onboarding_handoffs": rows(
            OnboardingHandoff._base_manager.filter(person_id__in=person_ids)
        ),
        "coordination_assignments": rows(
            PersonAssignment._base_manager.filter(person_id__in=person_ids).select_related(
                "team__section__location", "department"
            )
        ),
        "housing_assignments": rows(
            HousingAssignment._base_manager.filter(person_id__in=person_ids).select_related(
                "bed__room__facility__location"
            )
        ),
        "legalization_cases": rows(
            LegalizationCase._base_manager.filter(person_id__in=person_ids)
        ),
        "private_documents": rows(
            PrivateDocument._base_manager.filter(person_id__in=person_ids)
        ),
        "quarantined_uploads": rows(
            QuarantinedUpload._base_manager.filter(person_id__in=person_ids)
        ),
        "import_rows": rows(
            CandidateImportRow._base_manager.filter(created_person_id__in=person_ids)
        ),
        "conversions": rows(
            EmployeeConversion.objects.filter(person_id__in=person_ids).select_related(
                "candidate", "employee"
            )
        ),
        "incoming_aliases": rows(
            Person.objects.filter(merged_into_id__in=person_ids)
        ),
    }


def _display_value(person, field_name):
    display = getattr(person, f"get_{field_name}_display", None)
    value = display() if callable(display) else getattr(person, field_name)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return _("Yes") if value else _("No")
    return value if value not in (None, "") else _("—")


def _comparison_rows(person_a, person_b):
    rows = []
    for field_name in MERGE_FIELDS:
        field = Person._meta.get_field(field_name)
        rows.append(
            {
                "field": field_name,
                "label": field.verbose_name,
                "person_a": _display_value(person_a, field_name),
                "person_b": _display_value(person_b, field_name),
                "equal": getattr(person_a, field_name) == getattr(person_b, field_name),
            }
        )
    return rows


def _ranges_overlap(first, second) -> bool:
    first_end = first.valid_until or date.max
    second_end = second.valid_until or date.max
    return first.valid_from <= second_end and second.valid_from <= first_end


def _merge_conflicts(*, suggestion, survivor, duplicate, references):
    conflicts: list[MergeConflict] = []
    if suggestion.state != PersonDuplicateSuggestion.State.OPEN:
        conflicts.append(MergeConflict("suggestion_closed", _("The suggestion is no longer open.")))
    if survivor.merged_into_id or duplicate.merged_into_id:
        conflicts.append(MergeConflict("already_merged", _("A selected Person is already a merged alias.")))
    if any(row.merged_into_id == duplicate.pk for row in references["incoming_aliases"]):
        conflicts.append(
            MergeConflict(
                "duplicate_has_aliases",
                _("A canonical Person with existing aliases cannot become a duplicate."),
            )
        )
    reasons = duplicate_match_reasons(survivor, duplicate)
    if not reasons:
        conflicts.append(
            MergeConflict(
                "no_current_match",
                _("The records no longer satisfy a deterministic duplicate rule."),
            )
        )
    if duplicate.employee_id or any(
        row.person_id == duplicate.pk for row in references["conversions"]
    ):
        conflicts.append(
            MergeConflict(
                "duplicate_employee",
                _("The employee-backed Person must be selected as canonical."),
            )
        )

    survivor_recruitments = {
        row.candidate.recruitment_id_id
        for row in references["applications"]
        if row.person_id == survivor.pk and row.candidate.recruitment_id_id
    }
    duplicate_recruitments = {
        row.candidate.recruitment_id_id
        for row in references["applications"]
        if row.person_id == duplicate.pk and row.candidate.recruitment_id_id
    }
    if survivor_recruitments.intersection(duplicate_recruitments):
        conflicts.append(
            MergeConflict(
                "same_recruitment",
                _("Both records have an application in the same recruitment."),
            )
        )

    candidate_employee_ids = {
        row.candidate.converted_employee_id_id
        for row in references["applications"]
        if row.person_id == duplicate.pk and row.candidate.converted_employee_id_id
    }
    if candidate_employee_ids and (
        survivor.employee_id is None or candidate_employee_ids != {survivor.employee_id}
    ):
        conflicts.append(
            MergeConflict(
                "candidate_employee_conflict",
                _("A source application references a different or unlinked Employee."),
            )
        )

    survivor_assignments = [
        row
        for row in references["coordination_assignments"]
        if row.person_id == survivor.pk and row.is_active and row.is_primary
    ]
    duplicate_assignments = [
        row
        for row in references["coordination_assignments"]
        if row.person_id == duplicate.pk and row.is_active and row.is_primary
    ]
    if any(
        _ranges_overlap(left, right)
        for left in survivor_assignments
        for right in duplicate_assignments
    ):
        conflicts.append(
            MergeConflict(
                "organization_overlap",
                _("Active primary organization assignments overlap."),
            )
        )

    survivor_housing = [
        row
        for row in references["housing_assignments"]
        if row.person_id == survivor.pk and row.is_active
    ]
    duplicate_housing = [
        row
        for row in references["housing_assignments"]
        if row.person_id == duplicate.pk and row.is_active
    ]
    if any(
        _ranges_overlap(left, right)
        for left in survivor_housing
        for right in duplicate_housing
    ):
        conflicts.append(
            MergeConflict(
                "housing_overlap",
                _("Active housing periods overlap."),
            )
        )
    return tuple(conflicts)


def _signature_value(value):
    if isinstance(value, (date,)):
        return value.isoformat()
    return str(value) if value is not None else None


def _version_token(*, person_a, person_b, references):
    payload = {
        "people": {
            str(person.pk): {
                field: _signature_value(getattr(person, field))
                for field in (
                    "uuid",
                    "hydra_id",
                    *MERGE_FIELDS,
                    "employee_id",
                    "merged_into_id",
                )
            }
            for person in (person_a, person_b)
        },
        "references": {},
    }
    for kind, rows in references.items():
        signatures = []
        for row in rows:
            values = [row.pk]
            for field_name in (
                "person_id",
                "created_person_id",
                "merged_into_id",
                "valid_from",
                "valid_until",
                "is_active",
                "is_primary",
                "candidate_id",
                "employee_id",
            ):
                if hasattr(row, field_name):
                    values.append(_signature_value(getattr(row, field_name)))
            if kind == "applications":
                values.append(row.candidate.recruitment_id_id)
                values.append(row.candidate.converted_employee_id_id)
            signatures.append(values)
        payload["references"][kind] = signatures
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def build_merge_plan(*, suggestion, survivor_id=None, lock=False):
    """Build the same deterministic preview used again inside the commit lock."""

    person_ids = sorted((suggestion.person_low_id, suggestion.person_high_id))
    queryset = Person.objects
    if lock:
        queryset = queryset.select_for_update()
    people = {person.pk: person for person in queryset.filter(pk__in=person_ids).order_by("pk")}
    if set(people) != set(person_ids):
        raise ValidationError(_("One of the compared Person records no longer exists."))
    person_a = people[suggestion.person_low_id]
    person_b = people[suggestion.person_high_id]
    survivor_id = int(survivor_id or person_a.pk)
    if survivor_id not in people:
        raise ValidationError({"canonical_person": _("Choose one compared Person.")})
    survivor = people[survivor_id]
    duplicate = person_b if survivor.pk == person_a.pk else person_a
    references = _load_references(person_ids=person_ids, lock=lock)
    counts = {
        kind: sum(row.person_id == duplicate.pk for row in rows)
        for kind, rows in references.items()
        if kind in REFERENCE_LABELS
    }
    return {
        "suggestion": suggestion,
        "person_a": person_a,
        "person_b": person_b,
        "survivor": survivor,
        "duplicate": duplicate,
        "comparison_rows": _comparison_rows(person_a, person_b),
        "match_reasons": tuple(duplicate_match_reasons(person_a, person_b)),
        "match_reason_labels": tuple(
            MATCH_REASON_LABELS[reason]
            for reason in duplicate_match_reasons(person_a, person_b)
        ),
        "reference_counts": tuple(
            {
                "kind": kind,
                "label": REFERENCE_LABELS[kind],
                "count": counts[kind],
            }
            for kind in REFERENCE_LABELS
        ),
        "references": references,
        "conflicts": _merge_conflicts(
            suggestion=suggestion,
            survivor=survivor,
            duplicate=duplicate,
            references=references,
        ),
        "version_token": _version_token(
            person_a=person_a,
            person_b=person_b,
            references=references,
        ),
    }


def _assert_people_scope(*, actor, people, permission="view_person"):
    from hydra_people.selectors import people_for_user

    visible = set(
        people_for_user(user=actor, permission=permission)
        .filter(pk__in=[person.pk for person in people])
        .values_list("pk", flat=True)
    )
    if visible != {person.pk for person in people}:
        raise PermissionDenied


def _required_domain_permissions(references, survivor):
    required = set()
    if references["applications"]:
        required.update(("recruitment.view_candidate",))
    if references["arrival_plans"]:
        required.update(
            ("hydra_arrivals.view_arrivalplan", "hydra_arrivals.change_arrivalplan")
        )
    if references["onboarding_handoffs"]:
        required.update(
            (
                "hydra_arrivals.view_onboardinghandoff",
                "hydra_arrivals.reconcile_onboardinghandoff",
            )
        )
    if references["coordination_assignments"]:
        required.update(
            (
                "hydra_coordination.view_personassignment",
                "hydra_coordination.change_personassignment",
                "hydra_coordination.assign_person",
                "hydra_coordination.view_team",
            )
        )
    if references["housing_assignments"]:
        required.update(
            (
                "hydra_housing.view_housingfacility",
                "hydra_housing.view_housingroom",
                "hydra_housing.view_housingbed",
                "hydra_housing.view_housingassignment",
                "hydra_housing.change_housingassignment",
                "hydra_housing.move_housingassignment",
                "hydra_coordination.view_location",
            )
        )
    if references["legalization_cases"]:
        required.update(
            (
                "hydra_legalization.view_legalizationcase",
                "hydra_legalization.change_legalizationcase",
            )
        )
    if references["private_documents"] or references["quarantined_uploads"]:
        required.update(
            (
                "hydra_documents.view_privatedocument",
                "hydra_documents.change_privatedocument",
                "recruitment.view_candidate",
            )
        )
    if references["quarantined_uploads"]:
        required.add("hydra_documents.view_quarantinedupload")
    if survivor.employee_id and references["coordination_assignments"]:
        required.update(
            (
                "employee.view_employee",
                "employee.change_employeeworkinformation",
            )
        )
    return tuple(sorted(required))


def _assert_reference_scope(*, actor, references):
    from hydra_arrivals.selectors import arrival_plans_for_user
    from hydra_coordination.selectors import teams_for_user
    from hydra_housing.selectors import housing_assignments_for_user
    from hydra_legalization.selectors import legalization_cases_for_user
    from hydra_people.recruitment_selectors import linked_candidates_for_user

    candidate_ids = {
        row.candidate_id for row in references["applications"]
    } | {row.candidate_id for row in references["private_documents"]} | {
        row.candidate_id for row in references["quarantined_uploads"]
    }
    if candidate_ids:
        visible = set(
            linked_candidates_for_user(user=actor)
            .filter(pk__in=candidate_ids)
            .values_list("pk", flat=True)
        )
        if visible != candidate_ids:
            raise PermissionDenied
    arrival_ids = {row.pk for row in references["arrival_plans"]}
    if arrival_ids:
        visible = set(
            arrival_plans_for_user(user=actor)
            .filter(pk__in=arrival_ids)
            .values_list("pk", flat=True)
        )
        if visible != arrival_ids:
            raise PermissionDenied
    handoff_arrival_ids = {row.arrival_id for row in references["onboarding_handoffs"]}
    if handoff_arrival_ids:
        visible = set(
            arrival_plans_for_user(user=actor)
            .filter(pk__in=handoff_arrival_ids)
            .values_list("pk", flat=True)
        )
        if visible != handoff_arrival_ids:
            raise PermissionDenied
    team_ids = {row.team_id for row in references["coordination_assignments"]}
    if team_ids:
        visible = set(
            teams_for_user(user=actor)
            .filter(pk__in=team_ids)
            .values_list("pk", flat=True)
        )
        if visible != team_ids:
            raise PermissionDenied
    housing_ids = {row.pk for row in references["housing_assignments"]}
    if housing_ids:
        visible = set(
            housing_assignments_for_user(user=actor)
            .filter(pk__in=housing_ids)
            .values_list("pk", flat=True)
        )
        if visible != housing_ids:
            raise PermissionDenied
    case_ids = {row.pk for row in references["legalization_cases"]}
    if case_ids:
        visible = set(
            legalization_cases_for_user(user=actor)
            .filter(pk__in=case_ids)
            .values_list("pk", flat=True)
        )
        if visible != case_ids:
            raise PermissionDenied


def assert_merge_plan_access(*, actor, plan):
    _require_permissions(actor, MERGE_PERMISSIONS)
    _assert_people_scope(
        actor=actor,
        people=(plan["person_a"], plan["person_b"]),
        permission="change_person",
    )
    _require_permissions(
        actor,
        _required_domain_permissions(plan["references"], plan["survivor"]),
    )
    _assert_reference_scope(actor=actor, references=plan["references"])


@transaction.atomic
def dismiss_duplicate_suggestion(*, suggestion, actor, reason):
    _require_permissions(actor, DISMISS_PERMISSIONS)
    locked = (
        PersonDuplicateSuggestion.objects.select_for_update()
        .select_related("person_low", "person_high")
        .get(pk=suggestion.pk)
    )
    _assert_people_scope(actor=actor, people=(locked.person_low, locked.person_high))
    if locked.state != PersonDuplicateSuggestion.State.OPEN:
        raise ValidationError(_("Only an open suggestion can be dismissed."))
    reason = " ".join(str(reason or "").split())
    if len(reason) < 10:
        raise ValidationError({"reason": _("Provide a reason of at least 10 characters.")})
    locked.state = PersonDuplicateSuggestion.State.DISMISSED
    locked.resolved_at = timezone.now()
    locked.resolved_by = actor
    locked.resolution_reason = reason
    locked.modified_by = actor
    locked.save(
        update_fields=(
            "state",
            "resolved_at",
            "resolved_by",
            "resolution_reason",
            "modified_by",
        )
    )
    return locked


def validate_selected_fields(*, plan, field_sources):
    people = {"person_a": plan["person_a"], "person_b": plan["person_b"]}
    values = {}
    for field_name in MERGE_FIELDS:
        source_key = field_sources.get(field_name)
        if source_key not in people:
            raise ValidationError({field_name: _("Choose the source for every field.")})
        values[field_name] = getattr(people[source_key], field_name)
    if plan["survivor"].employee_id and values["lifecycle_state"] != Person.LifecycleState.EMPLOYEE:
        raise ValidationError(
            {"lifecycle_state": _("An employee-backed canonical Person must remain Employee.")}
        )
    has_applications = bool(plan["references"]["applications"])
    has_onboarding = bool(plan["references"]["onboarding_handoffs"])
    if has_applications and values["lifecycle_state"] == Person.LifecycleState.PROSPECT:
        raise ValidationError(
            {"lifecycle_state": _("A Person with applications cannot remain a Prospect.")}
        )
    if has_onboarding and values["lifecycle_state"] not in (
        Person.LifecycleState.ONBOARDING,
        Person.LifecycleState.EMPLOYEE,
    ):
        raise ValidationError(
            {"lifecycle_state": _("A Person with an onboarding handoff must remain Onboarding or Employee.")}
        )
    return values


def _apply_selected_fields(*, plan, field_sources, actor):
    survivor = plan["survivor"]
    values = validate_selected_fields(plan=plan, field_sources=field_sources)
    decisions = {}
    for field_name, value in values.items():
        setattr(survivor, field_name, value)
        decisions[field_name] = field_sources[field_name]
    survivor.modified_by = actor
    survivor.full_clean()
    survivor.save()
    return decisions


def _move_references(*, plan, actor, event):
    from hydra_arrivals.models import ArrivalPlan, OnboardingHandoff
    from hydra_coordination.models import PersonAssignment
    from hydra_documents.models import PrivateDocument, QuarantinedUpload
    from hydra_housing.models import HousingAssignment
    from hydra_legalization.models import LegalizationCase

    survivor = plan["survivor"]
    duplicate = plan["duplicate"]
    model_map = {
        "applications": PersonApplication,
        "arrival_plans": ArrivalPlan,
        "onboarding_handoffs": OnboardingHandoff,
        "coordination_assignments": PersonAssignment,
        "housing_assignments": HousingAssignment,
        "legalization_cases": LegalizationCase,
        "private_documents": PrivateDocument,
        "quarantined_uploads": QuarantinedUpload,
    }
    reference_events = []
    counts = {}
    for kind, model in model_map.items():
        object_ids = [
            row.pk for row in plan["references"][kind] if row.person_id == duplicate.pk
        ]
        counts[kind] = len(object_ids)
        if not object_ids:
            continue
        update = {"person_id": survivor.pk}
        if any(field.name == "modified_by" for field in model._meta.fields):
            update["modified_by_id"] = actor.pk
        model._base_manager.filter(pk__in=object_ids).update(**update)
        reference_events.extend(
            PersonMergeReference(
                event=event,
                relation_kind=kind,
                object_id=str(object_id),
            )
            for object_id in object_ids
        )
    PersonMergeReference.objects.bulk_create(reference_events)
    return counts


def _synchronize_employee_projection(*, survivor, actor):
    if not survivor.employee_id:
        return
    from hydra_coordination.models import PersonAssignment
    from hydra_coordination.services import _synchronize_employee_work_information

    day = timezone.localdate()
    current = list(
        PersonAssignment._base_manager.filter(
            person=survivor,
            is_active=True,
            is_primary=True,
            valid_from__lte=day,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .select_related("team__section__location__company", "department")
        .order_by("pk")
    )
    if len(current) == 1:
        _synchronize_employee_work_information(
            person=survivor,
            team=current[0].team,
            department=current[0].department,
            actor=actor,
        )


@transaction.atomic
def merge_duplicate_people(
    *, suggestion, survivor_id, field_sources, reason, expected_version_token, actor
):
    """Apply one reviewed merge atomically; never called by duplicate detection."""

    _require_permissions(actor, MERGE_PERMISSIONS)
    locked_suggestion = (
        PersonDuplicateSuggestion.objects.select_for_update()
        .select_related("person_low", "person_high")
        .get(pk=suggestion.pk)
    )
    plan = build_merge_plan(
        suggestion=locked_suggestion,
        survivor_id=survivor_id,
        lock=True,
    )
    assert_merge_plan_access(actor=actor, plan=plan)
    if plan["version_token"] != expected_version_token:
        raise ValidationError(
            _("The compared data changed after preview. Review a fresh preview before merging.")
        )
    if plan["conflicts"]:
        raise ValidationError([conflict.message for conflict in plan["conflicts"]])
    reason = " ".join(str(reason or "").split())
    if len(reason) < 10:
        raise ValidationError({"reason": _("Provide a reason of at least 10 characters.")})

    decisions = _apply_selected_fields(
        plan=plan,
        field_sources=field_sources,
        actor=actor,
    )
    duplicate = plan["duplicate"]
    survivor = plan["survivor"]
    moved_counts = {
        kind: sum(row.person_id == duplicate.pk for row in plan["references"][kind])
        for kind in REFERENCE_LABELS
    }
    event = PersonMergeEvent(
        survivor=survivor,
        duplicate=duplicate,
        actor=actor,
        reason=reason,
        match_reasons=list(plan["match_reasons"]),
        field_decisions=decisions,
        moved_reference_counts=moved_counts,
        preserved_source_identifiers={
            "survivor_hydra_id": survivor.hydra_id,
            "survivor_uuid": str(survivor.uuid),
            "duplicate_hydra_id": duplicate.hydra_id,
            "duplicate_uuid": str(duplicate.uuid),
        },
    )
    event.full_clean()
    event.save(force_insert=True)
    actual_counts = _move_references(plan=plan, actor=actor, event=event)
    if actual_counts != moved_counts:
        raise ValidationError(_("Dependent records changed during the merge."))

    duplicate.merged_into = survivor
    duplicate.merged_at = timezone.now()
    duplicate.merged_by = actor
    duplicate.lifecycle_state = Person.LifecycleState.INACTIVE
    duplicate.is_active = False
    duplicate.modified_by = actor
    duplicate.full_clean()
    duplicate.save(
        merge_transition=True,
        update_fields=(
            "merged_into",
            "merged_at",
            "merged_by",
            "lifecycle_state",
            "is_active",
            "modified_by",
        ),
    )
    locked_suggestion.state = PersonDuplicateSuggestion.State.MERGED
    locked_suggestion.resolved_at = timezone.now()
    locked_suggestion.resolved_by = actor
    locked_suggestion.resolution_reason = reason
    locked_suggestion.merge_event = event
    locked_suggestion.modified_by = actor
    locked_suggestion.save(
        update_fields=(
            "state",
            "resolved_at",
            "resolved_by",
            "resolution_reason",
            "merge_event",
            "modified_by",
        )
    )
    PersonDuplicateSuggestion.objects.filter(
        Q(person_low=duplicate) | Q(person_high=duplicate),
        state=PersonDuplicateSuggestion.State.OPEN,
    ).exclude(pk=locked_suggestion.pk).update(
        state=PersonDuplicateSuggestion.State.STALE,
        resolved_at=timezone.now(),
        resolved_by=actor,
        resolution_reason="canonical_merge",
        modified_by=actor,
    )
    _synchronize_employee_projection(survivor=survivor, actor=actor)
    return event
