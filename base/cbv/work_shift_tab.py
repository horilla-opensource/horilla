"""
This page is handling the cbv methods of work type and shift tab in employee profile page.
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.cbv.rotating_shift_assign import (
    RotatingShiftDetailview,
    RotatingShiftListParent,
)
from base.cbv.rotating_work_type import GeneralParent, RotatingWorkDetailView
from base.cbv.shift_request import ShiftRequestList
from base.cbv.work_type_request import WorkRequestListView
from base.methods import filtersubordinates, is_reportingmanager
from base.models import WorkTypeRequest
from employee.models import Employee
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import HorillaTabView


class WorkAndShiftTabView(HorillaTabView):
    """
    generic tab view for work type and shift
    """

    template_name = "cbv/work_shift_tab/extended_work-shift.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "work-shift"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["emp_id"] = pk
        employee = Employee.objects.get(id=pk)
        context["employee"] = employee
        context["tabs"] = [
            {
                "title": _("Work type request"),
                "url": f"{reverse('employee-worktype-tab-list',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Add Work Type Request",
                        "attrs": f"""
                                hx-get="{reverse('work-type-request')}?emp_id={pk}",
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
                    }
                ],
            },
            {
                "title": _("Rotating work type"),
                "url": f"{reverse('employee-rotating-work-tab-list',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Add Rotating Work",
                        "attrs": f"""
                                hx-get="{reverse('rotating-work-type-assign-add')}?emp_id={pk}",
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
                    }
                ],
            },
            {
                "title": _("Shift request"),
                "url": f"{reverse('shift-request-individual-tab-view',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Add Shift Request",
                        "attrs": f"""
                                hx-get="{reverse('shift-request')}?emp_id={pk}",
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
                    }
                ],
            },
            {
                "title": _("Rotating Shift"),
                "url": f"{reverse('rotating-shift-individual-tab-view',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Add Rotating Shift",
                        "attrs": f"""
                                hx-get="{reverse('rotating-shift-assign-add')}?emp_id={pk}",
								hx-target="#genericModalBody"
								data-toggle="oh-modal-toggle"
								data-target="#genericModal"
                      """,
                    }
                ],
            },
        ]
        return context


class WorkTypeIndividualTabList(WorkRequestListView):
    """
    List view for work type tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("employee-worktype-tab-list", kwargs={"pk": pk})
        self.view_id = "work_target"

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = WorkTypeRequest.objects.filter(employee_id=pk)
        return queryset

    columns = [
        col for col in WorkRequestListView.columns if col[1] != "comment_note"
    ] + [(_("Status"), "request_status")]


class ShiftRequestIndividualTabView(ShiftRequestList):
    """
    List view for shift request tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "shift-reques-individual-div"
        self.selected_instances_key_id = "shiftselectedInstancesIndividual"
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse(
            "shift-request-individual-tab-view", kwargs={"pk": pk}
        )

    columns = [
        column for column in ShiftRequestList.columns if column[1] != "comment"
    ] + [(_("Status"), "request_status")]

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(employee_id=pk)
        return queryset


class RotatingShiftAssignIndividualView(RotatingShiftListParent):
    """
    List view for Rotating shift request tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse(
            "rotating-shift-individual-tab-view", kwargs={"pk": pk}
        )
        self.view_id = "rotating-div"

    columns = RotatingShiftListParent.columns + [
        (_("Status"), "check_active"),
    ]

    row_attrs = """
                hx-get='{rotating_shift_individual_detail}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(employee_id=pk)
        return queryset


class RotatingWorkIndividualTab(GeneralParent):
    """
    List view for rotating work type tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("employee-rotating-work-tab-list", kwargs={"pk": pk})
        self.view_id = "rotating-work-div"

    columns = GeneralParent.columns + [
        (_("Status"), "detail_is_active"),
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        queryset = queryset.filter(employee_id=pk)
        return queryset

    row_attrs = """
                hx-get='{individual_tab_work_rotate_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


# @method_decorator(login_required, name="dispatch")
# class DetailViewChild(RotatingWorkDetailView):
#     """
#     parent for detail view
#     """

#     @method_decorator(login_required, name="dispatch")
#     def dispatch(self, *args, **kwargs):
#         return super(RotatingWorkDetailView, self).dispatch(*args, **kwargs)

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         pk = self.kwargs.get("pk")
#         queryset = queryset.filter(pk=pk)
#         return queryset


class RotatingShiftAssignIndividualDetailView(RotatingShiftDetailview):
    """
    Individual rotating shift assign detail view
    """

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(RotatingShiftDetailview, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        obj = queryset.get(pk=pk)
        employee_id = obj.employee_id
        if is_reportingmanager(self.request):
            queryset = filtersubordinates(
                self.request, queryset, "base.view_rotatingshiftassign"
            ) | queryset.filter(employee_id=self.request.user.employee_get)
        elif self.request.user.has_perm("base.view_rotatingshiftassign"):
            queryset = queryset.filter(employee_id=employee_id)
        else:
            queryset = queryset.filter(employee_id=self.request.user.employee_get)
        return queryset


@method_decorator(login_required, name="dispatch")
class DetailViewChild(RotatingWorkDetailView):
    """
    parent for detail view
    """

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(RotatingWorkDetailView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        pk = self.kwargs.get("pk")
        obj = queryset.get(pk=pk)
        emp_id = obj.employee_id
        # queryset = queryset.filter(employee_id=emp_id)
        if is_reportingmanager(self.request):
            queryset = filtersubordinates(
                self.request, queryset, "base.view_rotatingworktypeassign"
            ) | queryset.filter(employee_id=self.request.user.employee_get)
        elif self.request.user.has_perm("base.view_rotatingworktypeassign"):
            queryset = queryset.filter(employee_id=emp_id)
        else:
            queryset = queryset.filter(employee_id=self.request.user.employee_get)

        return queryset
