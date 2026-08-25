"""
this page is handling the cbv methods of talent pool page
"""

from django.contrib import messages
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaFormView, HorillaListView
from recruitment.cbv_decorators import manager_can_enter
from recruitment.filters import SkillZoneCandidateFilter
from recruitment.forms import SkillZoneCandidateForm, SkillZoneCreateForm
from recruitment.models import Candidate, SkillZone, SkillZoneCandidate


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("recruitment.add_skillzone"), name="dispatch")
class SkillZoneFormView(HorillaFormView):
    """
    form view for create talent pool
    """

    form_class = SkillZoneCreateForm
    model = SkillZone
    new_display_title = _("Create Talent Pool")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Talent Pool")

        return context

    def form_valid(self, form: SkillZoneCreateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Talent Pool updated successfully.")
            else:
                message = _("Talent Pool created successfully")
            form.save()

            messages.success(self.request, _(message))
            return self.HttpResponse(script="$('.filterButton').first().click();")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter("recruitment.add_skillzonecandidate"), name="dispatch"
)
class SkillZoneCandidateFormView(HorillaFormView):
    """
    form view for create talent pool candidate
    """

    form_class = SkillZoneCandidateForm
    model = SkillZoneCandidate
    new_display_title = _("Add Candidate to Talent Pool")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id = self.kwargs.get("sz_id")
        self.form.fields["skill_zone_id"].initial = id
        if cand_id := self.request.GET.get("candidate"):
            self.form.fields["candidate_id"].queryset = self.form.fields[
                "candidate_id"
            ].queryset.filter(id=cand_id)

        # if self.form.instance.pk:
        #     self.form_class.verbose_name = _("Update Talent Pool")
        return context

    def form_valid(self, form: SkillZoneCandidateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Candidate updated successfully.")
            else:
                message = _("Candidate added successfully.")
            form.save(commit=True)
            messages.success(self.request, _(message))
            return self.HttpResponse(script="$('.filterButton').first().click();")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter("recruitment.add_skillzonecandidate"), name="dispatch"
)
class SkillZoneProfileListView(HorillaListView):
    """
    Talent Pool Candidate profile List View
    """

    model = SkillZoneCandidate
    filter_class = SkillZoneCandidateFilter
    show_filter_tags = False
    filter_selected = False
    bulk_select_option = False
    template_name = "skill_zone/candidate_profile_tab.html"
    show_toggle_form = False

    columns = [
        (_("Title"), "skill_zone_id__title"),
        "added_on",
        "reason",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fixed (not auto-random) so pagination/sort/search requests - which
        # all hx-target="#{{view_id}}" from generic/horilla_list_table.html -
        # can be recognized in get_template_names() below and answered with
        # just that fragment. Without this, every such request re-renders the
        # full tab (header + Add button included) and htmx's outerHTML swap
        # dumps that whole response in place of the table, duplicating the
        # header on each page/sort/search click.
        self.view_id = "skillZoneCandidateList"

    def get_template_names(self):
        if self.request.headers.get("HX-Target") == self.view_id:
            return ["generic/horilla_list_table.html"]
        return [self.template_name]

    def get_queryset(self):
        qureryset = super().get_queryset()
        cand_id = self.kwargs.get("pk")
        return qureryset.filter(candidate_id=cand_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["candidate"] = Candidate.objects.get(id=self.kwargs.get("pk"))
        return context
