"""
recruitment/cbv/pipeline.py
"""

from typing import Any

from django.contrib import messages
from django.core.cache import cache as CACHE
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
    get_short_uuid,
)
from recruitment import filters, forms, models
from recruitment.cbv_decorators import manager_can_enter
from recruitment.templatetags.recruitmentfilters import (
    recruitment_manages,
    stage_manages,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class PipelineView(TemplateView):
    """
    PipelineView
    """

    template_name = "cbv/pipeline/pipeline.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class RecruitmentTabView(HorillaTabView):
    """
    RecruitmentTabView
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        recruitments = filters.RecruitmentFilter(self.request.GET).qs.filter(
            is_active=True
        )
        CACHE.set(
            self.request.session.session_key + "pipeline",
            {
                "stages": filters.StageFilter(self.request.GET).qs.order_by("sequence"),
                "recruitments": recruitments,
                "candidates": False,
            },
        )
        self.tabs = []
        view_perm = self.request.user.has_perm("recruitment.view_recruitment")
        change_perm = self.request.user.has_perm("recruitment.change_recruitment")
        add_cand_perm = self.request.user.has_perm("recruitment.add_candidate")
        delete_perm = self.request.user.has_perm("recruitment.delete_recruitment")
        add_stage_perm = self.request.user.has_perm("recruitment.add_stage")
        for rec in recruitments:
            rec_manager_perm = recruitment_manages(self.request.user, rec)
            stage_manage_perm = stage_manages(self.request.user, rec)
            tab = {}
            tab["title"] = rec
            tab["url"] = reverse("get-stages-recruitment", kwargs={"rec_id": rec.pk})
            tab["badge_label"] = _("Stages")
            tab["actions"] = []
            if rec_manager_perm:
                if add_stage_perm:
                    tab["actions"].append(
                        {
                            "action": _("Add Stage"),
                            "attrs": f"""
                                        data-toggle="oh-modal-toggle"
                                        data-target="#genericModal"
                                        hx-get="{reverse('rec-stage-create')}?recruitment_id={rec.pk}"
                                        hx-target="#genericModalBody"
                                        style="cursor: pointer;"
                                        """,
                        },
                    )

                if change_perm:
                    tab["actions"].append(
                        {
                            "action": _("Edit"),
                            "attrs": f"""
                                    data-toggle="oh-modal-toggle"
                                    data-target="#genericModal"
                                    hx-get="{reverse("recruitment-update-pipeline", kwargs={"pk": rec.pk})}"
                                    hx-target="#genericModalBody"
                                    style="cursor: pointer;"
                                    """,
                        },
                    )

                if add_cand_perm:
                    tab["actions"].append(
                        {
                            "action": _("Resume Shortlisting"),
                            "attrs": f"""
                                    data-toggle="oh-modal-toggle"
                                    data-target="#bulkResumeUpload"
                                    hx-get="{reverse('view-bulk-resume')}?rec_id={rec.pk}"
                                    hx-target="#bulkResumeUploadBody"
                                    style="cursor: pointer;"
                                    """,
                        },
                    )

                if change_perm:
                    if rec.closed:
                        tab["actions"].append(
                            {
                                "action": _("Reopen"),
                                "attrs": f"""
                                            href="{reverse("recruitment-reopen-pipeline", kwargs={"rec_id": rec.pk})}"
                                            style="cursor: pointer;"
                                            onclick="return confirm('Are you sure you want to reopen this recruitment?');"
                                            """,
                            },
                        )
                    else:
                        tab["actions"].append(
                            {
                                "action": _("Close"),
                                "attrs": f"""
                                        href="{reverse("recruitment-close-pipeline", kwargs={"rec_id": rec.pk})}"
                                        style="cursor: pointer;"
                                        onclick="return confirm('Are you sure you want to close this recruitment?');"
                                        """,
                            },
                        )
                if delete_perm:
                    tab["actions"].append(
                        {
                            "action": _("Delete"),
                            "attrs": f"""
                                        data-toggle="oh-modal-toggle"
                                        data-target="#deleteConfirmation"
                                        hx-get="{reverse('generic-delete')}?model=recruitment.Recruitment&pk={rec.pk}"
                                        hx-target="#deleteConfirmationBody"
                                        style="cursor: pointer;"
                                        """,
                        }
                    )
            if stage_manage_perm or view_perm:
                self.tabs.append(tab)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class GetStages(TemplateView):
    """
    GetStages
    """

    template_name = "cbv/pipeline/stages.html"
    stages = None

    def get(self, request, rec_id, *args, **kwargs):
        """
        get method
        """
        cache = CACHE.get(request.session.session_key + "pipeline")
        if not cache.get("candidates"):
            cache["candidates"] = filters.CandidateFilter(self.request.GET).qs.filter(
                is_active=True
            )
            CACHE.set(request.session.session_key + "pipeline", cache)

        self.stages = cache["stages"].filter(recruitment_id=rec_id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stages"] = self.stages
        context["view_id"] = get_short_uuid(6, "hsv")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class CandidateList(HorillaListView):
    """
    CandidateList
    """

    model = models.Candidate
    filter_class = filters.CandidateFilter
    filter_selected = False
    quick_export = False
    next_prev = False
    custom_empty_template = "cbv/pipeline/empty.html"
    header_attrs = {
        "action": """
        style="width:413px;"
""",
        "mobile": """
        style="width:100px;"
""",
        "Stage": """
        style="width:100px;"
""",
        "get_interview_count": """
        style="width:200px;"
""",
    }
    columns = [
        ("Name", "candidate_name", "get_avatar"),
        ("Email", "mail_indication"),
        ("Stage", "stage_drop_down"),
        ("Rating", "rating_bar"),
        ("Scheduled Interview", "get_interview_count"),
        ("Job Position", "job_position_id"),
        ("Contact", "mobile"),
    ]

    default_columns = [
        ("Name", "candidate_name", "get_avatar"),
        ("Email", "mail_indication"),
        ("Stage", "stage_drop_down"),
    ]

    bulk_update_fields = [
        "stage_id",
    ]

    row_attrs = """
                hx-get='{get_details_candidate}'
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
                """

    actions = [
        {
            "action": _("Schedule Interview"),
            "icon": "time-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    hx-get = "{get_schedule_interview}"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    hx-target="#genericModalBody"
                """,
        },
        {
            "action": _("Send Mail"),
            "icon": "mail-open-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    hx-get = "{get_send_mail}"
                    data-toggle="oh-modal-toggle"
                    data-target="#objectDetailsModal"
                    hx-target="#objectDetailsModalTarget"
                """,
        },
        {
            "action": _("Add to Skill Zone"),
            "icon": "heart-circle-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    data-toggle="oh-modal-toggle"
                    hx-get="{get_skill_zone_url}"
                    data-target="#genericModal"
                    hx-target="#genericModalBody"
                """,
        },
        {
            "action": _("Reject Candidate"),
            "icon": "thumbs-down-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    data-toggle="oh-modal-toggle"
                    hx-get="{get_rejected_candidate_url}"
                    {rejected_candidate_class}
                    data-target="#genericModal"
                    hx-target="#genericModalBody"
                """,
        },
        {
            "action": _("View Note"),
            "icon": "newspaper-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100 oh-activity-sidebar__open"
                    hx-get="{get_view_note_url}"
                    data-target="#activitySidebar"
                    hx-target="#activitySidebar"
                    onclick="$('#activitySidebar').addClass('oh-activity-sidebar--show')"
                """,
        },
        {
            "action": _("Document Request"),
            "icon": "document-attach-outline",
            "attrs": """
                     hx-get="{get_document_request}"
                    data-target="#genericModal"
                    hx-target="#genericModalBody"
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    data-toggle="oh-modal-toggle"
                """,
        },
        {
            "action": _("Resume"),
            "icon": "document-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                    href="{get_resume_url}" target="_blank"
                """,
        },
    ]
    records_count_in_tab = False

    def get_bulk_form(self):
        form = super().get_bulk_form()
        form.fields["stage_id"].queryset = form.fields["stage_id"].queryset.filter(
            recruitment_id=self.kwargs["rec_id"]
        )
        return form

    records_per_page = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = self.request.path

    def get(self, request, *args, **kwargs):
        self.selected_instances_key_id = f"selectedCandidateRecords{kwargs['stage_id']}"
        return super().get(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        if self.queryset is None:
            queryset = CACHE.get(self.request.session.session_key + "pipeline")[
                "candidates"
            ].filter(stage_id=self.kwargs["stage_id"])
            queryset = queryset.filter(stage_id=self.kwargs["stage_id"])
            super().get_queryset(queryset=queryset, filtered=True)

        return self.queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class PipelineNav(HorillaNavView):
    """
    HorillaNavView
    """

    search_url = reverse_lazy("cbv-pipeline-tab")
    nav_title = _("Pipeline")
    search_swap_target = "#pipelineContainer"
    filter_body_template = "cbv/pipeline/pipeline_filter.html"
    filter_instance = filters.RecruitmentFilter()
    filter_form_context_name = "form"
    apply_first_filter = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.request.user.has_perm("recruitment.add_recruitment"):
            self.create_attrs = f"""
                                hx-get="{reverse_lazy('recruitment-create')}?{urlencode({'pipeline': 'true'})}"
                                hx-target="#genericModalBody"
                                data-target="#genericModal"
                                data-toggle="oh-modal-toggle"
                                """
        else:
            self.create_attrs = None

    def get_context_data(self, **kwargs):
        """
        context data
        """
        context = super().get_context_data(**kwargs)
        stage_filter_obj = filters.StageFilter()
        candidate_filter_obj = filters.CandidateFilter()
        context["stage_filter_obj"] = stage_filter_obj
        context["candidate_filter_obj"] = candidate_filter_obj
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class ChangeStage(HorillaFormView):
    """
    Change Candidate stage
    """

    model = models.Candidate
    form_class = forms.StageChangeForm

    def form_valid(self, form):
        if form.is_valid():
            messages.success(self.request, _("Stage Updated"))
            form.save()
            return self.HttpResponse()
        messages.info(self.request, _("Stage not updated"))

        return self.HttpResponse()
