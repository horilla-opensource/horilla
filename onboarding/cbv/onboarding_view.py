"""
This page handles the cbv methods for onboarding view
"""

import contextlib
from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaDetailedView, HorillaFormView
from notifications.signals import notify
from onboarding.cbv_decorators import (
    recruitment_manager_can_enter,
    stage_manager_can_enter,
)
from onboarding.forms import (
    OnboardingTaskForm,
    OnboardingViewStageForm,
    OnboardingViewTaskForm,
)
from onboarding.models import CandidateTask, OnboardingStage, OnboardingTask
from recruitment.models import Candidate


@method_decorator(login_required, name="dispatch")
@method_decorator(
    recruitment_manager_can_enter("onboarding.add_onboardingstage"), name="dispatch"
)
class StageCreateForm(HorillaFormView):
    """
    Form view for create and update stage
    """

    form_class = OnboardingViewStageForm
    model = OnboardingStage
    new_display_title = _("Create Stage")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj_id = self.kwargs.get("obj_id")
        self.form.fields["recruitment_id"].widget = forms.HiddenInput()
        self.form.fields["recruitment_id"].initial = obj_id
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Stage")
        return context

    def form_valid(self, form: OnboardingViewStageForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Stage Updated Successfully")
            else:
                message = _("New stage created successfully")
            stage = form.save()
            stage.employee_id.set(
                Employee.objects.filter(id__in=form.data.getlist("employee_id"))
            )
            users = [employee.employee_user_id for employee in stage.employee_id.all()]
            messages.success(self.request, _(message))
            with contextlib.suppress(Exception):
                notify.send(
                    self.request.user.employee_get,
                    recipient=users,
                    verb="You are chosen as onboarding stage manager",
                    verb_ar="لقد تم اختيارك كمدير مرحلة التدريب.",
                    verb_de="Sie wurden als Onboarding-Stage-Manager ausgewählt.",
                    verb_es="Ha sido seleccionado/a como responsable de etapa de incorporación.",
                    verb_fr="Vous avez été choisi(e) en tant que responsable de l'étape d'intégration.",
                    icon="people-circle",
                    redirect=reverse("onboarding-view"),
                )

            return self.HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    stage_manager_can_enter("onboarding.add_onboardingtask"), name="dispatch"
)
class TaskCreateForm(HorillaFormView):
    """
    form view for create tasks
    """

    model = CandidateTask
    form_class = OnboardingViewTaskForm
    new_display_title = _("Create Task")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form.fields["stage_id"].widget = forms.HiddenInput()

        obj_id = self.kwargs.get("obj_id")
        stage = OnboardingStage.objects.get(id=obj_id)
        self.form.fields["stage_id"].initial = obj_id

        candidate_ids = stage.candidate.all().values_list("candidate_id", flat=True)
        cand_queryset = Candidate.objects.filter(id__in=candidate_ids)
        self.form.fields["candidates"].queryset = cand_queryset
        self.form.fields["candidates"].initial = cand_queryset

        context["form"] = self.form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:

        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Request")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: OnboardingTaskForm) -> HttpResponse:
        if form.is_valid():
            message = _("New Task Created Successfully")
            candidates = self.form.cleaned_data["candidates"]
            stage_id = self.form.cleaned_data["stage_id"]
            managers = self.request.POST.getlist("managers")
            title = self.form.cleaned_data["task_title"]
            onboarding_task = OnboardingTask(task_title=title, stage_id=stage_id)
            onboarding_task.save()
            onboarding_task.employee_id.set(managers)
            onboarding_task.candidates.set(candidates)
            if candidates:
                for cand in candidates:
                    task = CandidateTask(
                        candidate_id=cand,
                        stage_id=stage_id,
                        onboarding_task_id=onboarding_task,
                    )
                    task.save()
            users = [
                manager.employee_user_id
                for manager in onboarding_task.employee_id.all()
            ]
            notify.send(
                self.request.user.employee_get,
                recipient=users,
                verb="You are chosen as an onboarding task manager",
                verb_ar="لقد تم اختيارك كمدير مهام التدريب.",
                verb_de="Sie wurden als Onboarding-Aufgabenmanager ausgewählt.",
                verb_es="Ha sido seleccionado/a como responsable de tareas de incorporación.",
                verb_fr="Vous avez été choisi(e) en tant que responsable des tâches d'intégration.",
                icon="people-circle",
                redirect=reverse("onboarding-view"),
            )
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    stage_manager_can_enter("onboarding.change_onboardingtask"), name="dispatch"
)
class TaskUpdateFormView(HorillaFormView):
    """
    form view for update tasks
    """

    model = OnboardingTask
    form_class = OnboardingTaskForm
    new_display_title = _("Update Task")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.form.fields["stage_id"].widget = forms.HiddenInput()
        context["form"] = self.form
        # onboarding_task = OnboardingTask.objects.get(id=self.form.instance.pk)
        return context

    def form_valid(self, form: OnboardingTaskForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                onboarding_task = OnboardingTask.objects.get(id=self.form.instance.pk)
                task = form.save()
                task.employee_id.set(
                    Employee.objects.filter(id__in=form.data.getlist("employee_id"))
                )
                for cand_task in onboarding_task.candidatetask_set.all():
                    if cand_task.candidate_id not in task.candidates.all():
                        cand_task.delete()
                    else:
                        cand_task.stage_id = task.stage_id
                messages.success(self.request, _("Task updated successfully.."))
                users = [
                    employee.employee_user_id for employee in task.employee_id.all()
                ]
                notify.send(
                    self.request.user.employee_get,
                    recipient=users,
                    verb="You are chosen as an onboarding task manager",
                    verb_ar="لقد تم اختيارك كمدير مهام التدريب.",
                    verb_de="Sie wurden als Onboarding-Aufgabenmanager ausgewählt.",
                    verb_es="Ha sido seleccionado/a como responsable de tareas de incorporación.",
                    verb_fr="Vous avez été choisi(e) en tant que responsable des tâches d'intégration.",
                    icon="people-circle",
                    redirect=reverse("onboarding-view"),
                )

            form.save()
            return self.HttpResponse()
        return super().form_valid(form)


class OnboardingCandidateDetailView(HorillaDetailedView):
    """
    detail view of onboarding view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.body = [
            (_("Job Position"), "get_job_position"),
            (_("Contact"), "mobile"),
            (_("Joining Date"), "joining_date"),
            (_("Onboarding Portal Stage"), "onboarding_portal_html"),
            (_("Status"), "onboarding_status_col"),
            (_("Tasks"), "onboarding_task_col"),
        ]

    template_name = "cbv/onboarding_view/detail_view.html"

    model = Candidate
    title = _("Details")
    header = {
        "title": "name",
        "subtitle": "email",
        "avatar": "get_avatar",
    }

    cols = {"onboarding_task_col": 12}

    actions = [
        {
            "action": "View",
            "icon": "eye-outline",
            "attrs": """
                     class="oh-btn oh-btn--light w-50"
                     href="{get_individual_url}"
                     """,
        },
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
                    class="oh-btn oh-btn--info w-50"
                    href ="{get_update_url}"
                    """,
        },
    ]
