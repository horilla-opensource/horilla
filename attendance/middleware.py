from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from attendance.methods.utils import Request


class AttendanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        self.trigger_function()

    def trigger_function(self):
        from attendance.models import Attendance, AttendanceActivity
        from attendance.views.clock_in_out import clock_out
        from base.models import EmployeeShiftSchedule

        automatic_check_out_shifts = EmployeeShiftSchedule.objects.filter(
            is_auto_punch_out_enabled=True
        )

        for shift_schedule in automatic_check_out_shifts:
            activities = AttendanceActivity.objects.filter(
                shift_day=shift_schedule.day,
                clock_out_date=None,
                clock_out=None,
            ).order_by("-created_at")

            for activity in activities:
                attendance = Attendance.objects.filter(
                    employee_id=activity.employee_id,
                    attendance_clock_out=None,
                    attendance_clock_out_date=None,
                    shift_id=shift_schedule.shift_id,
                    attendance_day=shift_schedule.day,
                    attendance_date=activity.attendance_date,
                ).first()

                if attendance:
                    date = activity.attendance_date
                    if shift_schedule.is_night_shift:
                        date += timedelta(days=1)

                    combined_datetime = timezone.make_aware(
                        datetime.combine(date, shift_schedule.auto_punch_out_time)
                    )
                    current_time = timezone.now()

                    if combined_datetime < current_time:
                        try:
                            clock_out(
                                Request(
                                    user=attendance.employee_id.employee_user_id,
                                    date=date,
                                    time=shift_schedule.auto_punch_out_time,
                                    datetime=combined_datetime,
                                )
                            )
                        except Exception as e:
                            print(f"{e}")
