from django.apps import apps

try:
    RecruitmentMailTemplate = apps.get_model("recruitment", "RecruitmentMailTemplate")
    HorillaMailTemplate = apps.get_model("base", "HorillaMailTemplate")

    recruitment_mail_templates = RecruitmentMailTemplate.objects.all()
    for recruitment_mail in recruitment_mail_templates:
        if not HorillaMailTemplate.objects.filter(
            title=recruitment_mail.title
        ).exists():
            horilla_mail = HorillaMailTemplate(
                id=recruitment_mail.id,
                title=recruitment_mail.title,
                body=recruitment_mail.body,
                company_id=recruitment_mail.company_id,
            )
            horilla_mail.save()

    horilla_mail_templates = HorillaMailTemplate.objects.all()
    RecruitmentMailTemplate.objects.all().delete()
except Exception as e:
    pass

try:
    LeaveHoliday = apps.get_model("leave", "Holiday")
    BaseHoliday = apps.get_model("base", "Holidays")

    leave_holidays = LeaveHoliday.objects.all()
    for holiday in leave_holidays:
        if not BaseHoliday.objects.filter(
            name=holiday.name,
            start_date=holiday.start_date,
            end_date=holiday.end_date,
        ).exists():
            horilla = BaseHoliday(
                id=holiday.id,
                name=holiday.name,
                start_date=holiday.start_date,
                end_date=holiday.end_date,
            )
            horilla.save()

    base_leaves = BaseHoliday.objects.all()
    LeaveHoliday.objects.all().delete()
except Exception as e:
    pass

try:
    PenaltyAccount = apps.get_model("attendance", "PenaltyAccount")
    PenaltyAccounts = apps.get_model("base", "PenaltyAccounts")

    penalties = PenaltyAccount.objects.all()
    for penalty in penalties:
        filter_conditions = {
            "employee_id": penalty.employee_id,
            "penalty_amount": penalty.penalty_amount,
        }
        if apps.is_installed("attendance"):
            filter_conditions.update(
                {
                    "late_early_id": penalty.late_early_id,
                }
            )
        if apps.is_installed("leave"):
            filter_conditions.update(
                {
                    "leave_request_id": penalty.leave_request_id,
                    "leave_type_id": penalty.leave_type_id,
                    "minus_leaves": penalty.minus_leaves,
                    "deduct_from_carry_forward": penalty.deduct_from_carry_forward,
                }
            )

        if not PenaltyAccounts.objects.filter(**filter_conditions).exists():
            horilla = PenaltyAccounts(
                id=penalty.id,
                employee_id=penalty.employee_id,
                penalty_amount=penalty.penalty_amount,
            )
            if apps.is_installed("attendance"):
                horilla.late_early_id = penalty.late_early_id
            if apps.is_installed("leave"):
                horilla.leave_request_id = penalty.leave_request_id
                horilla.leave_type_id = penalty.leave_type_id
                horilla.minus_leaves = penalty.minus_leaves
                horilla.deduct_from_carry_forward = penalty.deduct_from_carry_forward
            horilla.save()
    penalty_accounts = PenaltyAccounts.objects.all()
    PenaltyAccount.objects.all().delete()
except Exception as e:
    pass

try:
    CompanyLeave = apps.get_model("leave", "CompanyLeave")
    BaseCompanyLeave = apps.get_model("base", "CompanyLeaves")

    company_leaves = CompanyLeave.objects.all()
    for leave in company_leaves:
        if not BaseCompanyLeave.objects.filter(
            based_on_week=leave.based_on_week,
            based_on_week_day=leave.based_on_week_day,
        ).exists():
            horilla = BaseCompanyLeave(
                id=leave.id,
                based_on_week=leave.based_on_week,
                based_on_week_day=leave.based_on_week_day,
            )
            horilla.save()

    base_leaves = BaseCompanyLeave.objects.all()
    CompanyLeave.objects.all().delete()
except Exception as e:
    pass

try:
    WorkRecord = apps.get_model("payroll", "WorkRecord")
    WorkRecords = apps.get_model("attendance", "WorkRecords")

    work_records = WorkRecord.objects.all()
    for work_record in work_records:
        if not WorkRecords.objects.filter(
            record_name=work_record.record_name,
            employee_id=work_record.employee_id,
            date=work_record.date,
        ).exists():
            new_work_record = WorkRecords(
                id=work_record.id,
                record_name=work_record.record_name,
                work_record_type=work_record.work_record_type,
                employee_id=work_record.employee_id,
                date=work_record.date,
                at_work=work_record.at_work,
                min_hour=work_record.min_hour,
                at_work_second=work_record.at_work_second,
                min_hour_second=work_record.min_hour_second,
                note=work_record.note,
                message=work_record.message,
                is_attendance_record=work_record.is_attendance_record,
                is_leave_record=work_record.is_leave_record,
                day_percentage=work_record.day_percentage,
                last_update=work_record.last_update,
            )
            new_work_record.save()

    new_work_records = WorkRecords.objects.all()
    WorkRecord.objects.all().delete()
except Exception as e:
    pass
