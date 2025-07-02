"""
this page handles the cbv methods of compensatory leave request page.
"""

from typing import Any

from django.apps import apps
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.methods import filtersubordinates, is_reportingmanager
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from leave.decorators import is_compensatory_leave_enabled
from leave.methods import attendance_days

if apps.is_installed("attendance"):
    from leave.filters import CompensatoryLeaveRequestFilter
    from leave.forms import CompensatoryLeaveForm
    from leave.models import CompensatoryLeaveRequest


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryLeaveView(TemplateView):
    """
    for compensatory page
    """

    template_name = "cbv/compensatory_leave/compensatory_home.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryListView(HorillaListView):
    """
    generic list view of page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("compensatory-list")
        # self.view_id = "compensator-container"

    filter_class = CompensatoryLeaveRequestFilter
    model = CompensatoryLeaveRequest
    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Leave Type"), "leave_type_id"),
        (_("Attendance Dates"), "compensatory_date"),
        (_("Requested Days"), "requested_days"),
        (_("Created By"), "created_by__employee_get"),
        (_("Status"), "status_display"),
        (_("Description"), "description"),
        (_("Comment"), "compensatory_comment"),
    ]
    option_method = "compensatory_options"

    sortby_mapping = [
        ("Employee", "employee_id__get_full_name"),
        ("Leave Type", "leave_type_id__name"),
        ("Attendance Dates", "compensatory_date"),
        ("Requested Days", "requested_days"),
        ("Created By", "created_by__get_full_name"),
        ("Status", "status_display"),
    ]
    row_status_indications = [
        (
            "rejected--dot",
            _("Rejected"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('rejected');
            $('[name=approved]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "requested--dot",
            _("Requested"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('requested');
            $('[name=rejected]').val('unknown').change();
            $('[name=approved]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
        (
            "approved--dot",
            _("Approved"),
            """
            onclick="
            $('#applyFilter').closest('form').find('[name=status]').val('approved');
            $('[name=rejected]').val('unknown').change();
            $('[name=requested]').val('unknown').change();
            $('#applyFilter').click();
            "

            """,
        ),
    ]

    row_status_class = "status-{status}"


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryNavView(HorillaNavView):
    """
    nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("compensatory-tab-view")
        self.create_attrs = f"""
             hx-get="{reverse_lazy("create-compensatory-leave")}"
             hx-target="#genericModalBody"
             data-target="#genericModal"
             data-toggle="oh-modal-toggle"
         """

    nav_title = _("Compensatory Leave Requests")
    filter_body_template = "cbv/compensatory_leave/compensatory_leave_filter.html"
    filter_instance = CompensatoryLeaveRequestFilter()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryLeaveTabView(HorillaTabView):
    """
    tabview of the page
    """

    template_name = "cbv/compensatory_leave/inherit_class.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("My Compensatory Leave Requests"),
                "url": f"{reverse('my-compensatory-tab')}",
            }
        ]

        if self.request.user.has_perm(
            "leave.change_leaveallocationrequest"
        ) or is_reportingmanager(self.request):
            self.tabs.append(
                {
                    "title": _("Compensatory Leave Requests"),
                    "url": f"{reverse('compensatory-tab')}",
                }
            )


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class MyCompensatoryLeaveTab(CompensatoryListView):
    """
    my compensate leave tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("my-compensatory-tab")

    def get_queryset(self):
        queryset = super().get_queryset()
        employee = self.request.user.employee_get
        queryset = queryset.filter(employee_id=employee.id)
        return queryset

    row_attrs = """
                {is_compensatory_request_rejected},
                hx-get='{my_compensatory_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryLeaveTab(CompensatoryListView):
    """
    compensate leave tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("compensatory-list")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = filtersubordinates(
            self.request, queryset, "leave.view_compensatoryleaverequest"
        )

        return queryset

    action_method = "compensatory_confirm_actions"
    row_attrs = """
                {is_compensatory_request_rejected},
                hx-get='{compensatory_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryGenericDetailView(HorillaDetailedView):
    """
    Generic Detail view of page
    """

    model = CompensatoryLeaveRequest
    title = _("Details")
    header = {
        "title": "compensatory_detail_name_subtitle",
        "subtitle": "compensatory_detail_subtitle",
        "avatar": "employee_id__get_avatar",
    }

    body = [
        (_("Requested Days"), "requested_days"),
        (_("Leave Type"), "leave_type_id"),
        (_("Created Date"), "requested_date"),
        (_("Created By"), "created_by__employee_get"),
        (_("Attendance Dates"), "compensatory_date"),
        (_("Description"), "description"),
        (_("Reject Reason"), "compensatory_detail_reject_reason", True),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class MyCompensatoryDetailView(CompensatoryGenericDetailView):
    """
    my compensatory tab detail view
    """

    action_method = "my_compensatory_detail_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryTabDetailView(CompensatoryGenericDetailView):
    """
    compensatory tab detail view
    """

    action_method = "compensatory_detail_actions"


@method_decorator(login_required, name="dispatch")
@method_decorator(is_compensatory_leave_enabled(), name="dispatch")
class CompensatoryForm(HorillaFormView):
    """
    for view
    """

    model = CompensatoryLeaveRequest
    form_class = CompensatoryLeaveForm
    new_display_title = _("Create Compensatory Leave Request")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Compensatory Leave Request")

        return context

    def form_valid(self, form: CompensatoryLeaveForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Compensatory Leave Updated")
            else:
                comp_req = form.save()
                comp_req.requested_days = attendance_days(
                    comp_req.employee_id, comp_req.attendance_id.all()
                )
                comp_req.save()
                message = _("Compensatory Leave Created")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


# class CompensatoryRejectForm(HorillaFormView):
#     """
#     for view
#     """

#     model = CompensatoryLeaveRequest
#     form_class = CompensatoryLeaveRequestRejectForm

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         if self.form.instance.pk:
#             self.form_class.verbose_name = _(
#                 "Reject Compensatory Leave Request"
#             )

#         return context

#     def form_valid(self, form: CompensatoryLeaveForm) -> HttpResponse:
#         if form.is_valid():
#             if form.instance.pk:
#                 message = _("Compensatory Leave Request Rejected")
#             form.save()
#             messages.success(self.request, message)
#             return self.HttpResponse("<script>window.location.reload()</script>")
#         return super().form_valid(form)
