"""
Dashbord of project
"""

import calendar
import datetime
from typing import Any

from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.urls import resolve, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import get_subordinates
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaDetailedView, HorillaListView
from project.cbv.cbv_decorators import is_projectmanager_or_member_or_perms
from project.filters import ProjectFilter
from project.models import Project


@method_decorator(login_required, name="dispatch")
@method_decorator(
    is_projectmanager_or_member_or_perms("project.view_project"), name="dispatch"
)
class ProjectsDueInMonth(HorillaListView):

    model = Project
    filter_class = ProjectFilter
    bulk_select_option = False
    columns = [(_("Project"), "title", "get_avatar")]
    show_filter_tags = False

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.has_perm("project.view_project"):
            employee = self.request.user.employee_get
            task_filter = queryset.filter(
                Q(task__task_members=employee) | Q(task__task_manager=employee)
            )
            project_filter = queryset.filter(Q(manager=employee) | Q(members=employee))
            queryset = task_filter | project_filter
            today = datetime.date.today()
            first_day = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            last_day_of_month = today.replace(day=last_day)
            queryset = queryset.filter(
                Q(end_date__gte=first_day) & Q(end_date__lte=last_day_of_month)
            ).exclude(status="expired")
        return queryset

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("projects-due-in-this-month")

    row_attrs = """
                hx-get='{get_detail_url}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


class ProjectDetailView(HorillaDetailedView):
    """
    detail view of the projects
    """

    model = Project
    title = _("Details")
    header = {"title": "title", "subtitle": "", "avatar": "get_avatar"}
    body = [
        (_("Manager"), "manager"),
        (_("Members"), "get_members"),
        (_("Status"), "status_column"),
        (_("No of Tasks"), "task_count"),
        (_("Start date"), "start_date"),
        (_("End date"), "end_date"),
        (_("Document"), "get_document_html"),
        (_("Description"), "description"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        instnce_id = resolve(self.request.path_info).kwargs.get("pk")
        employee = self.request.user.employee_get
        project = Project.objects.get(id=instnce_id)
        if (
            employee in project.managers.all()
            or employee in project.members.all()
            or self.request.user.has_perm("project.view_project")
        ):
            self.actions = [
                {
                    "action": _("View Project"),
                    "icon": "create-outline",
                    "attrs": """
                    class = "oh-btn oh-btn--info w-100"
                    {redirect}
                """,
                }
            ]

    def get_queryset(self) -> QuerySet[Any]:
        queryset = super().get_queryset()
        queryset = queryset.annotate(task_count=Count("task"))
        return queryset
