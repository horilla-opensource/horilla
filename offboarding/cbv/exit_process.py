"""
This page handles the cbv methods for existing process
"""

from datetime import datetime, timedelta

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.context_processors import intial_notice_period
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaDetailedView, HorillaFormView
from notifications.signals import notify
from offboarding.cbv_decorators import (
    any_manager_can_enter,
    offboarding_manager_can_enter,
    offboarding_or_stage_manager_can_enter,
)
from offboarding.forms import (
    OffboardingEmployeeForm,
    OffboardingForm,
    OffboardingStageForm,
    TaskForm,
)
from offboarding.models import (
    Offboarding,
    OffboardingEmployee,
    OffboardingStage,
    OffboardingTask,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    offboarding_manager_can_enter("offboarding.add_offboardingstage"), name="dispatch"
)
class OffboardingStageFormView(HorillaFormView):
    """
    form view for create button
    """

    form_class = OffboardingStageForm
    model = OffboardingStage
    new_display_title = _("Create Offboarding Stage")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offboarding_id = self.request.GET["offboarding_id"]
        self.form.fields["offboarding_id"].initial = offboarding_id
        self.form.fields["offboarding_id"].widget = forms.HiddenInput()
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Offboarding Stage")
        return context

    def form_valid(self, form: OffboardingStageForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Offboarding Stage Updated Successfully")
            else:
                message = _("Offboarding Stage Created Successfully")
            form.save()

            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload</script>")
        return super().form_valid(form)


@method_decorator(
    any_manager_can_enter("offboarding.add_offboardingemployee"), name="dispatch"
)
class OffboardingStageAddEmployeeForm(HorillaFormView):
    """
    form view for create button
    """

    form_class = OffboardingEmployeeForm
    model = OffboardingEmployee
    new_display_title = _("Add Employee")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        default_notice_period = (
            intial_notice_period(self.request)["get_initial_notice_period"]
            if intial_notice_period(self.request)["get_initial_notice_period"]
            else 0
        )
        end_date = datetime.today() + timedelta(days=default_notice_period)
        stage_id = self.request.GET["stage_id"]
        self.form.fields["stage_id"].initial = stage_id
        self.form.fields["notice_period_ends"].initial = end_date
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Employee")
        return context

    def form_valid(self, form: OffboardingEmployeeForm) -> HttpResponse:
        stage_id = self.request.GET["stage_id"]
        stage = OffboardingStage.objects.get(id=stage_id)
        if form.is_valid():
            if form.instance.pk:
                message = _("Updated Employee")
            else:
                message = _("Added Employee")
                instance = form.save()
                notify.send(
                    self.request.user.employee_get,
                    recipient=instance.employee_id.employee_user_id,
                    verb=f"You have been added to the {stage} of {stage.offboarding_id}",
                    verb_ar=f"لقد تمت إضافتك إلى {stage} من {stage.offboarding_id}",
                    verb_de=f"Du wurdest zu {stage} von {stage.offboarding_id} hinzugefügt",
                    verb_es=f"Has sido añadido a {stage} de {stage.offboarding_id}",
                    verb_fr=f"Vous avez été ajouté à {stage} de {stage.offboarding_id}",
                    redirect=reverse("offboarding-pipeline"),
                    icon="information",
                )
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload</script>")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("offboarding.add_offboarding"), name="dispatch")
class OffboardingCreateFormView(HorillaFormView):
    """
    form view for create and edit offboarding
    """

    form_class = OffboardingForm
    model = Offboarding
    new_display_title = _("Create Offboarding")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Offboarding")

        return context

    def form_valid(self, form: OffboardingForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Offboarding Updated")
            else:
                message = _("Offboarding saved")
            form.save()

            messages.success(self.request, message)
            return HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    offboarding_or_stage_manager_can_enter("offboarding.add_offboardingtask"),
    name="dispatch",
)
class OffboardingTaskFormView(HorillaFormView):
    """
    form view for create and edit offboarding tasks
    """

    model = OffboardingTask
    form_class = TaskForm
    new_display_title = _("Create Task")

    def get_initial(self) -> dict:
        initial = super().get_initial()
        stage_id = self.request.GET.get("stage_id")
        employees = OffboardingEmployee.objects.filter(stage_id=stage_id)
        if stage_id:
            initial["stage_id"] = stage_id
            initial["tasks_to"] = employees
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stage_id = self.request.GET.get("stage_id")
        employees = OffboardingEmployee.objects.filter(stage_id=stage_id)
        if self.form.instance.pk:
            self.form.fields["stage_id"].initial = stage_id
            self.form.fields["tasks_to"].initial = employees
            self.form.fields["tasks_to"].queryset = employees

            self.form_class.verbose_name = _("Update Task")

        return context

    def form_valid(self, form: TaskForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Task Updated")
            else:
                message = _("Task Added")
            form.save()

            messages.success(self.request, message)
            return HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


class ExitProcessDetailView(HorillaDetailedView):
    """
    detail view
    """

    model = OffboardingEmployee
    title = _("Details")
    header = {
        "title": "employee_id__get_full_name",
        "subtitle": "detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }
    body = [
        (_("Email"), "employee_id__employee_work_info__email"),
        (_("Job Position"), "employee_id__employee_work_info__job_position_id"),
        (_("Contact"), "employee_id__phone"),
        (_("Notice Period start Date"), "notice_period_starts"),
        (_("Notice Period end Date"), "notice_period_ends"),
        (_("Stage"), "detail_view_stage_custom"),
    ]
