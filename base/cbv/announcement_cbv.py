"""
Announcement page
"""

from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import AnnouncementForm
from base.methods import closest_numbers
from base.models import Announcement, AnnouncementView
from employee.models import Employee
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
)
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

            employees = form.cleaned_data["employees"]
            departments = form.cleaned_data["department"]
            job_positions = form.cleaned_data["job_position"]
            company = form.cleaned_data.get(
                "company_id", [self.request.user.employee_get.get_company()]
            )

            if not (employees or departments or job_positions):
                employees = Employee.objects.filter(
                    employee_work_info__company_id__in=company, is_active=True
                )
                message = _(
                    f"Announcement created successfully to all employees in {', '.join(company.values_list('company', flat=True))}."
                )

            anou.save()
            anou.attachments.set(attachment_ids)
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


class AnnouncementDetailView(HorillaDetailedView):

    model = Announcement
    template_name = "announcement/announcement_one.html"

    def get_context_data(self, **kwargs):
        import ast

        context = super().get_context_data(**kwargs)
        instance_ids = ast.literal_eval(self.request.GET.get("instance_ids", "[]"))
        url_info = resolve(self.request.path)
        url_name = url_info.url_name
        key = next(iter(url_info.kwargs), "pk")

        if self.instance:
            announcement_view_obj, _ = AnnouncementView.objects.get_or_create(
                user=self.request.user, announcement=self.instance
            )
            announcement_view_obj.viewed = True
            announcement_view_obj.save()

        if instance_ids:
            prev_id, next_id = closest_numbers(instance_ids, self.instance.pk)

            context.update(
                {
                    "instance_ids": str(instance_ids),
                    "ids_key": self.ids_key,
                    "next_url": reverse(url_name, kwargs={key: next_id}),
                    "previous_url": reverse(url_name, kwargs={key: prev_id}),
                }
            )

            get_params = self.request.GET.copy()
            get_params.pop(self.ids_key, None)
            context["extra_query"] = get_params.urlencode()
        else:
            context["extra_query"] = ""

        return context
