"""
this page is handling the cbv methods of skill zone page
"""

from django.contrib import messages
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaFormView
from recruitment.cbv_decorators import manager_can_enter
from recruitment.forms import SkillZoneCandidateForm, SkillZoneCreateForm
from recruitment.models import SkillZone, SkillZoneCandidate


@method_decorator(login_required, name="dispatch")
@method_decorator(manager_can_enter("recruitment.add_skillzone"), name="dispatch")
class SkillZoneFormView(HorillaFormView):
    """
    form view for create skill zone
    """

    form_class = SkillZoneCreateForm
    model = SkillZone
    new_display_title = _("Create Skill Zone")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Skill Zone")

        return context

    def form_valid(self, form: SkillZoneCreateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Skill Zone updated successfully.")
            else:
                message = _("Skill Zone created successfully")
            form.save()

            messages.success(self.request, _(message))
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter("recruitment.add_skillzonecandidate"), name="dispatch"
)
class SkillZoneCandidateFormView(HorillaFormView):
    """
    form view for create skill zone candidate
    """

    form_class = SkillZoneCandidateForm
    model = SkillZoneCandidate
    new_display_title = _("Add Candidate to  skill zone")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id = self.kwargs.get("sz_id")
        self.form.fields["skill_zone_id"].initial = id
        # if self.form.instance.pk:
        #     self.form_class.verbose_name = _("Update Skill Zone")
        return context

    def form_valid(self, form: SkillZoneCandidateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Candidate updated successfully.")
            else:
                message = _("Candidate added successfully.")
            form.save(commit=True)
            messages.success(self.request, _(message))
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)
