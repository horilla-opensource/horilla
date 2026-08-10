"""
CBV views for managing unpaid leave records.
Only HR/SuperAdmin can create/edit unpaid leaves.
"""

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.models import Company
from employee.models import Employee
from horilla_views.cbv_methods import permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
)
from leave.filters import UnpaidLeaveFilter
from leave.forms import UnpaidLeaveForm
from leave.models import UnpaidLeave


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.add_unpaidleave"), name="dispatch")
class UnpaidLeaveListView(HorillaListView):
    """
    List view for all unpaid leave records.
    HR/SuperAdmin only.
    """

    model = UnpaidLeave
    filter_class = UnpaidLeaveFilter
    paginate_by = 20
    template_name = "cbv/leave_accrual/unpaid_leave_list.html"

    columns = [
        (_("Employee"), "employee_id", "get_employee_name"),
        (_("Start Date"), "start_date"),
        (_("End Date"), "end_date"),
        (_("Days"), "days_count"),
        (_("Status"), "status"),
        (_("Reason"), "reason"),
    ]

    action_method = "unpaid_leave_list_actions"
    sortby_mapping = [
        (_("Employee"), "employee_id__badge_id"),
        (_("Start Date"), "start_date"),
        (_("End Date"), "end_date"),
        (_("Days"), "days_count"),
        (_("Status"), "status"),
    ]

    def get_queryset(self):
        """Filter to company employees"""
        queryset = super().get_queryset()
        # Add company filter if needed
        return queryset.select_related("employee_id")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_unpaidleave"), name="dispatch")
class UnpaidLeaveDetailView(HorillaDetailedView):
    """
    Detailed view for a single unpaid leave record.
    Shows full details and related audit logs.
    """

    model = UnpaidLeave
    template_name = "cbv/leave_accrual/unpaid_leave_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unpaid_leave = self.object
        context["unpaid_leave"] = unpaid_leave
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.add_unpaidleave"), name="dispatch")
class UnpaidLeaveCreateView(HorillaFormView):
    """
    Create a new unpaid leave record.
    HR/SuperAdmin only.
    """

    model = UnpaidLeave
    form_class = UnpaidLeaveForm
    template_name = "cbv/leave_accrual/unpaid_leave_form.html"
    success_url = reverse_lazy("unpaid-leave-list")

    def form_valid(self, form):
        """Save the form and calculate days_count"""
        instance = form.save(commit=False)
        # Calculate days count
        instance.days_count = (instance.end_date - instance.start_date).days
        # Set created_by to current user's employee record
        if hasattr(self.request.user, "employee_get"):
            instance.created_by = self.request.user.employee_get
        instance.save()
        messages.success(
            self.request,
            _("Unpaid leave record created successfully. Accrual has been paused."),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = _("Create")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.change_unpaidleave"), name="dispatch")
class UnpaidLeaveUpdateView(HorillaFormView):
    """
    Update an existing unpaid leave record.
    HR/SuperAdmin only.
    """

    model = UnpaidLeave
    form_class = UnpaidLeaveForm
    template_name = "cbv/leave_accrual/unpaid_leave_form.html"
    success_url = reverse_lazy("unpaid-leave-list")

    def form_valid(self, form):
        """Save the form and recalculate days_count"""
        instance = form.save(commit=False)
        # Recalculate days count
        instance.days_count = (instance.end_date - instance.start_date).days
        instance.save()
        messages.success(
            self.request,
            _(
                "Unpaid leave record updated successfully. "
                "Accrual status has been adjusted accordingly."
            ),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = _("Update")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.delete_unpaidleave"), name="dispatch")
class UnpaidLeaveDeleteView(HorillaFormView):
    """
    Delete an unpaid leave record.
    HR/SuperAdmin only.
    """

    model = UnpaidLeave
    template_name = "cbv/leave_accrual/unpaid_leave_confirm_delete.html"
    success_url = reverse_lazy("unpaid-leave-list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(
            request,
            _("Unpaid leave record deleted successfully. Accrual has been resumed."),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        return context
