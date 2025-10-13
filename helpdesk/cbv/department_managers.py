"""
This page handles the department managers page in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from helpdesk.filter import DepartmentManagerFilter
from helpdesk.forms import DepartmentManagerCreateForm
from helpdesk.models import DepartmentManager
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="helpdesk.add_departmentmanager"), name="dispatch"
)
class DepartmentManagersListView(HorillaListView):
    """
    List view of the resticted days page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.action_method = "actions_col"
        self.view_id = "department_managers"
        self.search_url = reverse("department-manager-list")

    model = DepartmentManager
    filter_class = DepartmentManagerFilter
    show_toggle_form = False

    columns = [
        (_("Department"), "department"),
        (_("Manager"), "manager"),
    ]

    header_attrs = {
        "department": """
                   style = "width:200px !important"
                   """,
        "manager": """
                   style = "width:200px !important"
                   """,
    }

    sortby_mapping = [
        ("Department", "department__department"),
        ("Manager", "manager__get_full_name"),
    ]

    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
                    class="oh-btn oh-btn--light-bkg w-50"
                    hx-get="{get_update_url}?instance_ids={ordered_ids}"
                    hx-target="#genericModalBody"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-50"
                    hx-confirm="Are you sure you want to remove this department manager?"
                    hx-target="#dapartmentManagerTr{get_instance_id}"
                    hx-post="{get_delete_url}"
                    hx-swap="innerHTML"
                    """,
        },
    ]

    row_attrs = """
                id = "dapartmentManagerTr{get_instance_id}"
                """


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="helpdesk.add_departmentmanager"), name="dispatch"
)
class DepartmentManagersNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("department-manager-list")
        self.search_in = [
            ("department__department", _("Department")),
            (
                "manager__employee_first_name",
                "Manager",
            ),
        ]
        self.create_attrs = f"""
                            onclick = "event.stopPropagation();"
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('department-manager-create')}"
                            """

    nav_title = _("Department managers")
    filter_instance = DepartmentManagerFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="helpdesk.add_departmentmanager"), name="dispatch"
)
class DepartmentManagersFormView(HorillaFormView):
    """
    Create and edit form for Department Manager
    """

    model = DepartmentManager
    form_class = DepartmentManagerCreateForm
    new_display_title = _("Create department manager")

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form view.
        """
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update department manager")
        return context

    def form_valid(self, form: DepartmentManagerCreateForm) -> HttpResponse:
        """
        Handle a valid form submission.
        If the form is valid, save the instance and display a success message.
        """
        if form.is_valid():
            if form.instance.pk:
                message = _("The department manager updated successfully.")
            else:
                message = _("The department manager created successfully.")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)
