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
            anou, attachment_ids = form.save(commit=False)
            anou.save()
            anou.attachments.set(attachment_ids)
            employees = form.cleaned_data["employees"]
            departments = form.cleaned_data["department"]
            job_positions = form.cleaned_data["job_position"]
            anou.department.set(departments)
            anou.job_position.set(job_positions)
            emp_dep = User.objects.filter(
                employee_get__employee_work_info__department_id__in=departments
            )
            emp_jobs = User.objects.filter(
                employee_get__employee_work_info__job_position_id__in=job_positions
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__department_id__in=departments
            )
            employees = employees | Employee.objects.filter(
                employee_work_info__job_position_id__in=job_positions
            )
            anou.employees.add(*employees)
            notify.send(
                self.request.user.employee_get,
                recipient=emp_dep,
                verb="Your department was mentioned in a post.",
                verb_ar="تم ذكر قسمك في منشور.",
                verb_de="Ihr Abteilung wurde in einem Beitrag erwähnt.",
                verb_es="Tu departamento fue mencionado en una publicación.",
                verb_fr="Votre département a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )
            notify.send(
                self.request.user.employee_get,
                recipient=emp_jobs,
                verb="Your job position was mentioned in a post.",
                verb_ar="تم ذكر وظيفتك في منشور.",
                verb_de="Ihre Arbeitsposition wurde in einem Beitrag erwähnt.",
                verb_es="Tu puesto de trabajo fue mencionado en una publicación.",
                verb_fr="Votre poste de travail a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )
            messages.success(self.request, message)
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)
