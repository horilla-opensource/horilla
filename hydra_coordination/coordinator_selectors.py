from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.models import Location, PersonAssignment
from hydra_coordination.selectors import active_grants_for_user
from hydra_legalization.models import LegalizationCase


COORDINATOR_PERMISSIONS = (
    "hydra_coordination.view_coordinator_panel",
    "hydra_coordination.view_location",
    "hydra_people.view_person",
    "hydra_arrivals.view_arrivalplan",
    "hydra_legalization.view_legalizationcase",
)
PANEL_ROW_LIMIT = 25


@dataclass(frozen=True)
class CoordinatorArrivalRow:
    plan: ArrivalPlan
    overdue: bool
    no_show: bool

    @property
    def person(self):
        return self.plan.person


@dataclass(frozen=True)
class CoordinatorLegalizationRow:
    case: LegalizationCase
    missing_deadline: bool
    overdue_deadline: bool
    due_soon: bool
    missing_validity: bool
    expired_validity: bool
    expiring_validity: bool

    @property
    def person(self):
        return self.case.person


@dataclass(frozen=True)
class CoordinatorPanelSnapshot:
    arrivals_today: int
    arrival_exception_count: int
    assignment_gap_count: int
    legalization_exception_count: int
    arrival_exceptions: list[CoordinatorArrivalRow]
    assignment_gaps: list[ArrivalPlan]
    legalization_exceptions: list[CoordinatorLegalizationRow]


def coordinator_locations_for_user(*, user) -> QuerySet[Location]:
    if not user.is_authenticated or not user.has_perms(COORDINATOR_PERMISSIONS):
        return Location._base_manager.none()
    queryset = Location._base_manager.filter(is_active=True).select_related("company")
    if user.is_superuser:
        return queryset.order_by("company__company", "name")
    location_ids = active_grants_for_user(user=user).filter(
        location__isnull=False
    ).values_list("location_id", flat=True)
    return queryset.filter(pk__in=location_ids).order_by("company__company", "name")


def _cutoff_for_day(day):
    if day == timezone.localdate():
        return timezone.now()
    return timezone.make_aware(
        datetime.combine(day, time.max),
        timezone.get_current_timezone(),
    )


def coordinator_snapshot_for_location(*, user, location, day):
    if not coordinator_locations_for_user(user=user).filter(pk=location.pk).exists():
        raise PermissionDenied

    cutoff = _cutoff_for_day(day)
    arrival_queryset = ArrivalPlan._base_manager.filter(
        destination_location=location,
        person__is_active=True,
    ).select_related("person", "coordinator", "destination_location")
    arrivals_today = arrival_queryset.filter(planned_at__date=day).count()

    arrival_exception_queryset = arrival_queryset.filter(
        Q(status=ArrivalPlan.Status.PLANNED, planned_at__lt=cutoff)
        | Q(status=ArrivalPlan.Status.NO_SHOW, planned_at__date=day)
    ).order_by("planned_at", "person__passport_name", "pk")
    arrival_exception_count = arrival_exception_queryset.count()
    arrival_exceptions = [
        CoordinatorArrivalRow(
            plan=plan,
            overdue=(
                plan.status == ArrivalPlan.Status.PLANNED
                and plan.planned_at < cutoff
            ),
            no_show=plan.status == ArrivalPlan.Status.NO_SHOW,
        )
        for plan in arrival_exception_queryset[:PANEL_ROW_LIMIT]
    ]

    assigned_person_ids = PersonAssignment._base_manager.filter(
        is_active=True,
        is_primary=True,
        valid_from__lte=day,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=day)
    ).values_list("person_id", flat=True)
    assignment_gap_queryset = (
        arrival_queryset.filter(
            status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at__date__lte=day,
        )
        .exclude(person_id__in=assigned_person_ids)
        .order_by("-actual_arrived_at", "person__passport_name", "pk")
    )
    assignment_gap_count = assignment_gap_queryset.count()
    assignment_gaps = list(assignment_gap_queryset[:PANEL_ROW_LIMIT])

    location_person_ids = PersonAssignment._base_manager.filter(
        is_active=True,
        is_primary=True,
        valid_from__lte=day,
        team__section__location=location,
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=day)
    ).values_list("person_id", flat=True)
    attention_until = day + timedelta(days=30)
    workflow_statuses = (
        LegalizationCase.Status.DRAFT,
        LegalizationCase.Status.COLLECTING_DOCUMENTS,
        LegalizationCase.Status.SUBMITTED,
        LegalizationCase.Status.ADDITIONAL_INFORMATION,
    )
    legalization_exception_queryset = (
        LegalizationCase._base_manager.filter(
            person_id__in=location_person_ids,
            person__is_active=True,
        )
        .filter(
            Q(
                status__in=workflow_statuses,
                deadline__isnull=True,
            )
            | Q(
                status__in=workflow_statuses,
                deadline__lte=attention_until,
            )
            | Q(
                status=LegalizationCase.Status.APPROVED,
                valid_until__isnull=True,
            )
            | Q(
                status=LegalizationCase.Status.APPROVED,
                valid_until__lte=attention_until,
            )
            | Q(status=LegalizationCase.Status.EXPIRED)
        )
        .select_related("person", "responsible")
        .distinct()
        .order_by("deadline", "valid_until", "person__passport_name", "pk")
    )
    legalization_exception_count = legalization_exception_queryset.count()
    legalization_exceptions = []
    for case in legalization_exception_queryset[:PANEL_ROW_LIMIT]:
        missing_deadline = case.status in workflow_statuses and case.deadline is None
        overdue_deadline = bool(
            case.status in workflow_statuses
            and case.deadline
            and case.deadline < day
        )
        due_soon = bool(
            case.status in workflow_statuses
            and case.deadline
            and day <= case.deadline <= attention_until
        )
        missing_validity = (
            case.status == LegalizationCase.Status.APPROVED
            and case.valid_until is None
        )
        expired_validity = (
            case.status == LegalizationCase.Status.EXPIRED
            or bool(case.valid_until and case.valid_until < day)
        )
        expiring_validity = bool(
            case.status == LegalizationCase.Status.APPROVED
            and case.valid_until
            and day <= case.valid_until <= attention_until
        )
        legalization_exceptions.append(
            CoordinatorLegalizationRow(
                case=case,
                missing_deadline=missing_deadline,
                overdue_deadline=overdue_deadline,
                due_soon=due_soon,
                missing_validity=missing_validity,
                expired_validity=expired_validity,
                expiring_validity=expiring_validity,
            )
        )

    return CoordinatorPanelSnapshot(
        arrivals_today=arrivals_today,
        arrival_exception_count=arrival_exception_count,
        assignment_gap_count=assignment_gap_count,
        legalization_exception_count=legalization_exception_count,
        arrival_exceptions=arrival_exceptions,
        assignment_gaps=assignment_gaps,
        legalization_exceptions=legalization_exceptions,
    )
