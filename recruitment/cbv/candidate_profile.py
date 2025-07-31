"""
This page handles the cbv methods for canidate profile page
"""

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.cbv.employee_profile import EmployeeProfileView
from horilla import settings
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView, HorillaProfileView
from onboarding.filters import CandidateTaskFilter
from onboarding.models import CandidateTask
from recruitment.cbv.candidate_mail_log import CandidateMailLogTabList
from recruitment.cbv_decorators import all_manager_can_enter
from recruitment.filters import CandidateFilter
from recruitment.models import Candidate
from recruitment.views import views


@method_decorator(login_required, name="dispatch")
@method_decorator(
    all_manager_can_enter(perm="recruitment.view_candidate"), name="dispatch"
)
class CandidateProfileView(HorillaProfileView):
    """
    Candidate ProfileView
    """

    model = Candidate
    filter_class = CandidateFilter
    push_url = "candidate-view-individual"
    key_name = "cand_id"

    actions = [
        {
            "title": _("Edit"),
            "src": f"/{settings.STATIC_URL}images/ui/edit_btn.png",
            "attrs": """
                        onclick="
                        window.location.href='{get_update_url}' "
                    """,
        },
        {
            "title": _("View candidate self tracking"),
            "src": f"/{settings.STATIC_URL}images/ui/exit-outline.svg",
            "accessibility": "recruitment.cbv.accessibility.view_candidate_self_tracking",
            "attrs": """
                href="{get_self_tracking_url}"
                class="oh-dropdown__link"
            """,
        },
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(
    all_manager_can_enter(perm="recruitment.view_candidate"), name="dispatch"
)
class CandidateProfileTasks(HorillaListView):
    """
    CandidateProfileTasks
    """

    custom_empty_template = "onboarding/empty_task.html"
    model = CandidateTask
    show_filter_tags = False
    filter_class = CandidateTaskFilter
    filter_selected = False
    selected_instances_key_id = "selectedInstanceIds"
    bulk_update_fields = [
        "status",
    ]

    def bulk_update_accessibility(self):
        return (
            super().bulk_update_accessibility()
            or self.request.user.employee_get.onboardingstage_set.filter(
                candidate__candidate_id__pk=self.kwargs["pk"]
            ).exists()
        )

    columns = [
        ("Task", "onboarding_task_id__task_title"),
        ("Status", "status_col"),
        (
            "Modified By",
            "modified_by__employee_get__get_full_name",
            "modified_by__employee_get__get_avatar",
        ),
    ]

    header_attrs = {
        "status_col": """
        style="width:180px!important;"
"""
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = self.request.path

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        self.queryset = (
            super()
            .get_queryset(queryset, filtered, *args, **kwargs)
            .filter(candidate_id__pk=self.kwargs["pk"])
        )
        return self.queryset


CandidateProfileView.add_tab(
    tabs=[
        {
            "title": "About",
            "view": views.candidate_about_tab,
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "Resume",
            "view": views.candidate_resume_tab,
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "Survey",
            "view": views.candidate_survey_tab,
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "Documents",
            "view": views.candidate_document_request_tab,
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "Notes",
            "view": views.add_note,
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "History",
            "view": views.candidate_history_tab,
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "Rating",
            "view": views.candidate_rating_tab,
            "accessibility": "recruitment.cbv.accessibility.rating_accessibility",
        },
        {
            "title": "Onboarding",
            "view": CandidateProfileTasks.as_view(),
            "accessibility": "recruitment.cbv.accessibility.onboarding_accessibility",
        },
        {
            "title": "Mail Log",
            # "view": views.get_mail_log
            "view": CandidateMailLogTabList.as_view(),
            "accessibility": "recruitment.cbv.accessibility.if_manager_accessibility",
        },
        {
            "title": "Scheduled Interviews",
            "view": views.candidate_interview_tab,
            "accessibility": "recruitment.cbv.accessibility.empl_scheduled_interview_accessibility",
        },
    ]
)


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "Scheduled Interviews",
            "view": views.scheduled_interview_tab,
            "accessibility": "recruitment.cbv.accessibility.empl_scheduled_interview_accessibility",
        },
    ]
)
