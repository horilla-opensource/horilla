from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_arrivals.selectors import arrival_plans_for_user
from hydra_coordination.models import PersonAssignment
from hydra_legalization.models import LegalizationCase
from hydra_legalization.selectors import legalization_cases_for_user
from hydra_housing.models import HousingAssignment
from hydra_housing.selectors import housing_assignments_for_user
from hydra_people.models import Person
from hydra_people.selectors import people_for_user


REPORT_VIEW_PERMISSIONS = (
    "hydra_reports.view_operational_report",
    "hydra_people.view_person",
    "hydra_coordination.view_personassignment",
    "hydra_coordination.view_location",
    "hydra_coordination.view_team",
    "hydra_arrivals.view_arrivalplan",
    "recruitment.view_candidate",
    "hydra_legalization.view_legalizationcase",
    "hydra_housing.view_housingfacility",
    "hydra_housing.view_housingroom",
    "hydra_housing.view_housingbed",
    "hydra_housing.view_housingassignment",
)

WORKFLOW_LEGALIZATION_STATUSES = (
    LegalizationCase.Status.DRAFT,
    LegalizationCase.Status.COLLECTING_DOCUMENTS,
    LegalizationCase.Status.SUBMITTED,
    LegalizationCase.Status.ADDITIONAL_INFORMATION,
)


@dataclass(frozen=True)
class OperationalReportRow:
    person: Person
    assignment: PersonAssignment | None
    arrival: ArrivalPlan | None
    legalization: LegalizationCase | None
    housing: HousingAssignment | None
    attention_flags: tuple[str, ...]


@dataclass(frozen=True)
class OperationalReportSummary:
    total_people: int
    employee_count: int
    arrival_attention_count: int
    legalization_attention_count: int
    housing_attention_count: int


def _current_assignment_query(*, day=None):
    day = day or timezone.localdate()
    return PersonAssignment._base_manager.filter(
        is_active=True,
        valid_from__lte=day,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))


def _arrival_attention_query(*, user):
    return arrival_plans_for_user(user=user).filter(
        Q(status=ArrivalPlan.Status.PLANNED, planned_at__lt=timezone.now())
        | Q(status=ArrivalPlan.Status.NO_SHOW)
    )


def _legalization_attention_query(*, user, day=None):
    day = day or timezone.localdate()
    attention_until = day + timedelta(days=30)
    return legalization_cases_for_user(user=user).filter(
        Q(status__in=WORKFLOW_LEGALIZATION_STATUSES, deadline__isnull=True)
        | Q(
            status__in=WORKFLOW_LEGALIZATION_STATUSES,
            deadline__lte=attention_until,
        )
        | Q(status=LegalizationCase.Status.APPROVED, valid_until__isnull=True)
        | Q(
            status=LegalizationCase.Status.APPROVED,
            valid_until__lte=attention_until,
        )
        | Q(status=LegalizationCase.Status.EXPIRED)
    )


def _current_housing_query(*, user, day=None):
    day = day or timezone.localdate()
    return housing_assignments_for_user(user=user, day=day, current_only=True)


def _housing_attention_people(*, user, day=None):
    day = day or timezone.localdate()
    confirmed_arrival_person_ids = arrival_plans_for_user(user=user).filter(
        status=ArrivalPlan.Status.CONFIRMED,
        actual_arrived_at__date__lte=day,
    ).values("person_id")
    housed_person_ids = _current_housing_query(user=user, day=day).values("person_id")
    return people_for_user(user=user).filter(
        pk__in=confirmed_arrival_person_ids
    ).exclude(pk__in=housed_person_ids)


def operational_people_for_user(*, user, filters=None) -> QuerySet[Person]:
    if not user.is_authenticated or not user.has_perms(REPORT_VIEW_PERMISSIONS):
        return Person.objects.none()

    filters = filters or {}
    day = timezone.localdate()
    queryset = people_for_user(user=user)
    query = (filters.get("q") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(hydra_id__icontains=query)
            | Q(passport_name__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )

    lifecycle = filters.get("lifecycle")
    if lifecycle in Person.LifecycleState.values:
        queryset = queryset.filter(lifecycle_state=lifecycle)

    current_assignment_q = Q(
        coordination_assignments__is_active=True,
        coordination_assignments__valid_from__lte=day,
    ) & (
        Q(coordination_assignments__valid_until__isnull=True)
        | Q(coordination_assignments__valid_until__gte=day)
    )
    location = filters.get("location")
    if location:
        queryset = queryset.filter(
            current_assignment_q,
            coordination_assignments__team__section__location=location,
        )
    team = filters.get("team")
    if team:
        queryset = queryset.filter(
            current_assignment_q,
            coordination_assignments__team=team,
        )

    arrival_status = filters.get("arrival_status")
    if arrival_status in ArrivalPlan.Status.values:
        arrival_ids = arrival_plans_for_user(
            user=user,
            status=arrival_status,
        ).values("person_id")
        queryset = queryset.filter(pk__in=arrival_ids)

    legalization_status = filters.get("legalization_status")
    if legalization_status in LegalizationCase.Status.values:
        case_ids = legalization_cases_for_user(
            user=user,
            status=legalization_status,
        ).values("person_id")
        queryset = queryset.filter(pk__in=case_ids)

    attention = filters.get("attention")
    if attention in {"any", "arrival", "legalization", "housing", "unassigned"}:
        current_assignments = _current_assignment_query(day=day).filter(
            person_id=OuterRef("pk")
        )
        queryset = queryset.annotate(
            report_has_current_assignment=Exists(current_assignments)
        )
        arrival_person_ids = _arrival_attention_query(user=user).values("person_id")
        legalization_person_ids = _legalization_attention_query(
            user=user,
            day=day,
        ).values("person_id")
        housing_person_ids = _housing_attention_people(
            user=user,
            day=day,
        ).values("pk")
        if attention == "arrival":
            queryset = queryset.filter(pk__in=arrival_person_ids)
        elif attention == "legalization":
            queryset = queryset.filter(pk__in=legalization_person_ids)
        elif attention == "unassigned":
            queryset = queryset.filter(report_has_current_assignment=False)
        elif attention == "housing":
            queryset = queryset.filter(pk__in=housing_person_ids)
        else:
            queryset = queryset.filter(
                Q(pk__in=arrival_person_ids)
                | Q(pk__in=legalization_person_ids)
                | Q(pk__in=housing_person_ids)
                | Q(report_has_current_assignment=False)
            )

    return queryset.distinct().order_by("passport_name", "hydra_id")


def operational_report_summary(*, user, people):
    return OperationalReportSummary(
        total_people=people.count(),
        employee_count=people.filter(
            lifecycle_state=Person.LifecycleState.EMPLOYEE
        ).count(),
        arrival_attention_count=people.filter(
            pk__in=_arrival_attention_query(user=user).values("person_id")
        )
        .distinct()
        .count(),
        legalization_attention_count=people.filter(
            pk__in=_legalization_attention_query(user=user).values("person_id")
        )
        .distinct()
        .count(),
        housing_attention_count=people.filter(
            pk__in=_housing_attention_people(user=user).values("pk")
        ).distinct().count(),
    )


def _attention_flags(*, assignment, arrival, legalization, housing, day=None):
    day = day or timezone.localdate()
    attention_until = day + timedelta(days=30)
    flags = []
    if assignment is None:
        flags.append("unassigned")
    if arrival:
        if (
            arrival.status == ArrivalPlan.Status.PLANNED
            and arrival.planned_at < timezone.now()
        ):
            flags.append("arrival_overdue")
        elif arrival.status == ArrivalPlan.Status.NO_SHOW:
            flags.append("arrival_no_show")
    if legalization:
        if (
            legalization.status in WORKFLOW_LEGALIZATION_STATUSES
            and (
                legalization.deadline is None
                or legalization.deadline <= attention_until
            )
        ):
            flags.append("legalization_deadline")
        if (
            legalization.status == LegalizationCase.Status.EXPIRED
            or (
                legalization.status == LegalizationCase.Status.APPROVED
                and (
                    legalization.valid_until is None
                    or legalization.valid_until <= attention_until
                )
            )
        ):
            flags.append("legalization_validity")
    if (
        arrival
        and arrival.status == ArrivalPlan.Status.CONFIRMED
        and housing is None
    ):
        flags.append("housing_missing")
    return tuple(flags)


def operational_report_rows(*, user, people, filters=None):
    people = list(people)
    filters = filters or {}
    person_ids = [person.pk for person in people]
    if not person_ids:
        return []

    visible_ids = people_for_user(user=user).filter(pk__in=person_ids).values("pk")
    assignments = (
        _current_assignment_query()
        .filter(person_id__in=visible_ids)
        .select_related("department", "team__section__location__company")
        .order_by("person_id", "-is_primary", "-valid_from", "-pk")
    )
    arrivals = arrival_plans_for_user(user=user).filter(person_id__in=person_ids)
    arrival_status = filters.get("arrival_status")
    if arrival_status in ArrivalPlan.Status.values:
        arrivals = arrivals.filter(status=arrival_status)
    if filters.get("attention") in {"arrival", "any"}:
        arrivals = arrivals.filter(
            pk__in=_arrival_attention_query(user=user).values("pk")
        )
    arrivals = arrivals.order_by("person_id", "-planned_at", "-pk")

    cases = legalization_cases_for_user(user=user).filter(person_id__in=person_ids)
    legalization_status = filters.get("legalization_status")
    if legalization_status in LegalizationCase.Status.values:
        cases = cases.filter(status=legalization_status)
    if filters.get("attention") in {"legalization", "any"}:
        cases = cases.filter(
            pk__in=_legalization_attention_query(user=user).values("pk")
        )
    cases = cases.order_by("person_id", "-created_at", "-pk")

    housing_assignments = _current_housing_query(user=user).filter(
        person_id__in=person_ids
    ).order_by("person_id", "-valid_from", "-pk")

    assignment_by_person = {}
    arrival_by_person = {}
    case_by_person = {}
    housing_by_person = {}
    for assignment in assignments:
        assignment_by_person.setdefault(assignment.person_id, assignment)
    for arrival in arrivals:
        arrival_by_person.setdefault(arrival.person_id, arrival)
    for case in cases:
        case_by_person.setdefault(case.person_id, case)
    for housing in housing_assignments:
        housing_by_person.setdefault(housing.person_id, housing)

    rows = []
    for person in people:
        assignment = assignment_by_person.get(person.pk)
        arrival = arrival_by_person.get(person.pk)
        legalization = case_by_person.get(person.pk)
        housing = housing_by_person.get(person.pk)
        rows.append(
            OperationalReportRow(
                person=person,
                assignment=assignment,
                arrival=arrival,
                legalization=legalization,
                housing=housing,
                attention_flags=_attention_flags(
                    assignment=assignment,
                    arrival=arrival,
                    legalization=legalization,
                    housing=housing,
                ),
            )
        )
    return rows
