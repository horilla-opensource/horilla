"""
mail.py

This module is used handle mail sent in thread
"""

import logging
from threading import Thread

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from base.backends import ConfiguredEmailBackend
from employee.models import EmployeeWorkInformation
from payroll.models.models import Payslip
from payroll.views.views import payslip_pdf

logger = logging.getLogger(__name__)


class MailSendThread(Thread):
    """
    MailSend
    """

    def __init__(self, request, result_dict, ids):
        Thread.__init__(self)
        self.result_dict = result_dict
        self.ids = ids
        self.request = request
        self.host = request.get_host()
        self.protocol = "https" if request.is_secure() else "http"

    def run(self) -> None:
        super().run()
        for record in list(self.result_dict.values()):
            html_message = render_to_string(
                "payroll/mail_templates/default.html",
                {
                    "record": record,
                    "host": self.host,
                    "protocol": self.protocol,
                },
            )
            attachments = []
            for instance in record["instances"]:
                response = payslip_pdf(self.request, instance.id)
                attachments.append(
                    (
                        f"{instance.get_payslip_title()}.pdf",
                        response.content,
                        "application/pdf",
                    )
                )
            employee = record["instances"][0].employee_id
            email_backend = ConfiguredEmailBackend()
            email = EmailMessage(
                f"Hello, {record['instances'][0].get_name()} Your Payslips is Ready!",
                html_message,
                email_backend.dynamic_from_email_with_display_name,
                [employee.get_mail()],
                # reply_to=["another@example.com"],
                # headers={"Message-ID": "foo"},
            )
            email.attachments = attachments

            # Send the email
            email.content_subtype = "html"
            try:
                email.send()
                Payslip.objects.filter(id__in=self.ids).update(sent_to_employee=True)
            except Exception as e:
                logger.exception(e)
                pass
        return
