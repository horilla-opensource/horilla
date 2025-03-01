# attendance/signals.py

from datetime import datetime, timedelta
from django.apps import apps
from django.db.models.signals import post_migrate, post_save, pre_delete
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver

from attendance.methods.utils import strtime_seconds
from attendance.models import (
    Attendance,
    AttendanceGeneralSetting,
    WorkRecords,
)
from base.models import Company, PenaltyAccounts
from employee.models import Employee
from horilla.methods import get_horilla_model_class


if apps.is_installed("payroll"):

    @receiver(post_save, sender=PenaltyAccounts)
    def create_initial_stage(sender, instance, created, **kwargs):
        """
        This is post save method, used to create initial stage for the recruitment
        """
        # only work when creating
        if created:
            penalty_amount = instance.penalty_amount
            if penalty_amount:
                Deduction = get_horilla_model_class(
                    app_label="payroll", model="deduction"
                )
                penalty = Deduction()
                if instance.late_early_id:
                    penalty.title = (
                        f"{instance.late_early_id.get_type_display()} penalty"
                    )
                    penalty.one_time_date = (
                        instance.late_early_id.attendance_id.attendance_date
                    )
                elif instance.leave_request_id:
                    penalty.title = (
                        f"Leave penalty {instance.leave_request_id.end_date}"
                    )
                    penalty.one_time_date = instance.leave_request_id.end_date
                else:
                    penalty.title = f"Penalty on {datetime.today()}"
                    penalty.one_time_date = datetime.today()
                penalty.include_active_employees = False
                penalty.is_fixed = True
                penalty.amount = instance.penalty_amount
                penalty.only_show_under_employee = True
                penalty.save()
                penalty.include_active_employees = False
                penalty.specific_employees.add(instance.employee_id)
                penalty.save()

            if instance.leave_type_id and instance.minus_leaves:
                available = instance.employee_id.available_leave.filter(
                    leave_type_id=instance.leave_type_id
                ).first()
                unit = round(instance.minus_leaves * 2) / 2
                if not instance.deduct_from_carry_forward:
                    available.available_days = max(0, (available.available_days - unit))
                else:
                    available.carryforward_days = max(
                        0, (available.carryforward_days - unit)
                    )

                available.save()


@receiver(post_save, sender=Attendance)
def attendance_post_save(sender, instance, **kwargs):
    """
    Handle post-save actions for Attendance model.
    """
    min_hour_second = strtime_seconds(instance.minimum_hour)
    at_work_second = strtime_seconds(instance.attendance_worked_hour)

    if not instance.attendance_validated:
        status, message = "CONF", _("Validate the attendance")
    elif at_work_second >= min_hour_second:
        status, message = "FDP", _("Present")
    elif at_work_second >= min_hour_second / 2:
        status, message = "HDP", _("Incomplete minimum hour")
    else:
        status, message = "ABS", _("Incomplete half minimum hour")
    try:
        work_record, created = WorkRecords.objects.get_or_create(
            date=instance.attendance_date,
            employee_id=instance.employee_id,
        )
    except WorkRecords.MultipleObjectsReturned:
        work_record = WorkRecords.objects.filter(
            date=instance.attendance_date,
            employee_id=instance.employee_id,
        )
        work_record = work_record.first()

    work_record.employee_id = instance.employee_id
    work_record.date = instance.attendance_date
    work_record.at_work = instance.attendance_worked_hour
    work_record.min_hour = instance.minimum_hour
    work_record.min_hour_second = min_hour_second
    work_record.at_work_second = at_work_second
    work_record.work_record_type = status
    work_record.message = message
    work_record.is_attendance_record = True
    work_record.attendance_id = instance
    work_record.shift_id = instance.shift_id

    if instance.attendance_validated:
        work_record.day_percentage = (
            1.00 if at_work_second > min_hour_second / 2 else 0.50
        )

    if work_record.is_leave_record:
        message = (
            _("Half day leave") if status == "HDP" else _("An approved leave exists")
        )

    if not instance.attendance_clock_out:
        status, message = "FDP", _("Currently working")

    work_record.work_record_type = status
    work_record.message = message
    work_record.save()


@receiver(pre_delete, sender=Attendance)
def attendance_pre_delete(sender, instance, **_kwargs):
    """
    Overriding Attendance model delete method
    """
    # Perform any actions before deleting the instance
    # ...
    WorkRecords.objects.filter(
        employee_id=instance.employee_id,
        is_attendance_record=True,
        date=instance.attendance_date,
    ).delete()


@receiver(post_migrate)
def add_missing_attendance_to_workrecord(sender, **kwargs):
    if sender.label not in ["attendance", "leave"]:
        return

    from attendance.models import WorkRecords, Attendance

    try:
        work_records = WorkRecords.objects.filter(
            is_attendance_record=True, attendance_id__isnull=True
        )

        if not work_records.exists():
            return

        attendances = Attendance.objects.all()
        attendance_map = {
            (att.employee_id, att.attendance_date): att for att in attendances
        }

        records_to_update = []
        for record in work_records:
            attendance = attendance_map.get((record.employee_id, record.date))
            if attendance:
                record.attendance_id = attendance
                records_to_update.append(record)
            else:
                record.delete()

        if records_to_update:
            WorkRecords.objects.bulk_update(
                records_to_update, ["attendance_id"], batch_size=500
            )
            print(
                f"Successfully updated {len(records_to_update)} work records with attendance information."
            )

    except Exception as e:
        print(f"Error updating work records with attendance: {e}")


@receiver(post_migrate)
def add_missing_shift_to_work_record(sender, **kwargs):
    if sender.label not in ["attendance", "leave"]:
        return

    try:
        work_records = WorkRecords.objects.filter(
            is_attendance_record=True, shift_id__isnull=True
        )

        if not work_records.exists():
            return

        records_to_update = []

        for record in work_records:
            if record.attendance_id:
                record.shift_id = record.attendance_id.shift_id
            else:
                record.shift_id = record.employee_id.employee_work_info.shift_id

            records_to_update.append(record)

        if records_to_update:
            WorkRecords.objects.bulk_update(
                records_to_update, ["shift_id"], batch_size=500
            )
            print(
                f"Successfully updated {len(records_to_update)} work records with shift information."
            )

    except Exception as e:
        print(f"Error updating work records with shift information: {e}")


@receiver(post_save, sender=Company)
def create_attendance_setting(sender, instance, created, raw, **kwargs):
    """
    Signal receiver that automatically creates an AttendanceGeneralSetting object
    whenever a new Company is created. This does NOT skip creation during
    loaddata, so the object will also be created when fixture data is loaded.
    """
    AttendanceGeneralSetting.objects.get_or_create(company_id=None)
    if created:
        AttendanceGeneralSetting.objects.get_or_create(company_id=instance)

@receiver(post_migrate)
def create_missing_work_records(sender, **kwargs):
    if sender.label not in ["attendance"]:
        return

    employees = Employee.objects.all()
    work_records = WorkRecords.objects.all()

    if work_records.exists():
        st_date = work_records.earliest("date").date

        for employee in employees:
            try:
                start_date = employee.employee_work_info.date_joining or st_date
                end_date = datetime.today().date()

                existing_dates = set(
                    WorkRecords.objects.filter(employee_id=employee.id).values_list("date", flat=True)
                )

                all_dates = {start_date + timedelta(days=i) for i in range((end_date - start_date).days)}
                missing_dates = all_dates - existing_dates

                work_records_to_create = [
                    WorkRecords(
                        employee_id=employee,
                        date=missing_date,
                        work_record_type="DFT",
                        shift_id=employee.employee_work_info.shift_id,
                    )
                    for missing_date in missing_dates
                ]

                if work_records_to_create:
                    WorkRecords.objects.bulk_create(work_records_to_create, batch_size=500, ignore_conflicts=True)

            except Exception as e:
                print(f"Error creating missing work records for employee {employee}: {e}")
                