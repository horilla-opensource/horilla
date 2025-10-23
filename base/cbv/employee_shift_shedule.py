"""
this page is handling the cbv methods for Employee shift shedule in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import EmployeeShiftFilter, EmployeeShiftScheduleFilter
from base.forms import EmployeeShiftScheduleForm
from base.models import EmployeeShiftSchedule
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="base.view_employeeshiftschedule"), name="dispatch"
)
class EmployeeShiftSheduleNav(HorillaNavView):
    """
    nav bar of the employee shift sheduel view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employee-shift-shedule-list")
        if self.request.user.has_perm("base.add_employeeshiftschedule"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('settings-employee-shift-shedule-create')}"
                                """

    nav_title = _("Shift Schedule")
    search_swap_target = "#listContainer"
    filter_instance = EmployeeShiftFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="base.add_employeeshiftschedule"), name="dispatch"
)
class EmployeeShiftSheduleCreateForm(HorillaFormView):
    """
    form view for creating  and updating job position in settings
    """

    model = EmployeeShiftSchedule
    form_class = EmployeeShiftScheduleForm
    new_display_title = _("Create Employee Shift Schedule")
    template_name = "cbv/settings/employee_shift_schedule_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form.fields["day"].initial = self.form.instance.day
            self.form_class.verbose_name = _("Update Employee Shift Schedule")
        return context

    def form_valid(self, form: EmployeeShiftScheduleForm) -> HttpResponse:
        if form.is_valid():
            if self.form.instance.pk:
                shifts = form.instance
                if shifts is not None:
                    days = form["day"].value()
                    if days:
                        shifts.day_id = days
                    shifts.save()
                    messages.success(self.request, _("Shift schedule Updated!."))
            else:
                form.save()
                messages.success(
                    self.request,
                    _("Employee Shift Schedule has been created successfully!"),
                )
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="base.view_employeeshiftschedule"), name="dispatch"
)
class EmployeeShiftSheduleList(HorillaListView):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "day-container"
        self.search_url = reverse("employee-shift-shedule-list")
        if not self.request.user.has_perm(
            "base.change_employeeshiftschedule"
        ) and not self.request.user.has_perm("base.delete_employeeshiftschedule"):
            self.action_method = None

    bulk_update_fields = ["start_time", "end_time", "minimum_working_hour"]

    model = EmployeeShiftSchedule
    filter_class = EmployeeShiftScheduleFilter
    show_filter_tags = False

    columns = [
        (_("Day"), "day_col", "get_avatar"),
        (_("Start Time"), "start_time"),
        (_("End Time"), "end_time"),
        (_("Minimum Working Hours"), "minimum_working_hour"),
        (_("Auto Check Out"), "auto_punch_out_col"),
    ]

    header_attrs = {"action": """ style="width:200px !important;" """}

    row_attrs = """
                id = "scheduleTr{get_instance_id}"
                hx-get='{get_detail_url}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    action_method = "actions_col"


class EmployeeShiftSheduleDetailView(HorillaDetailedView):
    """
    detail view of the page
    """

    model = EmployeeShiftSchedule
    title = _("Details")
    header = {"title": "day", "subtitle": "shift_id", "avatar": "get_avatar"}
    body = [
        (_("Start Time"), "start_time"),
        (_("End Time"), "end_time"),
        (_("Minimum Working Hours"), "minimum_working_hour"),
        (_("Auto Check Out"), "auto_punch_out_col"),
    ]

    action_method = "detail_actions_col"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        if instance.is_auto_punch_out_enabled:
            self.body.append(
                (_("Automatic Check Out Time"), "auto_punch_out_time"),
            )
        return context
