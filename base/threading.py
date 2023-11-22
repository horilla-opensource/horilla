from django.contrib import messages
from django.core.mail import send_mail
from threading import Thread
from django.conf import settings
from django.utils.translation import gettext as _
from django.template.loader import get_template



class MailSendThread(Thread):
    def __init__(self, request, leave_request,type):
        Thread.__init__(self)
        self.request = request
        self.leave_request = leave_request
        self.type = type

    def run(self):
        try:
            protocol = 'https' if self.request.is_secure() else 'http'
            send_to = self.leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id
            subject = _("**New leave request created**")
            url = f"{protocol}://{self.request.get_host()}/leave/request-view?id={self.leave_request.id}"

            if self.type == "request":
                body = _(f"A new leave request has been created for {self.leave_request.employee_id}. Click here to go to the leave request view: {url}")
                
            elif self.type == "approve":
                subject = _(f"**Leave Request Approved**")
                send_to = self.leave_request.employee_id.email
                url = f"{protocol}://{self.request.get_host()}/leave/user-request-view?id={self.leave_request.id}"
                body = _(f"Your leave request has been Approved by {self.request.user.employee_get.get_full_name()}. Click here to go to the leave request view: {url}")
                
            elif self.type == "reject":
                subject = _("**Leave Request Rejected**")
                send_to = self.leave_request.employee_id.email
                url = f"{protocol}://{self.request.get_host()}/leave/user-request-view?id={self.leave_request.id}"
                body = _(f"Your leave request has been Rejected by {self.request.user.employee_get.get_full_name()}. Click here to go to the leave request view: {url}")

            elif self.type == "cancel":
                subject = _("**New Cancellation Request**")
                body = _(f"A leave request needs to be cancelled for {self.leave_request.employee_id}. Click here to go to the leave request view: {url}")


            template_path = 'base/mail_templates/leave_request_template.html'
            html_template = get_template(template_path)

            context = {
                'subject': subject,
                'leave_request': self.leave_request,
                'url': url,
            }
            email_body = html_template.render(context)


            res = send_mail(
                subject, body, settings.EMAIL_HOST_USER, [send_to], fail_silently=False, html_message=email_body
            )                 
            if res==1:
                messages.success(self.request, _(f"Mail has been send to {self.leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id}"))
    
        except Exception as e:
            print(f"Could not send the mail to {send_to}. Error: {e}")