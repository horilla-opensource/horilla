"""
This page handles the cbv methods of employee individual view
"""

from django.contrib import messages
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from base import views as base_views
from base.cbv.mail_log_tab import MailLogTabList
from base.cbv.work_shift_tab import WorkAndShiftTabView
from base.context_processors import enable_profile_edit
from base.forms import AddToUserGroupForm
from employee import views
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla import settings
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaProfileView

Employee.cbv_employee_profile_edi_url = reverse_lazy("edit-profile")


class EmployeeProfileView(HorillaProfileView):
    """
    EmployeeProfileView
    """

    template_name = "cbv/profile/profile_view.html"

    model = Employee
    filter_class = EmployeeFilter
    push_url = "employee-view-individual"
    key_name = "obj_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        employee = self.request.user.employee_get
        if self.request.user.has_perm("employee.change_employee"):

            self.actions = [
                {
                    "title": "Edit",
                    "src": f"/{settings.STATIC_URL}images/ui/editing.png",
                    "accessibility": "employee.cbv.accessibility.edit_accessibility",
                    "attrs": """
                    onclick="window.location.href='{get_update_url}'"
                    """,
                },
                {
                    "title": "Block Account",
                    "src": f"/{settings.STATIC_URL}images/ui/block-user.png",
                    "accessibility": "employee.cbv.accessibility.block_account_accessibility",
                    "attrs": """
                    id="block-account"
                    """,
                },
                {
                    "title": "Un-Block Account",
                    "src": f"/{settings.STATIC_URL}images/ui/unlock.png",
                    "accessibility": "employee.cbv.accessibility.un_block_account_accessibility",
                    "attrs": """
                    id="block-account"
                    """,
                },
                {
                    "title": "Send password reset link",
                    "src": f"/{settings.STATIC_URL}images/ui/key.png",
                    "accessibility": "employee.cbv.accessibility.password_reset_accessibility",
                    "attrs": """
                    onclick="$('#reset-button').click();"
                    """,
                },
            ]
        elif employee.pk == kwargs["pk"] and enable_profile_edit(self.request).get(
            "profile_edit_enabled"
        ):
            self.actions = [
                {
                    "title": "Edit Profile",
                    "src": f"/{settings.STATIC_URL}images/ui/editing.png",
                    "accessibility": "employee.cbv.accessibility.edit_accessibility",
                    "attrs": """
                    onclick="window.location.href='{cbv_employee_profile_edi_url}'"
                    """,
                },
                {
                    "title": "Send password reset link",
                    "src": f"/{settings.STATIC_URL}images/ui/key.png",
                    "accessibility": "employee.cbv.accessibility.password_reset_accessibility",
                    "attrs": """
                    onclick="$('#reset-button').click();"
                    """,
                },
            ]


EmployeeProfileView.add_tab(
    tabs=[
        {
            "title": "About",
            "view": views.about_tab,
        },
        {
            "title": "Work Type & Shift",
            # "view": views.shift_tab,
            "view": WorkAndShiftTabView.as_view(),
            "accessibility": "employee.cbv.accessibility.workshift_accessibility",
        },
        {
            "title": "Groups & Permissions",
            "view": base_views.employee_permission_assign,
            "accessibility": "employee.cbv.accessibility.permission_accessibility",
        },
        {
            "title": "Note",
            "view": views.note_tab,
            "accessibility": "employee.cbv.accessibility.note_accessibility",
        },
        {
            "title": "Documents",
            "view": views.document_tab,
            "accessibility": "employee.cbv.accessibility.document_accessibility",
        },
        {
            "title": "Mail Log",
            "view": MailLogTabList.as_view(),
            "accessibility": "employee.cbv.accessibility.mail_log_accessibility",
        },
        {
            "title": "History",
            "view": views.history_tab,
            "accessibility": "employee.cbv.accessibility.history_accessibility",
        },
    ]
)


@method_decorator(
    [login_required, permission_required("auth.add_group")], name="dispatch"
)
class GroupAssignView(View):
    """
    View to assign multiple groups to a single employee
    """

    def get(self, request, *args, **kwargs):
        employee_id = request.GET.get("employee")
        employee = Employee.objects.get(id=employee_id)
        groups = employee.employee_user_id.groups.all
        form = AddToUserGroupForm(
            initial={
                "group": groups,
                "employee": request.GET.get("employee"),
            }
        )
        return render(
            request,
            "cbv/auth/user_assign_to_group.html",
            {"form": form, "employee_id": request.GET.get("employee")},
        )

    def post(self, request, *args, **kwargs):
        form = AddToUserGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Employee assigned to group"))
            return HttpResponse("<script>window.location.reload()</script>")
        return render(
            request,
            "cbv/auth/user_assign_to_group.html",
            {"form": form, "employee_id": request.POST.get("employee")},
        )
