"""
This page handles the cbv methods for recruitment survey page
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaDetailedView, HorillaFormView
from recruitment.forms import QuestionForm, TemplateForm
from recruitment.models import RecruitmentSurvey, SurveyTemplate


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.add_recruitmentsurvey"), name="dispatch"
)
class QuestionFormView(HorillaFormView):
    """
    form view for create button
    """

    form_class = QuestionForm
    model = RecruitmentSurvey
    new_display_title = _("Survey Questions")
    template_name = "cbv/recruitment_survey/survey_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Survey Questions")
        return context

    def form_valid(self, form: QuestionForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Survey question updated.")
            else:
                message = _("New survey question created.")
            instance = form.save(commit=False)
            instance.save()
            instance.recruitment_ids.set(form.recruitment)
            instance.template_id.set(form.cleaned_data["template_id"])
            messages.success(self.request, _(message))
            return HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.add_recruitmentsurvey"), name="dispatch"
)
class QuestionDuplicateFormView(HorillaFormView):
    """
    form view for create duplicate for asset
    """

    form_class = QuestionForm
    model = RecruitmentSurvey
    new_display_title = _("Duplicate Survey Questions")
    template_name = "cbv/recruitment_survey/survey_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        original_object = RecruitmentSurvey.objects.get(id=self.kwargs["obj_id"])
        form = self.form_class(instance=original_object)
        for field_name, field in form.fields.items():
            if isinstance(field, forms.CharField):
                if field.initial:
                    initial_value = field.initial
                else:
                    initial_value = f"{form.initial.get(field_name, '')} (copy)"
                form.initial[field_name] = initial_value
                form.fields[field_name].initial = initial_value
        context["form"] = form
        self.form_class.verbose_name = _("Duplicate")
        return context

    def form_valid(self, form: QuestionForm) -> HttpResponse:
        if form.is_valid():
            message = _("New survey question created.")
            instance = form.save(commit=False)
            instance.save()
            instance.recruitment_ids.set(form.recruitment)
            instance.template_id.set(form.cleaned_data["template_id"])
            messages.success(self.request, _(message))
            return HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.add_surveytemplate"), name="dispatch"
)
class SurveyTemplateFormView(HorillaFormView):
    """
    form view for create and edit survey templates
    """

    form_class = TemplateForm
    model = SurveyTemplate

    def get_form(self, form_class=None):
        title = self.request.GET.get("title")
        instance = SurveyTemplate.objects.filter(title=title).first()

        if not self.request.POST:
            self.form = self.form_class(instance=instance)
        else:
            self.form = self.form_class(self.request.POST, instance=instance)
        return self.form

    def form_invalid(self, form: Any) -> HttpResponse:
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: TemplateForm) -> HttpResponse:
        if form.is_valid():
            message = _("Template saved")
            form.save()
            messages.success(self.request, _(message))
            return HttpResponse("<script>window.location.reload();</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.add_surveytemplate"), name="dispatch"
)
class RecruitmentSurveyDetailView(HorillaDetailedView):
    """
    detail view of the page
    """

    model = RecruitmentSurvey
    title = _("Details")
    body = [
        (_("Question"), "question"),
        (_("Question Type"), "get_question_type"),
        (_("Sequence"), "sequence"),
        (_("Recruitment"), "recruitment_col"),
        (_("Options"), "options_col", True),
    ]

    header = {"title": "question", "subtitle": "", "avatar": ""}

    cols = {"question": 12}

    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
                     class="oh-btn oh-btn--info w-50"
                     hx-get="{get_edit_url}"
                     hx-target ="#genericModalBody"
                     data-target = "#genericModal"
                     data-toggle ="oh-modal-toggle"
                     """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger w-50"
                    href ="{get_delete_url}"
                    onclick="return confirm(' Are you sure want to delete?')"
                    """,
        },
    ]
