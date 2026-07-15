from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from attendance.models import Attendance
from hydra_coordination.models import PersonAssignment, ScopeGrant, Team


BRIGADIER_PERMISSIONS = (
    "hydra_coordination.view_brigadier_panel",
    "hydra_people.view_person",
    "employee.view_employee",
    "attendance.view_attendance",
)


@dataclass(frozen=True)
class BrigadierRosterRow:
    assignment: PersonAssignment
    attendance: Attendance | None
    no_attendance: bool
    missing_clock_in: bool
    at_work: bool
    completed: bool
    pending_validation: bool
    late_come: bool
    early_out: bool

    @property
    def person(self):
        return self.assignment.person

    @property
    def employee(self):
        return self.assignment.person.employee

    @property
    def has_exception(self):
        return any(
            (
                self.no_attendance,
                self.missing_clock_in,
                self.pending_validation,
                self.late_come,
                self.early_out,
            )
        )


def brigadier_teams_for_user(*, user):
    """Return only directly granted Teams; containing grants never widen this panel."""

    if not user.is_authenticated or not user.has_perms(BRIGADIER_PERMISSIONS):
        return Team.objects.none()
    queryset = Team.objects.filter(
        is_active=True,
        section__is_active=True,
        section__location__is_active=True,
    ).select_related("section__location__company", "section__department")
    if user.is_superuser:
        return queryset

    today = timezone.localdate()
    direct_team_ids = (
        ScopeGrant.objects.filter(
            user=user,
            team__isnull=False,
            is_active=True,
            valid_from__lte=today,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        .values_list("team_id", flat=True)
    )
    return queryset.filter(pk__in=direct_team_ids).distinct()


def brigadier_roster_for_team(*, user, team, day, query=""):
    if not brigadier_teams_for_user(user=user).filter(pk=team.pk).exists():
        raise PermissionDenied

    assignments = (
        PersonAssignment.objects.filter(
            team=team,
            is_primary=True,
            is_active=True,
            valid_from__lte=day,
            person__is_active=True,
            person__employee__isnull=False,
            person__employee__is_active=True,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=day))
        .filter(
            Q(person__employee__employee_work_info__date_joining__isnull=True)
            | Q(person__employee__employee_work_info__date_joining__lte=day)
        )
        .filter(
            Q(person__employee__employee_work_info__contract_end_date__isnull=True)
            | Q(person__employee__employee_work_info__contract_end_date__gte=day)
        )
        .select_related(
            "person__employee__employee_work_info",
            "team__section__location__company",
            "department",
        )
        .order_by("person__last_name", "person__first_name", "person__pk")
    )
    query = query.strip()
    if query:
        assignments = assignments.filter(
            Q(person__passport_name__icontains=query)
            | Q(person__first_name__icontains=query)
            | Q(person__last_name__icontains=query)
            | Q(person__hydra_id__icontains=query)
        )

    assignments = list(assignments)
    employee_ids = [assignment.person.employee_id for assignment in assignments]
    attendances = (
        Attendance._base_manager.filter(
            employee_id_id__in=employee_ids,
            attendance_date=day,
        )
        .prefetch_related("late_come_early_out")
        .order_by("employee_id_id", "pk")
    )
    attendance_by_employee = {
        attendance.employee_id_id: attendance for attendance in attendances
    }

    rows = []
    for assignment in assignments:
        attendance = attendance_by_employee.get(assignment.person.employee_id)
        report_types = (
            {report.type for report in attendance.late_come_early_out.all()}
            if attendance is not None
            else set()
        )
        clock_in = attendance.attendance_clock_in if attendance is not None else None
        clock_out = attendance.attendance_clock_out if attendance is not None else None
        rows.append(
            BrigadierRosterRow(
                assignment=assignment,
                attendance=attendance,
                no_attendance=attendance is None,
                missing_clock_in=attendance is not None and clock_in is None,
                at_work=attendance is not None and clock_in is not None and clock_out is None,
                completed=attendance is not None and clock_out is not None,
                pending_validation=(
                    attendance is not None
                    and clock_out is not None
                    and not attendance.attendance_validated
                ),
                late_come="late_come" in report_types,
                early_out="early_out" in report_types,
            )
        )
    return rows
