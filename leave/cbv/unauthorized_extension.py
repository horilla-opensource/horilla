"""
CBV views for managing unauthorized extension records.
Tracks when employees don't return on approved paid leave date.
Only HR/SuperAdmin can manage these records.
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
from leave.filters import UnauthorizedExtensionFilter
from leave.forms import UnauthorizedExtensionForm
from leave.models import UnauthorizedExtension


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.add_unauthorizedextension"), name="dispatch")
class UnauthorizedExtensionListView(HorillaListView):
    """
    List view for all unauthorized extension records.
    HR/SuperAdmin only.
    Shows extensions when employees didn't return on approved date.
    """

    model = UnauthorizedExtension
    filter_class = UnauthorizedExtensionFilter
    paginate_by = 20
    template_name = "cbv/leave_accrual/unauthorized_extension_list.html"

    columns = [
        (_("Employee"), "employee_id", "get_employee_name"),
        (_("Approved Return"), "approved_return_date"),
        (_("Actual Return"), "actual_return_date"),
        (_("Days"), "unauthorized_days"),
        (_("Status"), "status"),
        (_("Remarks"), "remarks"),
    ]

    action_method = "unauthorized_extension_list_actions"
    sortby_mapping = [
        (_("Employee"), "employee_id__badge_id"),
        (_("Approved Return"), "approved_return_date"),
        (_("Actual Return"), "actual_return_date"),
        (_("Days"), "unauthorized_days"),
        (_("Status"), "status"),
    ]

    def get_queryset(self):
        """Filter to company leave requests"""
        queryset = super().get_queryset()
        return queryset.select_related("employee_id", "leave_request_id")


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_unauthorizedextension"), name="dispatch")
class UnauthorizedExtensionDetailView(HorillaDetailedView):
    """
    Detailed view for a single unauthorized extension record.
    Shows full details, related leave request, and impact on service.
    """

    model = UnauthorizedExtension
    template_name = "cbv/leave_accrual/unauthorized_extension_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unauthorized_ext = self.object
        context["unauthorized_extension"] = unauthorized_ext
        # Calculate impact on service
        context["service_impact"] = unauthorized_ext.unauthorized_days
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.add_unauthorizedextension"), name="dispatch")
class UnauthorizedExtensionCreateView(HorillaFormView):
    """
    Create a new unauthorized extension record.
    HR/SuperAdmin only. Called when employee doesn't return on approved date.
    """

    model = UnauthorizedExtension
    form_class = UnauthorizedExtensionForm
    template_name = "cbv/leave_accrual/unauthorized_extension_form.html"
    success_url = reverse_lazy("unauthorized-extension-list")

    def form_valid(self, form):
        """Save the form and calculate unauthorized_days"""
        instance = form.save(commit=False)
        # Calculate unauthorized days
        instance.unauthorized_days = (
            instance.actual_return_date - instance.approved_return_date
        ).days
        # Set created_by to current user's employee record
        if hasattr(self.request.user, "employee_get"):
            instance.created_by = self.request.user.employee_get
        instance.save()
        messages.success(
            self.request,
            _(
                f"Unauthorized extension record created for {instance.unauthorized_days} days. "
                "This period will be excluded from service calculations."
            ),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = _("Create")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.change_unauthorizedextension"), name="dispatch")
class UnauthorizedExtensionUpdateView(HorillaFormView):
    """
    Update an existing unauthorized extension record.
    HR/SuperAdmin only.
    """

    model = UnauthorizedExtension
    form_class = UnauthorizedExtensionForm
    template_name = "cbv/leave_accrual/unauthorized_extension_form.html"
    success_url = reverse_lazy("unauthorized-extension-list")

    def form_valid(self, form):
        """Save the form and recalculate unauthorized_days"""
        instance = form.save(commit=False)
        # Recalculate unauthorized days
        instance.unauthorized_days = (
            instance.actual_return_date - instance.approved_return_date
        ).days
        instance.save()
        messages.success(
            self.request,
            _(
                f"Unauthorized extension record updated. "
                f"Total unauthorized days: {instance.unauthorized_days}. "
                "Service calculation has been adjusted."
            ),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = _("Update")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.delete_unauthorizedextension"), name="dispatch")
class UnauthorizedExtensionDeleteView(HorillaFormView):
    """
    Delete an unauthorized extension record.
    HR/SuperAdmin only. Removes service exclusion.
    """

    model = UnauthorizedExtension
    template_name = "cbv/leave_accrual/unauthorized_extension_confirm_delete.html"
    success_url = reverse_lazy("unauthorized-extension-list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(
            request,
            _("Unauthorized extension record deleted. Service calculation updated."),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        return context
