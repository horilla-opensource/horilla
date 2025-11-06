"""
Onboarding candidate view.
"""

from typing import Any

from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.models import HorillaMailTemplate
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from recruitment.filters import CandidateFilter
from recruitment.models import Candidate


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="candidate.view_candidate"), name="dispatch")
class OnboardingCandidatesView(TemplateView):
    """
    onboarding candidates view
    """

    template_name = "cbv/onboarding_candidates/onboarding_candidates.html"

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        hired_candidates = Candidate.objects.filter(
            is_active=True,
            hired=True,
            recruitment_id__closed=False,
        )
        mail_templates = HorillaMailTemplate.objects.all()
        context["mail_templates"] = mail_templates
        context["hired_candidates"] = hired_candidates
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="candidate.view_candidate"), name="dispatch")
class OnboardingCandidatesList(HorillaListView):
    """
    List view
    """

    bulk_update_fields = [
        "joining_date",
        "probation_end",
        "job_position_id",
        "recruitment_id",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("onboarding-candidates-list")

    def get_queryset(self):
        if not getattr(self, "queryset"):
            queryset = super().get_queryset()
            self.queryset = (
                queryset.filter(
                    is_active=True,
                    recruitment_id__closed=False,
                )
                .filter(Q(hired=True) | Q(stage_id__stage_type="hired"))
                .distinct()
            ).order_by("-id")

        return self.queryset

    model = Candidate
    filter_class = CandidateFilter

    columns = [
        ("Candidate", "name", "get_avatar"),
        ("Email", "last_email"),
        ("Date of joining", "date_of_joining"),
        ("Probation ends", "probation_date"),
        ("Job position", "job_position_id"),
        ("Recruitment", "recruitment_id"),
        ("Offer letter", "offer_letter"),
    ]
    header_attrs = {
        "action": "style='width: 350px;'",
    }

    action_method = "actions"

    row_status_indications = [
        (
            "joining--dot",
            _("Joining Set"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=joining_set]').val('true');
                $('[name=portal_sent]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "not-joining--dot",
            _("Joining Not-Set"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=joining_set]').val('false');
                $('[name=portal_sent]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "not-portal--dot",
            _("Portal Not-Sent"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=portal_sent]').val('false');
                $('[name=joining_set]').val('unknown').change();
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "portal--dot",
            _("Portal Send"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=portal_sent]').val('true');
                $('[name=joining_set]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    sortby_mapping = [
        ("Candidate", "name"),
        ("Email", "last_email"),
        ("Date of joining", "date_of_joining"),
        ("Job position", "job_position_id__job_position"),
        ("Recruitment", "recruitment_id__title"),
        ("Probation ends", "probation_date"),
    ]

    row_attrs = """
                onclick="window.location.href='{get_individual_url}'"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="candidate.view_candidate"), name="dispatch")
class OnboardingCandidatesNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("onboarding-candidates-list")
        self.create_attrs = f"""
                                href="{reverse_lazy('candidate-create')}?onboarding=True"
                                """
        self.filter_instance = CandidateFilter()

    nav_title = _("Hired Candidates")
    filter_body_template = "cbv/onboarding_candidates/filter.html"
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    group_by_fields = [
        ("recruitment_id", _("Recruitment")),
        ("job_position_id", _("Job position")),
        ("country", _("Country")),
        ("stage_id", _("Stage")),
        ("joining_date", _("Joining Date")),
        ("probation_end", _("Probation End")),
        ("offer_letter_status", _("Offer Letter Status")),
        ("rejected_candidate__reject_reason_id", _("Rejected Reason")),
        ("skillzonecandidate_set__skill_zone_id", _("Skill Zone")),
    ]

    actions = [
        {
            "action": _("Send Portal"),
            "attrs": """

                    data-target="#addAttachments"
                    data-toggle="oh-modal-toggle"
                    id="send-port"
                    """,
        }
    ]
