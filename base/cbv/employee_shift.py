"""
This page handles employee shift page in settings
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import EmployeeShiftFilter
from base.models import EmployeeShift
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_employeeshift"), name="dispatch")
class EmployeeShiftListView(HorillaListView):
    """
    List view of the employee shift page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.view_id = "shift_view"
        self.search_url = reverse("employee-shift-list")
        self.actions = []
        if self.request.user.has_perm("base.change_employeeshift"):
            self.actions.append(
                {
                    "action": _("Edit"),
                    "icon": "create-outline",
                    "attrs": """
                    class="oh-btn oh-btn--light-bkg oh-btn--sq-sm"
                    hx-get="{get_update_url}?instance_ids={ordered_ids}"
                    hx-target="#genericModalBody"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    """,
                }
            )
        if self.request.user.has_perm("base.delete_employeeshift"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger oh-btn--sq-sm"
                            hx-get="{get_delete_url}?model=base.employeeshift&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = EmployeeShift
    filter_class = EmployeeShiftFilter
    show_toggle_form = False

    bulk_update_fields = [
        "weekly_full_time",
        "full_time",
    ]

    columns = [
        (_("Shift"), "employee_shift"),
    ]

    sortby_mapping = [
        (_("Shift"), "employee_shift"),
    ]

    row_attrs = """ id = "shiftTr{get_instance_id}" """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_employeeshift"), name="dispatch")
class EmployeeShiftDetailView(HorillaDetailedView):
    """
    detail view for employee shift, also registered as the related-object-link
    target for EmployeeShift via detail_view_url_name
    """

    model = EmployeeShift
    detail_view_url_name = "employee-shift-detail-view"
    detail_view_permission = "base.view_employeeshift"
    title = _("Employee Shift")

    header = {
        "title": "employee_shift",
        "subtitle": "",
        "avatar": "",
    }

    body = [
        (_("Employee Shift"), "employee_shift"),
        (_("Weekly Full Time"), "weekly_full_time"),
        (_("Full Time"), "full_time"),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_employeeshift"), name="dispatch")
class EmployeeShiftNav(HorillaNavView):
    """
    Nav bar
    """

    template_name = "generic/inline_nav.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("employee-shift-list")
        if self.request.user.has_perm("base.add_employeeshift"):
            self.create_attrs = f"""
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('employee-shift-create-view')}"
                                """

    nav_title = _("Employee Shift")
    filter_instance = EmployeeShiftFilter()
    search_swap_target = "#listContainer"
