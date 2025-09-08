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
from horilla_views.generic.cbv.kanban import HorillaKanbanView
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

    filter_class = filters.RecruitmentFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        recruitments = self.filter_class(self.request.GET).qs.filter(is_active=True)
        view_type = self.request.GET.get("view", "card")
        CACHE.set(
            self.request.session.session_key + "pipeline",
            {
                "stages": GetStages.filter_class(self.request.GET).qs.order_by(
                    "sequence"
                ),
                "recruitments": recruitments,
                "candidates": False,
            },
            timeout=600,
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
            url = reverse("candidate-card-cbv", kwargs={"pk": rec.pk})

            if view_type == "list":
                url = (
                    reverse("get-stages-recruitment", kwargs={"rec_id": rec.pk})
                    + f"?view={view_type}"
                )
            tab["url"] = url

            self.query_params["view"] = view_type
            tab["badge_label"] = _("Stages")
            tab["actions"] = []
            if rec_manager_perm or change_perm:
                if add_stage_perm or rec_manager_perm or change_perm:
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

                    tab["actions"].append(
                        {
                            "action": _("Manage Stage Order"),
                            "attrs": f"""
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-get="{reverse("rec-update-stage-seq", kwargs={"pk": rec.pk})}"
                                hx-target="#genericModalBody"
                                style="cursor: pointer;"
                            """,
                        }
                    )

                if change_perm or rec_manager_perm or change_perm:
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

                if add_cand_perm or rec_manager_perm or change_perm:
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

                if change_perm or rec_manager_perm:
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_filter_tags"] = True

        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(
    manager_can_enter(perm="recruitment.view_recruitment"), name="dispatch"
)
class GetStages(TemplateView):
    """
    GetStages
    """

    filter_class = filters.StageFilter

    template_name = "cbv/pipeline/stages.html"
    stages = None

    def get(self, request, *args, **kwargs):
        """
        get method
        """
        rec_id = kwargs["rec_id"]
        cache = CACHE.get(request.session.session_key + "pipeline")
        if not cache.get("candidates"):
            cache["candidates"] = CandidateList.filter_class(
                self.request.GET
            ).qs.filter(is_active=True)
            CACHE.set(request.session.session_key + "pipeline", cache)

        self.stages = cache["stages"].filter(recruitment_id=rec_id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stages"] = self.stages
        context["view_id"] = get_short_uuid(6, "hsv")
        context["rec_id"] = kwargs["rec_id"]
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
    show_filter_tags = True
    records_per_page = 10
    records_count_in_tab = False

    custom_empty_template = "cbv/pipeline/empty.html"
    header_attrs = {
        "action": """ style="width:400px;" """,
        "mobile": """ style="width:100px;" """,
        "Stage": """ style="width:100px;" """,
        "get_interview_count": """ style="width:200px;" """,
    }
    columns = [
        ("Name", "candidate_name", "get_avatar"),
        ("Email", "mail_indication"),
        ("Stage", "stage_drop_down"),
        ("Rating", "rating_bar"),
        ("Hired Date", "hired_date"),
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
        "hired_date",
    ]

    row_attrs = """
        hx-get='{get_details_candidate}'
        data-toggle="oh-modal-toggle"
        data-target="#genericModal"
        hx-target="#genericModalBody"
    """

    header_attrs = {
        "option": """
            style="width:280px !important"
        """
    }
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
                class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100 disabled"
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

    def get_bulk_form(self):
        form = super().get_bulk_form()
        form.fields["stage_id"].queryset = form.fields["stage_id"].queryset.filter(
            recruitment_id=self.kwargs["rec_id"]
        )
        return form

    def bulk_update_accessibility(self):
        """
        Bulk Update accessiblity
        """
        if not self.kwargs.get("stage_id"):
            return super().bulk_update_accessibility()
        first_cand_in_stage = self.queryset.first()
        return super().bulk_update_accessibility() or (
            first_cand_in_stage
            and (
                self.request.user.employee_get
                in first_cand_in_stage.stage_id.stage_managers.all()
                or self.request.user.employee_get
                in first_cand_in_stage.recruitment_id.recruitment_managers.all()
            )
        )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = self.request.path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.bulk_update_accessibility():
            context["actions"] = []
        return context

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
class CandidateCard(HorillaKanbanView):
    model = models.Candidate
    filter_class = filters.CandidateFilter
    group_filter_class = filters.StageFilter
    group_key = "stage_id"
    records_per_page = 10
    filter_keys_to_remove = ["rec_id"]

    kanban_attrs = """
        hx-get='{get_details_candidate}'
        data-toggle="oh-modal-toggle"
        data-target="#genericModal"
        hx-target="#genericModalBody"
    """

    details = {
        "image_src": "{get_avatar}",
        "title": "{get_full_name}",
        "email": "{email}",
        "position": "{job_position_id}",
    }

    group_actions = [
        {
            "action": _("Add Candidate"),
            "accessibility": "recruitment.accessibility.add_candidate_accessibility",
            "attrs": """
                hx-target="#genericModalBody"
                hx-get="{get_add_candidate_url}"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
            """,
        },
        {
            "action": _("Edit"),
            "accessibility": "recruitment.accessibility.edit_stage_accessibility",
            "attrs": """
                hx-target="#genericModalBody"
                hx-get="{get_stage_update_url}"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
            """,
        },
        {
            "action": _("Bulk Mail"),
            "accessibility": "recruitment.accessibility.edit_stage_accessibility",
            "attrs": """
                hx-target="#objectCreateModalTarget"
                hx-get="{get_send_email_url}"
                data-toggle="oh-modal-toggle"
                data-target="#objectCreateModal"
            """,
        },
        {
            "action": _("Delete"),
            "accessibility": "recruitment.accessibility.delete_stage_accessibility",
            "attrs": """
                hx-target="#deleteConfirmationBody"
                hx-get="{get_delete_url}"
                data-toggle="oh-modal-toggle"
                data-target="#deleteConfirmation"
            """,
        },
    ]

    actions = [
        {
            "action": _("Schedule Interview"),
            "attrs": """
                hx-get = "{get_schedule_interview}"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
            """,
        },
        {
            "action": _("Send Mail"),
            "attrs": """
                hx-get = "{get_send_mail}"
                data-toggle="oh-modal-toggle"
                data-target="#objectDetailsModal"
                hx-target="#objectDetailsModalTarget"
            """,
        },
        {
            "action": "Add to Skill Zone",
            "accessibility": "recruitment.cbv.accessibility.add_skill_zone",
            "attrs": """
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{get_add_to_skill}"
                hx-target="#genericModalBody"
                class="oh-dropdown__link"

            """,
        },
        {
            "action": "View candidate self tracking",
            "accessibility": "recruitment.cbv.accessibility.check_candidate_self_tracking",
            "attrs": """
                href="{get_self_tracking_url}"
                class="oh-dropdown__link"
            """,
        },
        {
            "action": "Request Document",
            "accessibility": "recruitment.cbv.accessibility.request_document",
            "attrs": """
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{get_document_request_doc}"
                hx-target="#genericModalBody"
                class="oh-dropdown__link"
            """,
        },
        {
            "action": "Add to Rejected",
            "accessibility": "recruitment.cbv.accessibility.add_reject",
            "attrs": """
                hx-target="#genericModalBody"
                hx-swap="innerHTML"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{get_add_to_reject}"
                class="oh-dropdown__link"
            """,
        },
        {
            "action": "Edit Rejected Candidate",
            "accessibility": "recruitment.cbv.accessibility.edit_reject",
            "attrs": """
                hx-target="#genericModalBody"
                hx-swap="innerHTML"
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-get="{get_add_to_reject}"
                class="oh-dropdown__link"
            """,
        },
        {
            "action": _("View Note"),
            "attrs": """
                hx-get="{get_view_note_url}"
                data-target="#activitySidebar"
                hx-target="#activitySidebar"
                onclick="$('#activitySidebar').addClass('oh-activity-sidebar--show')"
            """,
        },
        {
            "action": _("Resume"),
            "attrs": """
                href="{get_resume_url}" target="_blank"
            """,
        },
        {
            "action": "archive_status",
            "attrs": """
                class="oh-dropdown__link"
                onclick="archiveCandidate({get_archive_url});"
            """,
        },
        {
            "action": "Delete",
            "attrs": """
                class="oh-dropdown__link oh-dropdown__link--danger"
                onclick="event.stopPropagation();
                deleteCandidate('{get_delete_url}'); "
            """,
        },
    ]

    def get_related_groups(self, *args, **kwargs):
        related_groups = super().get_related_groups(*args, **kwargs)
        rec_id = self.kwargs.get("pk")
        if rec_id:
            related_groups = related_groups.filter(recruitment_id=rec_id)

        return related_groups


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

        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": f'{reverse_lazy("cbv-pipeline-tab")}?view=list',
                "attrs": f"""
                    title ='List'
                """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": f'{reverse_lazy("cbv-pipeline-tab")}?view=card',
                "attrs": f"""
                    title ='Card'
                """,
            },
        ]

    def get_context_data(self, **kwargs):
        """
        context data
        """
        context = super().get_context_data(**kwargs)
        stage_filter_obj = GetStages.filter_class()
        candidate_filter_obj = CandidateList.filter_class()
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
