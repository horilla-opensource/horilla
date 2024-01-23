from django.core.mail import EmailMessage
from django.contrib import messages
from django.core.mail import send_mail
from threading import Thread
from django.conf import settings
from django.utils.translation import gettext as _
from django.template.loader import render_to_string
from django.template.loader import get_template
from employee.models import EmployeeWorkInformation
from horilla.settings import EMAIL_HOST_USER


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
        if leave_request_id != "#":
            link = int(leave_request_id)
        for recipient in recipients:
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

            email = EmailMessage(subject, html_message, EMAIL_HOST_USER, [recipient.email])
            email.content_subtype = "html"
            try:
                email.send()
            except:
                messages.error(self.request, f"Mail not sent to {recipient.get_full_name()}")

    def run(self) -> None:
        super().run()
        if self.type == "request":
            owner = self.leave_request.employee_id
            reporting_manager = self.leave_request.employee_id.get_reporting_manager()

            content_manager = f"This is to inform you that a leave request has been requested by {owner}. Take the necessary actions for the leave request. Should you have any additional information or updates, please feel free to communicate directly with the {owner}."
            subject_manager = f"Leave request has been requested by {owner}"
            
            self.send_email(subject_manager, content_manager, [reporting_manager], self.leave_request.id)

            content_owner = f"This is to inform you that the leave request you created has been successfully logged into our system. The manager will now take the necessary actions to address leave request. Should you have any additional information or updates, please feel free to communicate directly with the {reporting_manager}."
            subject_owner = "Leave request created successfully"

            self.send_email(subject_owner, content_owner, [owner], self.leave_request.id)

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
            
            self.send_email(subject_manager, content_manager, [reporting_manager], self.leave_request.id)

            content_owner = f"This is to inform you that a cancellation request created for your leave request has been successfully logged into our system. The manager will now take the necessary actions to address the leave request. Should you have any additional information or updates, please feel free to communicate directly with the {reporting_manager}."
            subject_owner = "Leave request cancellation requested"

            self.send_email(subject_owner, content_owner, [owner], self.leave_request.id)
            
        return