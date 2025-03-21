"""
this page is handling the cbv methods for Break point conditions in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.filters import AttendanceBreakpointFilter
from attendance.forms import AttendanceValidationConditionForm
from attendance.models import AttendanceValidationCondition
from horilla.decorators import permission_required
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class BreakPointList(HorillaListView):
    """
    list view of the Break point conditions in settings
    """

    model = AttendanceValidationCondition
    filter_class = AttendanceBreakpointFilter

    columns = [
        (_("Auto Validate Till"), "validation_at_work"),
        (_("Min Hour To Approve OT"), "minimum_overtime_to_approve"),
        (_("OT Cut-Off/Day"), "overtime_cutoff"),
        (_("Actions"), "break_point_actions"),
    ]
    header_attrs = {
        "validation_at_work": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class BreakPointNavView(HorillaNavView):
    """
    navbar of attendance breakpoint view
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        condition = AttendanceValidationCondition.objects.first()
        if not condition and self.request.user.has_perm(
            "attendance.add_attendancevalidationcondition"
        ):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('break-point-create-form')}"
                                """

    nav_title = _("Break Point Condition")
    search_swap_target = "#listContainer"
    filter_instance = AttendanceBreakpointFilter()


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class BreakPointCreateForm(HorillaFormView):
    """
    form view for create and edit Break Point in settings
    """

    model = AttendanceValidationCondition
    form_class = AttendanceValidationConditionForm
    new_display_title = _("Create Attendance condition")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # form = self.form_class()
        if self.form.instance.pk:
            form = self.form_class(instance=self.form.instance)
            self.form_class.verbose_name = _("Update Attendance condition")
        context[form] = self.form
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Attendance condition")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: AttendanceValidationConditionForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                messages.success(
                    self.request, _("Attendance Break-point settings updated.")
                )
            else:
                messages.success(
                    self.request, _("Attendance Break-point settings created.")
                )
            form.save()
            return self.HttpResponse("<script>location.reload();</script>")
        return super().form_valid(form)
