"""Assigned leave: how many days of each leave type an employee has."""

import re

from django.db import transaction
from django.utils import timezone
from simple_history.utils import bulk_create_with_history, bulk_update_with_history

from employee.methods.methods import clean_badge_id, import_valid_date
from employee.models import Employee
from leave.models import AvailableLeave, LeaveType

from .base import Checked, Context, Dataset, Field


def _days(value, label, errors, default):
    """A non-negative number of days; blank takes ``default``."""
    if value is None or str(value).strip() == "":
        return default
    try:
        days = float(value)
    except (TypeError, ValueError):
        errors[f"{label} Error"] = f"{label} must be a number."
        return None
    if days != days or days in (float("inf"), float("-inf")) or days < 0:
        errors[f"{label} Error"] = f"{label} must be a non-negative number."
        return None
    return days


class AssignedLeaveDataset(Dataset):
    key = "assigned_leave"
    label = "Leave Balances"
    subtitle = "Leave balances for each employee"
    icon = "calendar-outline"
    permission = "leave.add_availableleave"
    update_permissions = ["leave.change_availableleave"]
    supports_update = True
    match_choices = ["Badge ID", "Leave Type"]
    default_match_keys = ["Badge ID", "Leave Type"]
    locked_match_keys = ["Badge ID", "Leave Type"]
    match_help = (
        "Each row must find exactly one balance, by employee and leave type. Only the days and the date "
        "are changed, and blank cells leave the current value alone."
    )
    created_models = {"leave_types": LeaveType}
    preview_columns = [
        "Badge ID",
        "Leave Type",
        "Available Days",
        "Carryforward Days",
        "Assigned Date",
    ]
    hint_create = (
        "Assigns leave types to employees. A balance that already exists is refused."
    )
    hint_update = "Finds each employee's balance by Badge ID and Leave Type and changes only the days the sheet fills in."
    hint_both = (
        "Updates balances that already exist, and assigns the rest, in the same import."
    )
    upload_note = (
        "Employees are found by Badge ID and leave types by name. A blank Available Days or "
        "Carryforward Days is 0 when assigning, and left alone when updating. A leave type that does not "
        "exist yet is created from its name; set its reset and carryforward rules on the leave type afterwards."
    )

    fields = [
        Field(
            "Badge ID",
            required=True,
            group="Assignment",
            sample="E-1048",
            aliases=(
                "employee badge id",
                "employee id",
                "emp id",
                "staff id",
                "badge",
                "id",
            ),
        ),
        Field(
            "Leave Type",
            required=True,
            group="Assignment",
            sample="Casual Leave",
            aliases=("leave", "type", "leave name"),
            kind="suggest",
            suggest="leave_types",
        ),
        Field(
            "Available Days",
            group="Balance",
            sample="12",
            aliases=("days", "balance", "leave days", "entitlement", "available"),
            kind="number",
        ),
        Field(
            "Carryforward Days",
            group="Balance",
            sample="0",
            aliases=("carry forward days", "carry forward", "carryforward"),
            kind="number",
        ),
        Field(
            "Assigned Date",
            group="Balance",
            sample="2024-01-01",
            aliases=("start date", "from date", "date"),
            kind="date",
        ),
    ]

    def suggestions(self):
        return {
            "leave_types": sorted(
                set(LeaveType.objects.entire().values_list("name", flat=True))
            )
        }

    def prepare(self, rows, ctx):
        for row in rows:
            row["Badge ID"] = (
                clean_badge_id(row.get("Badge ID")) if row.get("Badge ID") else None
            )
            value = row.get("Assigned Date")
            if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}[ T]", value):
                row["Assigned Date"] = value[:10]
        return rows

    # -------------------------------------------------------------- check
    def check(
        self, rows, ctx: Context, progress=None, mode="create", match_keys=()
    ) -> Checked:
        rows = self.prepare(rows, ctx)
        result = Checked()
        employees = {
            str(e.badge_id).strip().lower(): e
            for e in Employee.objects.entire()
            .select_related("employee_work_info")
            .filter(badge_id__isnull=False)
        }
        types = {}
        for leave_type in LeaveType.objects.entire():
            types.setdefault(leave_type.name.strip().lower(), []).append(leave_type)
        balances = {
            (b.employee_id_id, b.leave_type_id_id): b
            for b in AvailableLeave.objects.entire()
        }
        seen = set()
        new_types = (
            {}
        )  # lower-case name -> [name as written, largest Available Days given]
        max_name = LeaveType._meta.get_field("name").max_length
        total = len(rows) or 1

        for position, row in enumerate(rows, start=1):
            if progress and (position % 25 == 0 or position == total):
                progress(5 + int(position / total * 90))
            errors = {}
            employee = leave_type = None

            badge = row.get("Badge ID")
            if not badge:
                errors["Badge ID Error"] = "Badge ID is required."
            else:
                employee = employees.get(str(badge).strip().lower())
                if employee is None:
                    errors["Badge ID Error"] = "No employee has this Badge ID."
                elif ctx.company is not None:
                    info = getattr(employee, "employee_work_info", None)
                    if getattr(info, "company_id_id", None) != ctx.company.pk:
                        errors["Badge ID Error"] = (
                            f"This employee is not in {ctx.company.company}."
                        )
                        employee = None

            name = (row.get("Leave Type") or "").strip()
            if not name:
                errors["Leave Type Error"] = "Leave Type is required."
            else:
                options = types.get(name.lower(), [])
                if options and employee is not None:
                    leave_type, why = self._leave_type_for(options, employee)
                    if why:
                        errors["Leave Type Error"] = why
                elif options:
                    leave_type = options[0]
                elif mode == "update":
                    errors["Leave Type Error"] = "This leave type does not exist."
                elif len(name) > max_name:
                    errors["Leave Type Error"] = (
                        f"Leave Type is {len(name)} characters; the most allowed is {max_name}."
                    )
                else:
                    row["__new_type"] = name.lower()

            balance = None
            if employee is not None and leave_type is not None:
                balance = balances.get((employee.pk, leave_type.pk))
            if employee is not None and (
                leave_type is not None or row.get("__new_type")
            ):
                pair = (
                    employee.pk,
                    leave_type.pk if leave_type is not None else row["__new_type"],
                )
                if pair in seen:
                    errors["Leave Type Error"] = (
                        "This employee and leave type appear more than once in the file."
                    )
                elif balance is not None and mode == "create":
                    errors["Leave Type Error"] = (
                        "This leave type is already assigned to the employee."
                    )
                elif balance is None and leave_type is not None and mode == "update":
                    errors["Leave Type Error"] = (
                        "This leave type is not assigned to the employee yet."
                    )

            updating = balance is not None and mode in ("update", "both")
            # An update changes only what the sheet fills in; a new balance starts from 0.
            blank = None if updating else 0
            available = _days(
                row.get("Available Days"), "Available Days", errors, blank
            )
            carry = _days(
                row.get("Carryforward Days"), "Carryforward Days", errors, blank
            )
            when = None
            if row.get("Assigned Date"):
                date_errors = {}
                when = import_valid_date(
                    row["Assigned Date"],
                    "Assigned Date",
                    date_errors,
                    "Assigned Date Error",
                )
                if date_errors:
                    errors.update(date_errors)

            if errors:
                result.errors.append(self._error_entry(row, errors, employee))
                continue

            if updating:
                seen.add((employee.pk, leave_type.pk))
                apply, changes = self._changes(balance, available, carry, when)
                if not changes:
                    result.unchanged.append(row)
                    continue
                row.update(
                    {
                        "__op": "update",
                        "__pk": balance.pk,
                        "__apply": apply,
                        "__changes": changes,
                    }
                )
                result.valid.append(row)
                continue

            if row.get("__new_type"):
                seen.add((employee.pk, row["__new_type"]))
                made = new_types.setdefault(row["__new_type"], [name, None])
                if row.get("Available Days"):
                    made[1] = max(made[1] or 0, available)
            else:
                seen.add((employee.pk, leave_type.pk))
            row.update(
                {
                    "__op": "create",
                    "__employee": employee.pk,
                    "__leave_type": leave_type.pk if leave_type is not None else None,
                    "__available": available,
                    "__carry": carry,
                    "__date": when,
                    "__changes": ["New balance"] if mode == "both" else [],
                }
            )
            result.valid.append(row)

        result.errors.sort(key=lambda e: e["row"])
        # Only the leave types some valid row still needs.
        needed = {r["__new_type"] for r in result.valid if r.get("__new_type")}
        result.will_create = {"leave_types": sorted(new_types[k][0] for k in needed)}
        if progress:
            progress(100)
        return result

    @staticmethod
    def _changes(balance, available, carry, when):
        """({field: new value}, ["Label: old -> new"]) for what the sheet changes."""
        apply, changes = {}, []

        def note(label, field, old, new):
            apply[field] = new
            changes.append(f"{label}: {old if old not in (None, '') else '-'} → {new}")

        if available is not None and float(available) != float(
            balance.available_days or 0
        ):
            note("Available Days", "available_days", balance.available_days, available)
        if carry is not None and float(carry) != float(balance.carryforward_days or 0):
            note(
                "Carryforward Days",
                "carryforward_days",
                balance.carryforward_days,
                carry,
            )
        if when is not None and when != balance.assigned_date:
            note("Assigned Date", "assigned_date", balance.assigned_date, when)
        return apply, changes

    @staticmethod
    def _leave_type_for(options, employee):
        """The leave type of that name for this employee's company (or for every company)."""
        info = getattr(employee, "employee_work_info", None)
        company = getattr(info, "company_id_id", None)
        for option in options:
            if option.company_id_id == company and company is not None:
                return option, ""
        for option in options:
            if option.company_id_id is None:
                return option, ""
        return None, "This leave type belongs to a different company than the employee."

    @staticmethod
    def _error_entry(row, errors, employee):
        keys = {f.key for f in AssignedLeaveDataset.fields}
        by_field = {
            k[: -len(" Error")]: v
            for k, v in errors.items()
            if k[: -len(" Error")] in keys
        }
        return {
            "row": int(row.get("__row") or 0),
            "name": employee.get_full_name() if employee is not None else "-",
            "badge": row.get("Badge ID") or "-",
            "messages": list(errors.values()),
            "by_field": by_field,
            "data": {k: v for k, v in row.items() if k in keys},
        }

    # ------------------------------------------------------------- commit
    def commit(self, rows, ctx: Context, mode="create", progress=None) -> dict:
        new = [r for r in rows if r.get("__op", "create") == "create"]
        known = [r for r in rows if r.get("__op") == "update"]
        employees = {
            e.pk: e
            for e in Employee.objects.entire().filter(
                pk__in={r["__employee"] for r in new}
            )
        }
        types = {
            t.pk: t
            for t in LeaveType.objects.entire().filter(
                pk__in={r["__leave_type"] for r in new if r["__leave_type"]}
            )
        }
        today = timezone.now().date()
        made, created_types, touched = [], {}, []
        with transaction.atomic():
            for row in new:
                key = row.get("__new_type")
                if key and key not in created_types:
                    days = [
                        r["__available"]
                        for r in new
                        if r.get("__new_type") == key and r.get("Available Days")
                    ]
                    created_types[key] = LeaveType.objects.create(
                        name=row["Leave Type"].strip(),
                        total_days=(
                            max(days)
                            if days
                            else LeaveType._meta.get_field("total_days").default
                        ),
                        company_id=ctx.company,
                    )
            for row in new:
                leave = AvailableLeave(
                    employee_id=employees[row["__employee"]],
                    leave_type_id=(
                        created_types[row["__new_type"]]
                        if row.get("__new_type")
                        else types[row["__leave_type"]]
                    ),
                    available_days=row["__available"],
                    carryforward_days=row["__carry"],
                    assigned_date=row["__date"] or today,
                )
                # What save() would work out: reset date, carryforward expiry and the total.
                leave.pre_save_processing()
                made.append(leave)
            # With history, so each balance shows up in the leave ledger.
            bulk_create_with_history(
                made,
                AvailableLeave,
                default_user=ctx.user,
                default_change_reason="Imported through Master Data Import",
            )

            balances = {
                b.pk: b
                for b in AvailableLeave.objects.entire().filter(
                    pk__in=[r["__pk"] for r in known]
                )
            }
            for row in known:
                balance = balances[row["__pk"]]
                for field, value in row["__apply"].items():
                    setattr(balance, field, value)
                balance.total_leave_days = round(
                    max(balance.available_days + balance.carryforward_days, 0), 3
                )
                touched.append(balance)
            if touched:
                bulk_update_with_history(
                    touched,
                    AvailableLeave,
                    [
                        "available_days",
                        "carryforward_days",
                        "total_leave_days",
                        "assigned_date",
                    ],
                    manager=AvailableLeave.objects.entire(),
                    default_user=ctx.user,
                    default_change_reason="Updated through Master Data Import",
                )
        if progress:
            progress(100)
        return {
            "assigned": len(made),
            "updated": len(touched),
            "leave_types": len(created_types),
        }
