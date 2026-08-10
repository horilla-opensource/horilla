"""
Management command: create_summary_fixtures
-------------------------------------------
Generates test data for the Attendance Monthly Summary feature.

Grace time = 30 min (default). Min hour = 08:00 for all records.
  effective_min = 28800 - 1800 = 27000 s = 7h30m
  half_boundary = 28800 / 2   = 14400 s = 4h00m

Classification thresholds:
  FULL PRESENT   worked >= 7h30m  (>= effective_min)
  HALF DAY       worked >= 4h00m  (>= min/2, < effective_min)
  SHORT HOURS    worked <  4h00m  AND has clock-out
  MISSING OUT    worked <  4h00m  AND no clock-out

Employees:
  FX01 Alice Fixture  — regular employee, full days + 1 half day
  FX02 Bob Fixture    — all four attendance types in one month
  FX03 Carol Fixture  — leave scenarios (approved + pending + unpaid)
  FX04 David Fixture  — grace-time boundary edge cases
  FX05 Eve Fixture    — overlap: attendance records that collide with leave days

Run:
    python manage.py create_summary_fixtures
    python manage.py create_summary_fixtures --month 2026-06
    python manage.py create_summary_fixtures --flush   # delete fixtures first
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

FIXTURE_EMAIL_DOMAIN = "fixture.summary.test"

# (day_of_month, clock_in, clock_out, worked_hhmm, min_hhmm)
# clock_out=None -> missing out (no punch-out recorded)
SCENARIOS = {
    # ── Alice: mostly full days, one clear half day ─────────────────────────
    "alice": [
        (1, "09:00", "17:30", "08:30", "08:00"),  # FULL  — 8h30m > 7h30m
        (2, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (3, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (4, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (5, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (8, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (9, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (10, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (11, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (12, "09:00", "14:30", "05:30", "08:00"),  # HALF  — 5h30m in [4h, 7h30m)
        (15, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (16, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (17, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (18, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (19, "09:00", "17:30", "08:30", "08:00"),  # FULL
    ],
    # ── Bob: all four types spread across the month ──────────────────────────
    "bob": [
        (1, "09:00", "17:30", "08:30", "08:00"),  # FULL  — 8h30m
        (2, "09:00", "15:00", "06:00", "08:00"),  # HALF  — 6h (clearly in half zone)
        (3, "09:00", "13:30", "04:30", "08:00"),  # HALF  — 4h30m (above min/2)
        (4, "09:00", "11:30", "02:30", "08:00"),  # SHORT — 2h30m, has clock-out
        (5, "09:00", None, "01:30", "08:00"),  # MO    — 1h30m, no clock-out
        (8, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (9, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (10, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (11, "09:00", "14:00", "05:00", "08:00"),  # HALF  — 5h
        (12, "10:00", "12:30", "02:30", "08:00"),  # SHORT — 2h30m, has clock-out
        (15, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (16, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (17, "09:00", None, "00:45", "08:00"),  # MO    — 45 min, no clock-out
        (18, "09:00", "17:30", "08:30", "08:00"),  # FULL
    ],
    # ── Carol: attendance present on non-leave days; leave handled separately ─
    "carol": [
        (1, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (2, "09:00", "17:30", "08:30", "08:00"),  # FULL
        # Days 3-11: leave (see LEAVES below)
        (12, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (15, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (16, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (17, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (18, "09:00", "17:30", "08:30", "08:00"),  # FULL
    ],
    # ── David: grace-time boundary cases ────────────────────────────────────
    # effective_min = 27000 s = 7h30m  |  half_boundary = 14400 s = 4h00m
    "david": [
        (
            1,
            "09:00",
            "16:30",
            "07:30",
            "08:00",
        ),  # FULL  — exactly effective_min (27000 >= 27000)
        (
            2,
            "09:00",
            "16:29",
            "07:29",
            "08:00",
        ),  # HALF  — 1 min below grace (26940 < 27000, >= 14400)
        (
            3,
            "09:00",
            "13:00",
            "04:00",
            "08:00",
        ),  # HALF  — exactly min/2 (14400 >= 14400)
        (
            4,
            "09:00",
            "12:59",
            "03:59",
            "08:00",
        ),  # SHORT — 1 min below half (14340 < 14400), has clock-out
        (5, "09:30", None, "00:30", "08:00"),  # MO    — 30 min, no clock-out
        (8, "09:00", "17:30", "08:30", "08:00"),  # FULL  — standard full day
        (9, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (
            10,
            "09:00",
            "17:00",
            "08:00",
            "08:00",
        ),  # FULL  — exactly min (28800 >= 27000)
    ],
    # ── Eve: overlap — attendance collides with leave on the same day ────────
    # Tests how the summary handles days that have BOTH an attendance record
    # AND a leave request.
    #
    # Leave setup for Eve (see LEAVES["eve"]):
    #   Days  3-7 : approved paid leave
    #   Days  8-9 : pending (requested) paid leave
    #   Days 10-11: approved unpaid leave
    #
    # Attendance overlapping those leave days:
    #   Day  4 : full attendance DURING approved paid leave    → overlap: present + paid_leave
    #   Day  8 : half attendance DURING pending paid leave     → overlap: present + paid_leave(pending)
    #   Day 10 : short-hours attendance DURING unpaid leave    → overlap: present + unpaid_leave
    #   Day  6 : missing-out DURING approved paid leave        → overlap: MO + paid_leave
    "eve": [
        (1, "09:00", "17:30", "08:30", "08:00"),  # FULL  — clean, no leave
        (2, "09:00", "17:30", "08:30", "08:00"),  # FULL  — clean, no leave
        # Overlapping days (leave also set below)
        (
            4,
            "09:00",
            "17:30",
            "08:30",
            "08:00",
        ),  # FULL  + approved paid leave  (days 3-7)
        (6, "09:00", None, "01:00", "08:00"),  # MO    + approved paid leave  (days 3-7)
        (
            8,
            "09:00",
            "14:00",
            "05:00",
            "08:00",
        ),  # HALF  + pending paid leave   (days 8-9)
        (
            10,
            "10:00",
            "12:30",
            "02:30",
            "08:00",
        ),  # SHORT + approved unpaid leave (days 10-11)
        # Clean full days after leave
        (12, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (15, "09:00", "17:30", "08:30", "08:00"),  # FULL
        (16, "09:00", "17:30", "08:30", "08:00"),  # FULL
    ],
}

# Leave requests: (start_day, end_day, payment_type, status)
LEAVES = {
    "carol": [
        (3, 7, "paid", "approved"),  # 5 days — approved paid leave
        (8, 9, "paid", "requested"),  # 2 days — pending paid leave
        (10, 11, "unpaid", "approved"),  # 2 days — approved unpaid leave
    ],
    "eve": [
        (
            3,
            7,
            "paid",
            "approved",
        ),  # days 3-7 approved paid — day 4 & 6 also have attendance
        (
            8,
            9,
            "paid",
            "requested",
        ),  # days 8-9 pending paid  — day 8 also has attendance
        (
            10,
            11,
            "unpaid",
            "approved",
        ),  # days 10-11 unpaid      — day 10 also has attendance
    ],
}


def _hhmm_to_secs(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 3600 + int(m) * 60


def _time(hhmm):
    """Return datetime.time from 'HH:MM' string, or None."""
    if hhmm is None:
        return None
    h, m = hhmm.split(":")
    return datetime.time(int(h), int(m))


class Command(BaseCommand):
    help = "Create fixture attendance data for the Monthly Summary feature."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            default=None,
            help="Target month as YYYY-MM (default: current month)",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing fixture employees before recreating",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from attendance.models import Attendance, GraceTime
        from base.models import Company
        from employee.models import Employee, EmployeeWorkInformation
        from leave.models import LeaveRequest, LeaveType

        # -- Resolve target month -------------------------------------------
        month_str = options["month"]
        if month_str:
            year, mon = map(int, month_str.split("-"))
        else:
            today = datetime.date.today()
            year, mon = today.year, today.month

        month_start = datetime.date(year, mon, 1)
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nCreating fixture data for {month_start.strftime('%B %Y')}"
            )
        )
        self.stdout.write(
            "  Grace=30min | min=8h | FULL>=7h30m | HALF>=4h | SHORT<4h+out | MO<4h+no-out"
        )

        # -- Company --------------------------------------------------------
        company = Company.objects.first()
        if not company:
            self.stdout.write(self.style.ERROR("No company found. Create one first."))
            return
        self.stdout.write(f"  Using company: {company.company}")

        # -- Flush if requested ---------------------------------------------
        # We flush attendance + leave records only (not the Employee rows) to
        # avoid PROTECT FK chains in payroll / contracts.  Employees are
        # recreated if missing; existing ones get their data wiped and refilled.
        if options["flush"]:
            from attendance.models import Attendance as _Att
            from leave.models import LeaveRequest as _LR

            fixture_pks = list(
                Employee.objects.filter(
                    email__endswith=f"@{FIXTURE_EMAIL_DOMAIN}"
                ).values_list("pk", flat=True)
            )
            if fixture_pks:
                att_del, _ = _Att.objects.filter(employee_id__in=fixture_pks).delete()
                lr_del, _ = _LR.objects.filter(employee_id__in=fixture_pks).delete()
                self.stdout.write(
                    f"  Flushed: {att_del} attendance records, {lr_del} leave requests."
                )
            else:
                self.stdout.write("  Nothing to flush.")

        # -- Default GraceTime (30 min) -------------------------------------
        grace, created = GraceTime.objects.get_or_create(
            is_default=True,
            defaults={
                "allowed_time": "00:30:00",
                "allowed_time_in_secs": 1800,
                "allowed_clock_in": True,
                "allowed_clock_out": True,
            },
        )
        grace.company_id.add(company)
        if created:
            self.stdout.write("  Created default GraceTime: 30 min")

        # -- Leave types ----------------------------------------------------
        paid_lt = LeaveType.objects.filter(payment="paid").first()
        if not paid_lt:
            self.stdout.write(
                self.style.WARNING(
                    "  No paid LeaveType found — paid leave fixtures skipped."
                )
            )
        unpaid_lt = LeaveType.objects.filter(payment="unpaid").first()
        if not unpaid_lt:
            self.stdout.write(
                self.style.WARNING(
                    "  No unpaid LeaveType found — unpaid leave fixtures skipped."
                )
            )

        # -- Employees ------------------------------------------------------
        fixture_specs = [
            (
                "alice",
                "Alice",
                "Fixture",
                "FX01",
                "alice@" + FIXTURE_EMAIL_DOMAIN,
                "0500000001",
            ),
            (
                "bob",
                "Bob",
                "Fixture",
                "FX02",
                "bob@" + FIXTURE_EMAIL_DOMAIN,
                "0500000002",
            ),
            (
                "carol",
                "Carol",
                "Fixture",
                "FX03",
                "carol@" + FIXTURE_EMAIL_DOMAIN,
                "0500000003",
            ),
            (
                "david",
                "David",
                "Fixture",
                "FX04",
                "david@" + FIXTURE_EMAIL_DOMAIN,
                "0500000004",
            ),
            (
                "eve",
                "Eve",
                "Fixture",
                "FX05",
                "eve@" + FIXTURE_EMAIL_DOMAIN,
                "0500000005",
            ),
        ]

        # Detect extra NOT NULL columns added by other-branch migrations (e.g.
        # healthcare_management) that exist in the DB but are unknown to the
        # current ORM.  We inject them as 0 via raw SQL INSERT.
        from django.db import connection as _conn

        with _conn.cursor() as _cur:
            _cur.execute("PRAGMA table_info(employee_employee)")
            _orm_cols = {f.column for f in Employee._meta.concrete_fields}
            _extra_not_null = sorted(
                row[1]
                for row in _cur.fetchall()
                if row[3] == 1 and row[4] is None and row[1] not in _orm_cols
            )
        if _extra_not_null:
            self.stdout.write(
                self.style.WARNING(
                    f"  Extra NOT NULL DB columns from other branch "
                    f"(set to 0): {', '.join(_extra_not_null)}"
                )
            )

        def _get_or_create_employee(email, first, last, badge, phone, gender):
            try:
                return Employee.objects.get(email=email), False
            except Employee.DoesNotExist:
                pass

            if not _extra_not_null:
                emp = Employee(
                    email=email,
                    employee_first_name=first,
                    employee_last_name=last,
                    badge_id=badge,
                    phone=phone,
                    gender=gender,
                )
                emp.save()
                return emp, True

            # Raw SQL INSERT: ORM fields + extra columns from other branch
            base_cols = [
                "employee_first_name",
                "employee_last_name",
                "email",
                "phone",
                "badge_id",
                "gender",
                "is_active",
                "marital_status",
            ]
            base_vals = [first, last, email, phone, badge, gender, True, "single"]
            all_cols = base_cols + _extra_not_null
            all_vals = base_vals + [0] * len(_extra_not_null)
            col_str = ", ".join(all_cols)
            ph_str = ", ".join(["%s"] * len(all_cols))
            with _conn.cursor() as _c:
                _c.execute(
                    f"INSERT INTO employee_employee ({col_str}) VALUES ({ph_str})",
                    all_vals,
                )
            emp = Employee.objects.get(email=email)
            from employee.models import EmployeeWorkInformation as _EWI

            _EWI.objects.get_or_create(employee_id=emp)
            from django.db.models.signals import post_save as _ps

            _ps.send(sender=Employee, instance=emp, created=True, using="default")
            return emp, True

        employees = {}
        for key, first, last, badge, email, phone in fixture_specs:
            emp, created = _get_or_create_employee(
                email,
                first,
                last,
                badge,
                phone,
                gender="female" if first in ("Alice", "Carol", "Eve") else "male",
            )
            if not created:
                Employee.objects.filter(pk=emp.pk).update(
                    badge_id=badge,
                    employee_first_name=first,
                    employee_last_name=last,
                )

            wi, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=emp)
            wi.company_id = company
            wi.save(update_fields=["company_id"])

            employees[key] = emp
            verb = "Created" if created else "Using existing"
            self.stdout.write(f"  {verb} employee: {emp.get_full_name()} ({badge})")

        # -- Attendance records --------------------------------------------
        att_created = att_updated = att_skipped = 0
        for key, specs in SCENARIOS.items():
            emp = employees[key]
            for day, clock_in, clock_out, worked_hhmm, min_hhmm in specs:
                try:
                    att_date = datetime.date(year, mon, day)
                except ValueError:
                    continue

                worked_secs = _hhmm_to_secs(worked_hhmm)
                att, created = Attendance.objects.get_or_create(
                    employee_id=emp,
                    attendance_date=att_date,
                    defaults={
                        "attendance_clock_in": _time(clock_in),
                        "attendance_clock_out": _time(clock_out),
                        "attendance_worked_hour": worked_hhmm,
                        "attendance_overtime": "00:00",
                        "minimum_hour": min_hhmm,
                        "at_work_second": worked_secs,
                        "attendance_validated": True,
                    },
                )
                if created:
                    att_created += 1
                else:
                    # Update worked hours so --flush-less reruns fix stale data
                    Attendance.objects.filter(pk=att.pk).update(
                        attendance_clock_in=_time(clock_in),
                        attendance_clock_out=_time(clock_out),
                        attendance_worked_hour=worked_hhmm,
                        minimum_hour=min_hhmm,
                        at_work_second=worked_secs,
                    )
                    att_updated += 1

        self.stdout.write(
            f"  Attendance: {att_created} created, {att_updated} updated, {att_skipped} unchanged"
        )

        # -- Leave requests ------------------------------------------------
        lv_created = lv_skipped = 0
        for key, leave_specs in LEAVES.items():
            emp = employees[key]
            for start_day, end_day, payment, status in leave_specs:
                if payment == "paid" and not paid_lt:
                    continue
                if payment == "unpaid" and not unpaid_lt:
                    continue
                lt = paid_lt if payment == "paid" else unpaid_lt
                try:
                    s = datetime.date(year, mon, start_day)
                    e = datetime.date(year, mon, end_day)
                except ValueError:
                    continue

                if LeaveRequest.objects.filter(
                    employee_id=emp,
                    leave_type_id=lt,
                    start_date=s,
                    end_date=e,
                ).exists():
                    lv_skipped += 1
                    continue

                LeaveRequest.objects.create(
                    employee_id=emp,
                    leave_type_id=lt,
                    start_date=s,
                    end_date=e,
                    status=status,
                    description=f"Fixture leave — {status}",
                    start_date_breakdown="full_day",
                    end_date_breakdown="full_day",
                )
                lv_created += 1

        self.stdout.write(
            f"  Leave requests: {lv_created} created, {lv_skipped} already existed"
        )

        # -- Summary -------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done. Fixture employees:"))
        for key, (_, first, last, badge, email, _phone) in zip(
            employees.keys(), fixture_specs
        ):
            scenario_desc = {
                "alice": "Full days + 1 half day (day 12)",
                "bob": "Full + Half + Short hours + Missing out",
                "carol": "Full days + Approved/Pending/Unpaid leave",
                "david": "Grace boundary edge cases",
                "eve": "OVERLAP: attendance on leave days (days 4,6,8,10)",
            }
            self.stdout.write(
                f"  {first} {last:8s}  {badge}  {email}"
                f"  <- {scenario_desc.get(key, '')}"
            )
        self.stdout.write("")
        self.stdout.write("Expected classification with 30-min grace:")
        self.stdout.write("  Alice : ~14 full + 0.5 half  = 14.5 present")
        self.stdout.write(
            "  Bob   :  7 full + 1.5 half   =  8.5 present,  2 short,  2 MO"
        )
        self.stdout.write("  Carol :  5 full + approved leaves")
        self.stdout.write(
            "  David :  3 full + 1 half boundary + 1 half below-grace,  1 short,  1 MO"
        )
        self.stdout.write(
            "  Eve   :  OVERLAP — day4=FULL+approved-leave, day6=MO+approved-leave,"
        )
        self.stdout.write(
            "                     day8=HALF+pending-leave,  day10=SHORT+unpaid-leave"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Open: Attendance -> Monthly Summary -> "
            f"From {month_start}  To {datetime.date(year, mon, 28)}"
        )
        self.stdout.write(
            "Filter by employee or search 'Fixture' to see only these records.\n"
        )
