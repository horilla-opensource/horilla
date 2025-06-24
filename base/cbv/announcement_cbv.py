"""
Announcement page
"""

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import AnnouncementForm
from base.models import Announcement
from employee.models import Employee
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView
from notifications.signals import notify


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.add_announcement"), name="dispatch")
class AnnouncementFormView(HorillaFormView):
    """
    form view for create button
    """

    form_class = AnnouncementForm
    model = Announcement
    new_display_title = _("Create Announcements.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Edit Announcement.")

        return context

    def form_valid(self, form: AnnouncementForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Announcement updated successfully.")
            else:
                message = _("Announcement created successfully.")
            announcement, attachment_ids = form.save(commit=False)
            announcement.save()
            announcement.attachments.set(attachment_ids)

            employees = form.cleaned_data["employees"]
            departments = form.cleaned_data["department"]
            job_positions = form.cleaned_data["job_position"]
            company = form.cleaned_data["company_id"]

            announcement.department.set(departments)
            announcement.job_position.set(job_positions)
            announcement.company_id.set(company)

            dept_ids = departments.values_list("id", flat=True)
            job_ids = job_positions.values_list("id", flat=True)

            employees_from_dept = Employee.objects.filter(
                employee_work_info__department_id__in=dept_ids
            )
            employees_from_job = Employee.objects.filter(
                employee_work_info__job_position_id__in=job_ids
            )

            all_employees = (
                employees | employees_from_dept | employees_from_job
            ).distinct()
            announcement.employees.add(*all_employees)

            all_emps = employees_from_dept | employees_from_job | employees
            user_map = User.objects.filter(employee_get__in=all_emps).distinct()

            dept_emp_ids = set(employees_from_dept.values_list("id", flat=True))
            job_emp_ids = set(employees_from_job.values_list("id", flat=True))
            direct_emp_ids = set(employees.values_list("id", flat=True))

            notified_ids = dept_emp_ids.union(job_emp_ids)
            direct_only_ids = direct_emp_ids - notified_ids

            sender = self.request.user.employee_get

            def send_notification(users, verb):
                if users.exists():
                    notify.send(
                        sender,
                        recipient=users,
                        verb=verb,
                        verb_ar="لقد تم ذكرك في إعلان.",
                        verb_de="Sie wurden in einer Ankündigung erwähnt.",
                        verb_es="Has sido mencionado en un anuncio.",
                        verb_fr="Vous avez été mentionné dans une annonce.",
                        redirect="/",
                        icon="chatbox-ellipses",
                    )

            send_notification(
                user_map.filter(employee_get__id__in=dept_emp_ids),
                _("Your department was mentioned in an announcement."),
            )
            send_notification(
                user_map.filter(employee_get__id__in=job_emp_ids),
                _("Your job position was mentioned in an announcement."),
            )
            send_notification(
                user_map.filter(employee_get__id__in=direct_only_ids),
                _("You have been mentioned in an announcement."),
            )
            messages.success(self.request, message)
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)
