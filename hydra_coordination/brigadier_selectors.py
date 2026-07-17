from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from attendance.models import Attendance
from base.models import EmployeeShiftSchedule
from hydra_coordination.models import PersonAssignment, ScopeGrant, Team
from leave.models import LeaveRequest


BRIGADIER_PERMISSIONS = (
    "hydra_coordination.view_brigadier_panel",
    "hydra_people.view_person",
    "employee.view_employee",
    "attendance.view_attendance",
    "leave.view_leaverequest",
)


@dataclass(frozen=True)
class BrigadierRosterRow:
    assignment: PersonAssignment
    attendance: Attendance | None
    schedule: EmployeeShiftSchedule | None
    approved_leave: LeaveRequest | None
    scheduled: bool
    expected_to_work: bool
    approved_leave_full_day: bool
    approved_leave_partial_day: bool
    schedule_missing: bool
    leave_conflict: bool
    attendance_on_approved_leave: bool
    attendance_on_unscheduled_day: bool
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
                self.schedule_missing,
                self.leave_conflict,
                self.attendance_on_approved_leave,
                self.attendance_on_unscheduled_day,
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


def _leave_portions(leave, day):
    end_date = leave.end_date or leave.start_date
    if not leave.start_date <= day <= end_date:
        return False, False
    if leave.start_date < day < end_date:
        return True, True

    breakdowns = set()
    if day == leave.start_date:
        breakdowns.add(leave.start_date_breakdown)
    if day == end_date:
        breakdowns.add(leave.end_date_breakdown)
    if "full_day" in breakdowns:
        return True, True
    return "first_half" in breakdowns, "second_half" in breakdowns


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
    weekday = day.strftime("%A").lower()
    shift_ids = {
        assignment.person.employee.employee_work_info.shift_id_id
        for assignment in assignments
        if assignment.person.employee.employee_work_info.shift_id_id
    }
    schedules = EmployeeShiftSchedule._base_manager.filter(
        shift_id_id__in=shift_ids,
        day__day=weekday,
        is_active=True,
    ).select_related("shift_id", "day")
    schedule_by_shift = {schedule.shift_id_id: schedule for schedule in schedules}
    approved_leaves = (
        LeaveRequest._base_manager.filter(
            employee_id_id__in=employee_ids,
            status="approved",
            start_date__lte=day,
        )
        .filter(
            Q(end_date__gte=day)
            | Q(end_date__isnull=True, start_date=day)
        )
        .select_related("leave_type_id")
        .order_by("employee_id_id", "start_date", "pk")
    )
    leaves_by_employee = {}
    for leave in approved_leaves:
        leaves_by_employee.setdefault(leave.employee_id_id, []).append(leave)

    rows = []
    for assignment in assignments:
        employee = assignment.person.employee
        attendance = attendance_by_employee.get(employee.pk)
        work_info = employee.employee_work_info
        shift_id = work_info.shift_id_id
        schedule = schedule_by_shift.get(shift_id)
        employee_leaves = leaves_by_employee.get(employee.pk, [])
        approved_leave = employee_leaves[0] if employee_leaves else None
        first_half_leave = second_half_leave = False
        for leave in employee_leaves:
            covers_first, covers_second = _leave_portions(leave, day)
            first_half_leave = first_half_leave or covers_first
            second_half_leave = second_half_leave or covers_second
        full_day_leave = first_half_leave and second_half_leave
        partial_day_leave = bool(employee_leaves) and not full_day_leave
        scheduled = schedule is not None
        schedule_missing = shift_id is None
        expected_to_work = scheduled and not full_day_leave
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
                schedule=schedule,
                approved_leave=approved_leave,
                scheduled=scheduled,
                expected_to_work=expected_to_work,
                approved_leave_full_day=full_day_leave,
                approved_leave_partial_day=partial_day_leave,
                schedule_missing=schedule_missing,
                leave_conflict=len(employee_leaves) > 1,
                attendance_on_approved_leave=(
                    attendance is not None and full_day_leave
                ),
                attendance_on_unscheduled_day=(
                    attendance is not None and not scheduled and not full_day_leave
                ),
                no_attendance=expected_to_work and attendance is None,
                missing_clock_in=attendance is not None and clock_in is None,
                at_work=attendance is not None and clock_in is not None and clock_out is None,
                completed=attendance is not None and clock_out is not None,
                pending_validation=(
                    attendance is not None
                    and clock_out is not None
                    and not attendance.attendance_validated
                ),
                late_come=(
                    "late_come" in report_types and not first_half_leave
                ),
                early_out=(
                    "early_out" in report_types and not second_half_leave
                ),
            )
        )
    return rows
