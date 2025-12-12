from typing import Any

from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import filtersubordinates, is_reportingmanager
from helpdesk.filter import TicketFilter, TicketReGroup
from helpdesk.models import TICKET_STATUS, Ticket
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.pipeline import Pipeline
from horilla_views.generic.cbv.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSectionView,
    HorillaTabView,
)


@method_decorator(login_required, name="dispatch")
class TicketPipelineView(HorillaSectionView):
    """
    Offboarding Pipeline View
    """

    nav_url = reverse_lazy("ticket-pipeline-nav")
    view_url = reverse_lazy("get-ticket-tabs")
    view_container_id = "pipelineContainer"
    script_static_paths = ["tickets/action.js"]
    template_name = "cbv/pipeline/ticket_section_view.html"


@method_decorator(login_required, name="dispatch")
class TicketPipelineNav(HorillaNavView):
    """
    Offboarding Pipeline Navigation View
    """

    nav_title = "Tickets"
    search_swap_target = "#pipelineContainer"
    search_url = reverse_lazy("ticket-tab")
    filter_body_template = "cbv/pipeline/ticket_filter_form.html"
    filter_instance = TicketFilter()
    filter_form_context_name = "form"
    group_by_fields = [
        ("employee_id", _("Owner")),
        ("ticket_type", _("Ticket Type")),
        ("status", _("Status")),
        ("priority", _("Priority")),
        ("tags", _("Tags")),
        ("assigned_to", _("Assigner")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]
    actions = [
        {
            "action": "Archive",
            "attrs": """
                href="#"
                role="button"
                class="oh-dropdown__link"
                onclick = "ticketBulkArchive(event)"
            """,
        },
        {
            "action": "Unarchive",
            "attrs": """
                href="#"
                role="button"
                class="oh-dropdown__link"
                onclick = "ticketBulkUnArchive(event)"
            """,
        },
        {
            "action": "Delete",
            "attrs": """
                href="#"
                role="button"
                class="oh-dropdown__link oh-dropdown__link--danger"
                onclick = "ticketsBulkDelete(event)"
            """,
        },
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_attrs = f"""
            class="oh-btn oh-btn--secondary"
            hx-get="{reverse('ticket-create')}"
            hx-target="#objectCreateModalTarget"
            data-toggle="oh-modal-toggle"
            data-target="#objectCreateModal"
        """


@method_decorator(login_required, name="dispatch")
class TicketTabView(HorillaTabView):
    """
    Pipeline List View
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.tabs = [
            {
                "title": _("My Tickets"),
                # "url":f'{ reverse("ticket-pipeline-view")}?ticket_tab=my_tickets&',
                "url": f'{ reverse("ticket-tab-list")}?ticket_tab=my_tickets&',
            },
            {
                "title": _("Suggested Tickets"),
                # "url":f'{ reverse("ticket-pipeline-view")}?ticket_tab=suggested_tickets&',
                "url": f'{ reverse("ticket-tab-list")}?ticket_tab=suggested_tickets&',
            },
        ]

        if is_reportingmanager(self.request) or self.request.user.has_perm(
            "helpdesk.view_ticket"
        ):
            self.tabs.append(
                {
                    "title": _("All Tickets"),
                    # "url":f'{ reverse("ticket-pipeline-view")}?ticket_tab=all_tickets&',
                    "url": f'{ reverse("ticket-tab-list")}?ticket_tab=all_tickets&',
                }
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_filter_tags"] = True
        return context


# class TicketPipelineTabView(Pipeline):
#     """
#     Offboarding Pipeline View
#     """
#     grouper = "status"
#     allowed_fields = [
#         {
#             "field" : "status",
#             "model": Ticket,
#             "url": reverse_lazy("ticket-tab-list"),
#             "filter": TicketFilter,
#             "parameters": [
#                 "pipeline_status={status}",
#             ],
#             "actions": [],
#         }
#     ]
#     def get_queryset(self):
#         super().get_queryset()
#         class Ticket():
#             def __init__(self,status):
#                 self.name = status
#                 self.status = status[0]

#             def __str__(self):
#                 return self.name[1]

#         status = [Ticket(status) for status in TICKET_STATUS]
#         self.queryset = status
#         return self.queryset


@method_decorator(login_required, name="dispatch")
class TicketListView(HorillaListView):
    """
    Pipeline List View
    """

    model = Ticket
    filter_class = TicketFilter
    # custom_empty_template = "cbv/pipeline/empty_list.html"
    bulk_update_fields = [
        "ticket_type",
        "status",
        "priority",
        "assigned_to",
        "tags",
    ]
    columns = [
        (_("Ticket ID"), "get_ticket_id_col"),
        (_("Title"), "title"),
        (_("Owner"), "employee_id"),
        (_("Type"), "ticket_type"),
        (_("Forward to"), "get_raised_on"),
        (_("Assigned to"), "get_assigned_to"),
        (_("Status"), "get_status_col"),
        (_("Priority"), "get_priority_stars"),
        (_("Tags"), "get_tags_col"),
    ]

    row_attrs = """
        onclick="window.location.href = `{get_ticket_detail_url}`"
        class = "{row_colors}"
    """

    action_method = """ticket_action_col"""
    header_attrs = {"action": "style='width:200px'"}

    row_status_indications = [
        (
            "canceled--dot",
            _("Canceled"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('canceled');
            $('[name=new]').val('unknown').change();
            $('[name=in_progress]').val('unknown').change();
            $('[name=on_hold]').val('unknown').change();
            $('[name=resolved]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "resolved--dot",
            _("Resolved"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('resolved');
            $('[name=new]').val('unknown').change();
            $('[name=in_progress]').val('unknown').change();
            $('[name=on_hold]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "on_hold--dot",
            _("On Hold"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('on_hold');
            $('[name=new]').val('unknown').change();
            $('[name=in_progress]').val('unknown').change();
            $('[name=resolved]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "in_progress--dot",
            _("In Progress"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('in_progress');
            $('[name=new]').val('unknown').change();
            $('[name=on_hold]').val('unknown').change();
            $('[name=resolved]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "new--dot",
            _("New"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('new');
            $('[name=on_hold]').val('unknown').change();
            $('[name=in_progress]').val('unknown').change();
            $('[name=resolved]').val('unknown').change();
            $('[name=canceled]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
    ]
    row_status_class = "new-{new} in_progress-{in_progress} on_hold-{on_hold} resolved-{resolved} canceled-{canceled}"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.request.GET.get("ticket_tab") == "all_tickets":
            if (
                self.request.user.has_perm("helpdesk.view_claimrequest")
                or self.request.user.has_perm("helpdesk.change_claimrequest")
                or self.request.user.has_perm("helpdesk.change_ticket")
                or self.request.user.has_perm("helpdesk.delete_ticket")
            ):
                self.action_method = "ticket_action_col"
            else:
                self.action_method = None

    def get_queryset(self):
        queryset = super().get_queryset()
        ticket_tab = self.request.GET.get("ticket_tab", "my_tickets")
        if ticket_tab == "my_tickets":
            return queryset.filter(employee_id=self.request.user.employee_get)

        elif ticket_tab == "suggested_tickets":
            employee = self.request.user.employee_get
            qs_cpy = queryset
            queryset = queryset.none()
            if hasattr(employee, "employee_work_info"):
                work_info = employee.employee_work_info
                department = work_info.department_id
                job_position = work_info.job_position_id

                if department:
                    queryset |= qs_cpy.filter(
                        raised_on=department.id, assigning_type="department"
                    )

                if job_position:
                    queryset |= qs_cpy.filter(
                        raised_on=job_position.id, assigning_type="job_position"
                    )

            queryset |= qs_cpy.filter(
                raised_on=employee.id, assigning_type="individual"
            )
            return queryset.distinct()

        elif ticket_tab == "all_tickets":
            queryset = filtersubordinates(
                self.request,
                queryset,
                "helpdesk.view_ticket",
            )
            return queryset
