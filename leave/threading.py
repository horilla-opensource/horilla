from threading import Thread

from django.contrib import messages
from django.core.mail import EmailMessage
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from base.backends import ConfiguredEmailBackend


class LeaveMailSendThread(Thread):

    def __init__(self, request, leave_request, type):
        Thread.__init__(self)
        self.request = request
        self.leave_request = leave_request
        self.type = type
        self.host = request.get_host()
        self.protocol = "https" if request.is_secure() else "http"

    def send_email(self, subject, content, recipients, leave_request_id="#"):
        host = self.host
        protocol = self.protocol
        email_backend = ConfiguredEmailBackend()
        if leave_request_id != "#":
            link = int(leave_request_id)
        for recipient in recipients:
            if recipient:
                html_message = render_to_string(
                    "base/mail_templates/leave_request_template.html",
                    {
                        "link": link,
                        "instance": recipient,
                        "host": host,
                        "protocol": protocol,
                        "subject": subject,
                        "content": content,
                    },
                )

                email = EmailMessage(
                    subject,
                    html_message,
                    email_backend.dynamic_from_email_with_display_name,
                    [recipient.email],
                )
                email.content_subtype = "html"
                try:
                    email.send()
                except:
                    messages.error(
                        self.request, f"Mail not sent to {recipient.get_full_name()}"
                    )

    def run(self) -> None:
        super().run()
        if self.type == "request":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            content_manager = f"This is to inform you that a leave request has been requested by {owner}. Take the necessary actions for the leave request. Should you have any additional information or updates, please feel free to communicate directly with the {owner}."
            subject_manager = f"Leave request has been requested by {owner}"

            self.send_email(
                subject_manager,
                content_manager,
                [reporting_manager],
                self.leave_request.id,
            )

            content_owner = f"This is to inform you that the leave request you created has been successfully logged into our system. The manager will now take the necessary actions to address leave request. Should you have any additional information or updates, please feel free to communicate directly with the {reporting_manager}."
            subject_owner = "Leave request created successfully"

            self.send_email(
                subject_owner, content_owner, [owner], self.leave_request.id
            )

        elif self.type == "approve":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            subject = "The Leave request has been successfully approved"
            content = f"This is to inform you that the leave request has been approved. If you have any questions or require further information, feel free to reach out to the {reporting_manager}."

            self.send_email(subject, content, [owner], self.leave_request.id)

        elif self.type == "reject":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            subject = "The Leave request has been rejected"
            content = f"This is to inform you that the leave request has been rejected. If you have any questions or require further information, feel free to reach out to the {reporting_manager}."

            self.send_email(subject, content, [owner], self.leave_request.id)

        elif self.type == "cancel":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            content_manager = f"This is to inform you that a leave request has been requested to cancel by {owner}. Take the necessary actions for the leave request. Should you have any additional information or updates, please feel free to communicate directly with the {owner}."
            subject_manager = f"Leave request cancellation"

            self.send_email(
                subject_manager,
                content_manager,
                [reporting_manager],
                self.leave_request.id,
            )

            content_owner = f"This is to inform you that a cancellation request created for your leave request has been successfully logged into our system. The manager will now take the necessary actions to address the leave request. Should you have any additional information or updates, please feel free to communicate directly with the {reporting_manager}."
            subject_owner = "Leave request cancellation requested"

            self.send_email(
                subject_owner, content_owner, [owner], self.leave_request.id
            )

        return


class LeaveClashThread(Thread):

    def __init__(self, leave_request):
        Thread.__init__(self)
        self.leave_request = leave_request

    def count_leave_clashes(self):
        from leave.models import LeaveRequest

        """
        Method to count leave clashes where this employee's leave request overlaps
        with other employees' requested dates.
        """
        overlapping_requests = LeaveRequest.objects.exclude(
            id=self.leave_request.id
        ).filter(
            Q(
                employee_id__employee_work_info__department_id=self.leave_request.employee_id.employee_work_info.department_id
            )
            | Q(
                employee_id__employee_work_info__job_position_id=self.leave_request.employee_id.employee_work_info.job_position_id
            ),
            start_date__lte=self.leave_request.end_date,
            end_date__gte=self.leave_request.start_date,
        )

        return overlapping_requests.count()

    def run(self) -> None:
        from leave.models import LeaveRequest

        super().run()
        dates = self.leave_request.requested_dates()
        leave_requests_to_update = LeaveRequest.objects.filter(
            Q(start_date__in=dates) | Q(end_date__in=dates)
        )

        for leave_request in leave_requests_to_update:
            leave_request.leave_clashes_count = self.count_leave_clashes()
            leave_request.save()
