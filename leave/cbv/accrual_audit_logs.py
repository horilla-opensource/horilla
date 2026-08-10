"""
CBV views for viewing leave accrual audit logs.
Read-only views showing all leave balance changes and accrual events.
Employees see only their own logs; HR/SuperAdmin see all.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla_views.cbv_methods import permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaListView,
)
from leave.filters import LeaveAccrualAuditLogFilter
from leave.models import LeaveAccrualAuditLog


@method_decorator(login_required, name="dispatch")
class LeaveAccrualAuditLogListView(HorillaListView):
    """
    List view for leave accrual audit logs.
    Employees see only their own logs.
    HR/SuperAdmin see all logs.
    """

    model = LeaveAccrualAuditLog
    filter_class = LeaveAccrualAuditLogFilter
    paginate_by = 50
    template_name = "cbv/leave_accrual/audit_log_list.html"

    columns = [
        (_("Employee"), "employee_id", "get_employee_name"),
        (_("Date"), "effective_date"),
        (_("Type"), "accrual_type"),
        (_("Old Balance"), "old_balance"),
        (_("New Balance"), "new_balance"),
        (_("Accrual Days"), "accrual_days"),
        (_("Reason"), "reason"),
    ]

    sortby_mapping = [
        (_("Employee"), "employee_id__badge_id"),
        (_("Date"), "effective_date"),
        (_("Type"), "accrual_type"),
        (_("Old Balance"), "old_balance"),
        (_("New Balance"), "new_balance"),
        (_("Accrual Days"), "accrual_days"),
    ]

    def get_queryset(self):
        """
        Filter logs based on user role:
        - Employees: only their own logs
        - HR/SuperAdmin: all logs
        """
        queryset = super().get_queryset().select_related("employee_id")
        user = self.request.user

        # Check if user is HR or SuperAdmin
        is_hr_admin = (
            user.groups.filter(name__in=["HR", "HR-JM"]).exists()
            or user.is_superuser
        )

        if not is_hr_admin:
            # Regular employee sees only their own logs
            if hasattr(user, "employee_get") and user.employee_get:
                queryset = queryset.filter(employee_id=user.employee_get)
            else:
                queryset = queryset.none()

        return queryset.order_by("-effective_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_hr_admin = (
            user.groups.filter(name__in=["HR", "HR-JM"]).exists()
            or user.is_superuser
        )
        context["is_hr_admin"] = is_hr_admin
        return context


@method_decorator(login_required, name="dispatch")
class LeaveAccrualAuditLogDetailView(HorillaDetailedView):
    """
    Detailed view for a single audit log entry.
    Shows full details of an accrual event.
    Employees can only view their own logs.
    """

    model = LeaveAccrualAuditLog
    template_name = "cbv/leave_accrual/audit_log_detail.html"

    def get_queryset(self):
        """
        Filter logs based on user role.
        """
        queryset = super().get_queryset()
        user = self.request.user

        # Check if user is HR or SuperAdmin
        is_hr_admin = (
            user.groups.filter(name__in=["HR", "HR-JM"]).exists()
            or user.is_superuser
        )

        if not is_hr_admin:
            # Regular employee sees only their own logs
            if hasattr(user, "employee_get") and user.employee_get:
                queryset = queryset.filter(employee_id=user.employee_get)
            else:
                queryset = queryset.none()

        return queryset.select_related("employee_id", "related_leave_type_id", "created_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audit_log = self.object
        context["audit_log"] = audit_log

        # Add type display
        type_display = dict(
            LeaveAccrualAuditLog.ACCRUAL_TYPE_CHOICES
        ).get(audit_log.accrual_type, audit_log.accrual_type)
        context["accrual_type_display"] = type_display

        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_leaveaccrualauditlog"), name="dispatch")
class LeaveAccrualAuditLogHRView(HorillaListView):
    """
    HR-specific audit log view with advanced filtering and export options.
    HR/SuperAdmin only.
    """

    model = LeaveAccrualAuditLog
    filter_class = LeaveAccrualAuditLogFilter
    paginate_by = 100
    template_name = "cbv/leave_accrual/audit_log_hr_view.html"

    columns = [
        (_("Employee"), "employee_id", "get_employee_name"),
        (_("Badge ID"), "employee_id__badge_id"),
        (_("Date"), "effective_date"),
        (_("Type"), "accrual_type"),
        (_("Old Balance"), "old_balance"),
        (_("New Balance"), "new_balance"),
        (_("Days"), "accrual_days"),
        (_("Leave Type"), "related_leave_type_id"),
        (_("Reason"), "reason"),
        (_("Created By"), "created_by"),
    ]

    sortby_mapping = [
        (_("Employee"), "employee_id__badge_id"),
        (_("Date"), "effective_date"),
        (_("Type"), "accrual_type"),
        (_("Old Balance"), "old_balance"),
        (_("New Balance"), "new_balance"),
    ]

    action_method = "audit_log_hr_actions"

    def get_queryset(self):
        """Get all audit logs for HR view"""
        queryset = super().get_queryset()
        return queryset.select_related(
            "employee_id",
            "related_leave_type_id",
            "created_by",
        ).order_by("-effective_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add summary statistics
        from django.db.models import Sum, Count
        queryset = self.get_queryset()
        
        context["total_accruals"] = queryset.count()
        context["total_credited"] = (
            queryset.filter(accrual_days__gt=0).aggregate(Sum("accrual_days"))[
                "accrual_days__sum"
            ]
            or 0
        )
        context["total_deducted"] = (
            abs(
                queryset.filter(accrual_days__lt=0).aggregate(Sum("accrual_days"))[
                    "accrual_days__sum"
                ]
            )
            or 0
        )
        
        return context
