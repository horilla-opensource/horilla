"""
This page handles the cbv methods for canidate profile page
"""

from django.utils.translation import gettext_lazy as _

from employee.cbv.employee_profile import EmployeeProfileView
from horilla import settings
from horilla_views.generic.cbv.views import HorillaProfileView
from recruitment.cbv.candidate_mail_log import CandidateMailLogTabList
from recruitment.filters import CandidateFilter
from recruitment.models import Candidate
from recruitment.views import views


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


CandidateProfileView.add_tab(
    tabs=[
        {"title": "About", "view": views.candidate_about_tab},
        {"title": "Resume", "view": views.candidate_resume_tab},
        {"title": "Survey", "view": views.candidate_survey_tab},
        {"title": "Documents", "view": views.candidate_document_request_tab},
        {"title": "Notes", "view": views.add_note},
        {"title": "History", "view": views.candidate_history_tab},
        {
            "title": "Rating",
            "view": views.candidate_rating_tab,
            "accessibility": "recruitment.cbv.accessibility.rating_accessibility",
        },
        {
            "title": "Onboarding",
            "view": views.candidate_onboarding_tab,
            "accessibility": "recruitment.cbv.accessibility.onboarding_accessibility",
        },
        {
            "title": "Mail Log",
            # "view": views.get_mail_log
            "view": CandidateMailLogTabList.as_view(),
        },
        {
            "title": "Sheduled Interviews",
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
