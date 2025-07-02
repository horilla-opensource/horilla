"""
Question Template page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.decorators import manager_can_enter
from base.methods import is_reportingmanager
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from pms.filters import QuestionTemplateFilter
from pms.forms import QuestionTemplateForm
from pms.models import QuestionTemplate


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_questiontemplate"), name="dispatch")
class QuestionTemplateView(TemplateView):
    """
    for question template page
    """

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context["form"] = QuestionTemplateForm
        return context

    template_name = "cbv/question_template/question_template.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_questiontemplate"), name="dispatch")
class QuestionTemplateList(HorillaListView):
    """
    List view of the question template page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("question-template-hx-view")
        self.action_method = "action_col"
        self.view_id = "questionTemplateList"

    model = QuestionTemplate
    filter_class = QuestionTemplateFilter

    columns = [
        (_("Title"), "question_template", "get_avatar"),
        (_("Total Questions"), "question_count"),
    ]

    header_attrs = {
        "action": """
                    style="width:250px !important"
                   """
    }

    sortby_mapping = [
        ("Total Questions", "question_count"),
    ]

    row_attrs = """
                onclick="window.location.href='{get_detail_url}'"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.view_questiontemplate"), name="dispatch")
class QuestionTemplateNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("question-template-hx-view")
        if self.request.user.has_perm(
            "pms.add_questiontemplate"
        ) or is_reportingmanager(self.request):
            self.create_attrs = f"""
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('question-template-creation')}"
                            """

    nav_title = _("Question Template")
    filter_instance = QuestionTemplateFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("pms.add_questiontemplate"), name="dispatch")
class QuestionTemplateFormView(HorillaFormView):
    """
    Form view
    """

    model = QuestionTemplate
    form_class = QuestionTemplateForm

    new_display_title = _("Add Question Template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Edit Question Template")
        return context

    def form_valid(self, form: QuestionTemplateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Question Template Updated Successfully")
                form.save()
                messages.success(self.request, _(message))
                return self.HttpResponse()
            else:
                message = _("Question Template Created Successfully")
                form.save()
                messages.success(self.request, _(message))
                detail_url = form.instance.get_detail_url()
                return self.HttpResponse(
                    f'<script>window.location.href="{detail_url}"</script>'
                )
        return super().form_valid(form)
