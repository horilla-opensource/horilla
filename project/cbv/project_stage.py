"""
This page handles the cbv methods for project stages
"""

import logging
from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaFormView

# from project.decorator import project_delete_permission
from project.forms import ProjectStageForm
from project.methods import you_dont_have_permission
from project.models import Project, ProjectStage

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
# @method_decorator(project_delete_permission, name="dispatch")
class ProjectStageCreateForm(HorillaFormView):
    """
    form view fro create and edit stages
    """

    form_class = ProjectStageForm
    model = ProjectStage
    new_display_title = _("Create Project Stage")

    def get(self, request, *args, pk=None, **kwargs):
        if request.GET.get("project_id"):
            project_id = request.GET.get("project_id")
        else:
            project_id = self.kwargs.get("project_id")
        stage_id = self.kwargs.get("pk")
        if project_id:
            try:
                if project_id:
                    project = Project.objects.filter(id=project_id).first()
                elif stage_id:
                    project = ProjectStage.objects.filter(id=stage_id).first().project
                if (
                    request.user.employee_get in project.managers.all()
                    or request.user.is_superuser
                ):
                    return super().get(request, *args, pk=pk, **kwargs)
                else:
                    return you_dont_have_permission(request)
            except Exception as e:
                logger.error(e)
                messages.error(request, _("Something went wrong!"))
                return HttpResponse("<script>window.location.reload()</script>")
        else:
            return super().get(request, *args, pk=pk, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get("project_id")
        if project_id:
            project = Project.objects.get(id=project_id)
            self.form.fields["project"].initial = project
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Project Stage")
        return context

    def form_valid(self, form: ProjectStageForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                project_id = self.form.cleaned_data["project"].id
                message = _(f"{self.form.instance} Updated")
            else:
                project_id = self.kwargs.get("project_id")
                message = _("New project stage created")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse(
                f"<span hx-get='/project/task-filter/{project_id}' hx-trigger='load' hx-target='#viewContainer'></span>"
            )
        return super().form_valid(form)


from django import forms


class StageDynamicCreateForm(ProjectStageCreateForm):
    """
    dynamic create form for stage
    """

    is_dynamic_create_view = True
    template_name = HorillaFormView.template_name

    def get_initial(self):
        initial = super().get_initial()
        project = self.request.GET.get("project")
        initial["project"] = project
        return initial

    def init_form(self, *args, data, files, instance=None, **kwargs):
        initial = self.get_initial()
        form = super().init_form(
            *args, data=data, files=files, instance=instance, initial=initial, **kwargs
        )
        if not initial.get("project"):
            form.fields["project"].widget = forms.Select(
                attrs={"class": "oh-select oh-select-2 w-100 oh-select2"}
            )
            form.fields["project"].queryset = Project.objects.all()

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.request.GET.get("project_id")
        if not project_id:
            project_id = self.request.GET.get("project")
        if project_id:
            project = Project.objects.get(id=project_id)
            self.form.fields["project"].initial = project
            self.form.fields["project"].choices = [(project.id, project.title)]
        return context

    def form_valid(self, form: ProjectStageForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _(f"{self.form.instance} Updated")
            else:
                message = _("New project stage created")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
