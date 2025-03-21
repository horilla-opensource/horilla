"""
This page  handles rotating shift types page in settings.
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import RotatingShiftFilter
from base.models import RotatingShift
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_rotatingshift"), name="dispatch")
class RotatingShiftTypeListView(HorillaListView):
    """
    List view of the employee shift page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.action_method = "actions_col"
        self.view_id = "shift_view"
        self.search_url = reverse("rotating-shift-list")
        self.actions = []
        if self.request.user.has_perm("base.change_rotatingshift"):
            self.actions.append(
                {
                    "action": "Edit",
                    "icon": "create-outline",
                    "attrs": """
                    class="oh-btn oh-btn--light-bkg w-100"
                    hx-get="{get_update_url}?instance_ids={ordered_ids}"
                    hx-target="#genericModalBody"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    """,
                }
            )
        if self.request.user.has_perm("base.delete_rotatingshift"):
            self.actions.append(
                {
                    "action": "Delete",
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=base.rotatingshift&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = RotatingShift
    filter_class = RotatingShiftFilter

    columns = [
        (_("Title"), "name"),
        (_("Shift 1"), "shift1"),
        (_("Shift 2"), "shift2"),
        (_("Additional Shifts"), "get_additional_shifts"),
    ]

    sortby_mapping = [
        ("Title", "name"),
        ("Shift 1", "shift1__employee_shift"),
        ("Shift 2", "shift2__employee_shift"),
        ("Additional Shifts", "get_additional_shifts"),
    ]

    row_attrs = """
                id = "rotatingShiftTr{get_instance_id}"
                """

    header_attrs = {
        "name": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="base.view_rotatingshift"), name="dispatch")
class RotatingShiftTypeNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("rotating-shift-list")
        if self.request.user.has_perm("base.add_rotatingshift"):
            self.create_attrs = f"""
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('rotating-shift-create')}"
                                """

    nav_title = _("Rotating Shift")
    filter_instance = RotatingShiftFilter()
    search_swap_target = "#listContainer"
