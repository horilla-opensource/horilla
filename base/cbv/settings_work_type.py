"""
this page is handling the cbv methods for work type in settings
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import WorkTypeFilter
from base.models import WorkType
from horilla.decorators import permission_required
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_worktype"), name="dispatch")
class WorkTypeList(HorillaListView):
    """
    list view of work types in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("worktype-list")
        self.actions = []
        if self.request.user.has_perm("base.change_worktype"):
            self.actions.append(
                {
                    "action": _("Edit"),
                    "icon": "create-outline",
                    "attrs": """
                            class="oh-btn oh-btn--light-bkg w-100"
                            hx-get='{get_update_url}?instance_ids={ordered_ids}'
                                    hx-target="#genericModalBody"
                                    data-toggle="oh-modal-toggle"
                                    data-target="#genericModal"
                        """,
                }
            )
        if self.request.user.has_perm("base.delete_worktype"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=base.worktype&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = WorkType
    filter_class = WorkTypeFilter
    show_toggle_form = False

    columns = [
        (_("Work Type"), "work_type"),
    ]

    row_attrs = """ id="workTypeTr{get_delete_instance}" """

    header_attrs = {
        "work_type": """ style="width:300px !important" """,
        "action": """ style="width:180px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_worktype"), name="dispatch")
class WorkTypeNav(HorillaNavView):
    """
    navbar of worktype
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("worktype-list")
        if self.request.user.has_perm("base.add_worktype"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('work-type-create-form')}"
                                """

    nav_title = _("Work Type")
    search_swap_target = "#listContainer"
    filter_instance = WorkTypeFilter()
