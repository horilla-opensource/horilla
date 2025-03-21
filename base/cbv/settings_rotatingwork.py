"""
this page is handling the cbv methods for Rotating work type in settings
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import RotatingWorkTypeFilter
from base.models import RotatingWorkType
from horilla.decorators import permission_required
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_rotatingworktype"), name="dispatch")
class RotatingWorkTypeList(HorillaListView):
    """
    list view of Rotating work types in settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("rotating-list")
        self.actions = []
        if self.request.user.has_perm("base.change_rotatingworktype"):
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
                },
            )
        if self.request.user.has_perm("base.delete_rotatingworktype"):
            self.actions.append(
                {
                    "action": _("Delete"),
                    "icon": "trash-outline",
                    "attrs": """
                            class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-100"
                            hx-get="{get_delete_url}?model=base.rotatingworktype&pk={pk}"
                            data-toggle="oh-modal-toggle"
                            data-target="#deleteConfirmation"
                            hx-target="#deleteConfirmationBody"
                        """,
                }
            )

    model = RotatingWorkType
    filter_class = RotatingWorkTypeFilter

    row_attrs = """
                id="rotatingWorkTypeTr{get_delete_instance}"
                """

    columns = [
        (_("Title"), "name"),
        (_("Work Type 1"), "work_type1"),
        (_("Work Type 2"), "work_type2"),
        (_("Additional Work Types"), "get_additional_worktytpes"),
    ]

    sortby_mapping = [
        ("Title", "name"),
        ("Work Type 1", "work_type1__work_type"),
        ("Work Type 2", "work_type2__work_type"),
        ("Additional Work Types", "get_additional_worktytpes"),
    ]

    header_attrs = {
        "name": """ style="width:200px !important" """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.view_rotatingworktype"), name="dispatch")
class RotatingWorkTypeNav(HorillaNavView):
    """
    navbar of Rotating worktype
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("rotating-list")
        if self.request.user.has_perm("base.add_rotatingworktype"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('rotating-work-type-create-form')}"
                                """

    nav_title = _("Rotating Work Type")
    search_swap_target = "#listContainer"
    filter_instance = RotatingWorkTypeFilter()
