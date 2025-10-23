"""
This page handles grace time in settings page.
"""

from typing import Any

from django.contrib import messages
from django.forms import HiddenInput
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from attendance.filters import GraceTimeFilter
from attendance.forms import GraceTimeForm
from attendance.models import GraceTime
from base.cbv.employee_shift import EmployeeShiftListView
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class GenericGraceTimeListView(HorillaListView):
    """
    List view of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "all-container"

    model = GraceTime
    filter_class = GraceTimeFilter

    columns = [
        (_("Allowed Time"), "allowed_time_col"),
        (_("Applicable on clock-in"), "applicable_on_clock_in_col"),
        (_("Applicable on clock-out"), "applicable_on_clock_out_col"),
        (_("Assigned Shifts"), "get_shifts_display"),
        (_("Is default"), "is_default_col"),
        (_("Is active"), "is_active_col"),
    ]

    header_attrs = {
        "allowed_time_col": """ style = "width:200px !important" """,
    }

    row_attrs = """ id = "graceTimeTr{get_instance_id}" """

    action_method = "action_col"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class DefaultGraceTimeList(GenericGraceTimeListView):
    """
    List of default grace time
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "default-container"

    selected_instances_key_id = "selectedInstancesDefault"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_default=True)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class GraceTimeList(GenericGraceTimeListView):
    """
    List of grace time
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "gracetime-container"

    selected_instances_key_id = "selectedInstancesData"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class DefaultGraceTimeNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # self.search_url = reverse("grace-time-list")
        default_grace_time = GraceTime.objects.filter(is_default=True).first()
        if not default_grace_time and self.request.user.has_perm(
            "attendance.add_gracetime"
        ):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('grace-time-create')}?default=True"
                                """

    nav_title = _("Default Grace Time")
    filter_instance = GraceTimeFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="attendance.view_attendancevalidationcondition"),
    name="dispatch",
)
class GraceTimeNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.search_url = reverse("grace-time-list")
        self.create_attrs = f"""
                            onclick = "event.stopPropagation();"
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('grace-time-create')}?default=False"
                            """

    nav_title = _("Grace Time")
    filter_instance = GraceTimeFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="attendance.add_gracetime"), name="dispatch")
class GraceTimeFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = GraceTime
    form_class = GraceTimeForm
    new_display_title = _("Create grace time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # is_default = eval(self.request.GET.get("default"))
        # self.form.fields["is_default"].initial = is_default
        qs = self.model.objects.all()
        default_object = qs.filter(is_default=True).first()
        if default_object and self.form.instance != default_object:
            self.form.fields["is_default"].widget = HiddenInput()

        if self.form.instance.pk:
            self.form.fields["shifts"].initial = self.form.instance.employee_shift.all()
            self.form_class.verbose_name = _("Update grace time")
        return context

    def form_valid(self, form: GraceTimeForm) -> HttpResponse:
        if form.is_valid():
            gracetime = form.save()
            if form.instance.pk:
                gracetime.employee_shift.clear()
                message = _("Grace time updated successfully.")
                messages.success(self.request, message)
            else:

                message = _("Grace time created successfully.")
                messages.success(self.request, message)
            shifts = form.cleaned_data.get("shifts")
            for shift in shifts:
                shift.grace_time_id = gracetime
                shift.save()
            # form.save()
            defaultValue = self.request.GET.get("default")
            if defaultValue == "False":
                return HttpResponse(
                    "<script>$('#genericModal').removeClass('oh-modal--show');$('#gracetime-containerReload').click();</script>"
                )
            return HttpResponse(
                "<script>$('#genericModal').removeClass('oh-modal--show');$('#default-containerReload').click();$('.defaultGraceNav').click();</script>"
            )
        return super().form_valid(form)


EmployeeShiftListView.columns.append((_("Grace Time"), "get_grace_time"))
EmployeeShiftListView.sortby_mapping.append(("Grace Time", "grace_time_id"))
EmployeeShiftListView.bulk_update_fields.append("grace_time_id")
