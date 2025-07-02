"""
Dashboard of onboarding
"""

from typing import Any

from django.db.models import CharField, Count, Q, Value
from django.db.models.functions import Cast, Concat
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView
from onboarding.cbv_decorators import all_manager_can_enter
from onboarding.filters import OnboardingTaskFilter
from onboarding.models import CandidateTask, OnboardingTask


@method_decorator(login_required, name="dispatch")
@method_decorator(
    all_manager_can_enter("onboarding.change_onboardingtask"), name="dispatch"
)
class MyOnboardingTaskList(HorillaListView):
    """
    List view for onboarding tasks in dashboard
    """

    model = OnboardingTask
    bulk_select_option = False
    filter_class = OnboardingTaskFilter

    row_attrs = """
                hx-get="{get_detail_url}"
                hx-target="#taskModalBody"
                data-target="#taskModal"
                data-toggle="oh-modal-toggle"
                """

    columns = [
        (_("Task"), "task_title_count"),
        (_("Todo"), "todo_count"),
        (_("Scheduled"), "scheduled_count"),
        (_("Ongoing"), "ongoing_count"),
        (_("Stuck"), "stuck_count"),
        (_("Done"), "done_count"),
    ]

    header_attrs = {
        "task_title_count": """
                          style = "width:100px !important "
                          """,
        "todo_count": """
                          style = "width:55px !important"
                          """,
        "scheduled_count": """
                          style = "width:55px !important;"
                          """,
        "ongoing_count": """
                          style = "width:60px !important"
                          """,
        "stuck_count": """
                          style = "width:55px !important"
                          """,
        "done_count": """
                          style = "width:65px !important"
                          """,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        employee_id = self.request.user.employee_get.id
        queryset = (
            queryset.filter(
                employee_id__id=employee_id,
                candidates__is_active=True,
                candidates__recruitment_id__closed=False,
            )
            .distinct()
            .annotate(
                todo_count=Count(
                    "candidatetask",
                    filter=Q(candidatetask__status="todo"),
                    distinct=True,
                ),
                scheduled_count=Count(
                    "candidatetask",
                    filter=Q(candidatetask__status="scheduled"),
                    distinct=True,
                ),
                ongoing_count=Count(
                    "candidatetask",
                    filter=Q(candidatetask__status="ongoing"),
                    distinct=True,
                ),
                stuck_count=Count(
                    "candidatetask",
                    filter=Q(candidatetask__status="stuck"),
                    distinct=True,
                ),
                done_count=Count(
                    "candidatetask",
                    filter=Q(candidatetask__status="done"),
                    distinct=True,
                ),
                task_title_count=Concat(
                    "task_title",
                    Value(" ("),
                    Cast(Count("candidatetask", distinct=True), CharField()),
                    Value(")"),
                    output_field=CharField(),
                ),
            )
        )

        return queryset

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "myOnboarding"
        self.search_url = reverse("task-report-onboarding")


@method_decorator(login_required, name="dispatch")
@method_decorator(
    all_manager_can_enter("onboarding.view_candidatetask"), name="dispatch"
)
class MyOnboardingCandidatesSingleView(HorillaListView):
    """
    Single view of my onboarding task in dashboard
    """

    model = CandidateTask
    bulk_select_option = None

    template_name = "cbv/dashboard/my_onboarding_task.html"

    columns = [
        (_("Candidaate"), "candidate_id__name"),
        (_("Status"), "status_col"),
    ]

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        task_id = self.request.GET.get("task_id")
        candidate_tasks = CandidateTask.objects.filter(onboarding_task_id__id=task_id)
        context["candidate_tasks"] = candidate_tasks
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        task_id = self.request.GET.get("task_id")
        queryset = queryset.filter(onboarding_task_id__id=task_id)
        return queryset
