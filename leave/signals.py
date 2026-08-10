# leave/signals.py

import threading

from django.apps import apps
from django.db.models.signals import post_migrate, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from horilla.methods import get_horilla_model_class
from leave.models import LeaveRequest, LeaveRequestConditionApproval

if apps.is_installed("attendance"):

    @receiver(post_save, sender=LeaveRequest)
    def leaverequest_pre_save(sender, instance, **_kwargs):
        """
        Overriding LeaveRequest model save method
        """
        WorkRecords = get_horilla_model_class(
            app_label="attendance", model="workrecords"
        )
        if (
            instance.start_date == instance.end_date
            and instance.end_date_breakdown != instance.start_date_breakdown
        ):
            instance.end_date_breakdown = instance.start_date_breakdown
            super(LeaveRequest, instance).save()

        period_dates = instance.requested_dates()
        if instance.status == "approved":
            for date in period_dates:
                try:
                    work_entry = (
                        WorkRecords.objects.filter(
                            date=date,
                            employee_id=instance.employee_id,
                        ).first()
                        if WorkRecords.objects.filter(
                            date=date,
                            employee_id=instance.employee_id,
                        ).exists()
                        else WorkRecords()
                    )
                    work_entry.employee_id = instance.employee_id
                    work_entry.is_leave_record = True
                    work_entry.leave_request_id = instance
                    work_entry.day_percentage = (
                        0.50
                        if instance.start_date == date
                        and instance.start_date_breakdown == "first_half"
                        or instance.end_date == date
                        and instance.end_date_breakdown == "second_half"
                        else 0.00
                    )
                    status = (
                        "CONF"
                        if instance.start_date == date
                        and instance.start_date_breakdown == "first_half"
                        or instance.end_date == date
                        and instance.end_date_breakdown == "second_half"
                        else "ABS"
                    )
                    work_entry.work_record_type = status
                    work_entry.date = date
                    work_entry.message = (
                        "Leave"
                        if status == "ABS"
                        else _("Half day Attendance need to validate")
                    )
                    work_entry.save()

                except Exception as e:
                    print(e)

        else:
            for date in period_dates:
                WorkRecords._base_manager.filter(
                    is_leave_record=True,
                    date=date,
                    employee_id=instance.employee_id,
                ).delete()

    @receiver(pre_delete, sender=LeaveRequest)
    def leaverequest_pre_delete(sender, instance, **kwargs):
        from attendance.models import WorkRecords

        work_records = WorkRecords._base_manager.filter(
            leave_request_id=instance
        ).delete()


# @receiver(post_migrate)
def add_missing_leave_to_workrecords(sender, **kwargs):
    if sender.label not in ["attendance", "leave"]:
        return

    if not apps.is_installed("attendance"):
        return
    try:
        from attendance.models import WorkRecords
        from leave.models import LeaveRequest

        work_records = WorkRecords.objects.filter(
            is_leave_record=True, leave_request_id__isnull=True
        )
        if not work_records.exists():
            return

        leave_requests = LeaveRequest.objects.all()
        date_leave_map = {}

        for leave in leave_requests:
            for date in leave.requested_dates():
                key = (leave.employee_id, date)
                date_leave_map[key] = leave

        records_to_update = []
        for record in work_records:
            leave_request = date_leave_map.get((record.employee_id, record.date))
            if leave_request:
                record.leave_request_id = leave_request
                records_to_update.append(record)

        if records_to_update:
            WorkRecords.objects.bulk_update(
                records_to_update, ["leave_request_id"], batch_size=500
            )
            print(
                f"Successfully updated {len(records_to_update)} work records with leave information"
            )

    except Exception as e:
        print(f"Error in leave/work records sync: {e}")


@receiver(post_save, sender=LeaveRequestConditionApproval)
def auto_approve_self_approval_stage(sender, instance, created, **kwargs):
    """
    When an approver in the multiple-approval chain is the same employee who
    submitted the leave request, automatically approve their stage so the
    request is not stuck and can progress to the next approver.
    """
    if created and instance.manager_id == instance.leave_request_id.employee_id:
        sender.objects.filter(pk=instance.pk).update(is_approved=True)


# ============================================================================
# ROYAL FALCON SECURITY - Leave Accrual Policy Signal Handlers
# ============================================================================


@receiver(post_save, sender="leave.UnpaidLeave")
def handle_unpaid_leave_status_change(sender, instance, created, update_fields, **kwargs):
    """
    Handle accrual pause when unpaid leave is approved.
    Resume accrual when employee returns from unpaid leave.
    """
    from leave.models import UnpaidLeave
    from leave.accrual_service import pause_accrual_for_unpaid_leave, resume_accrual_after_unpaid_leave
    
    try:
        # Get the current instance to check status
        unpaid_leave = UnpaidLeave.objects.get(pk=instance.pk)
        
        if unpaid_leave.status == "active" and (created or (update_fields and "status" in update_fields)):
            # Pause accrual when unpaid leave is activated
            pause_accrual_for_unpaid_leave(unpaid_leave)
            
        elif unpaid_leave.status == "returned" and update_fields and "status" in update_fields:
            # Resume accrual when employee returns
            resume_accrual_after_unpaid_leave(unpaid_leave)
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error handling unpaid leave status change: {str(e)}")


@receiver(post_save, sender="leave.UnauthorizedExtension")
def handle_unauthorized_extension_approval(sender, instance, created, update_fields, **kwargs):
    """
    Handle service adjustment when unauthorized extension is approved.
    """
    from leave.models import UnauthorizedExtension, EmployeeServiceAdjustment
    
    try:
        unauthorized_ext = UnauthorizedExtension.objects.get(pk=instance.pk)
        
        # Service adjustment is created in the create_unauthorized_extension_record function
        # This signal just logs the approval for audit purposes
        if unauthorized_ext.status == "approved" and update_fields and "status" in update_fields:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Unauthorized extension for {unauthorized_ext.employee_id.badge_id} approved: "
                f"{unauthorized_ext.unauthorized_days} days from {unauthorized_ext.approved_return_date}"
            )
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error handling unauthorized extension approval: {str(e)}")
