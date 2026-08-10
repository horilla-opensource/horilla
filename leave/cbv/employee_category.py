"""
CBV views for managing employee categories and leave accrual configuration.
Used by HR to define badge ID prefixes and carryforward limits.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
)
from leave.forms import EmployeeCategoryForm
from leave.models import EmployeeCategory


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_employeecategory"), name="dispatch")
class EmployeeCategoryListView(HorillaListView):
    """
    List view for all employee categories.
    Shows all badge ID prefixes and their carryforward limits.
    """

    model = EmployeeCategory
    paginate_by = 20
    template_name = "cbv/leave_accrual/employee_category_list.html"

    columns = [
        (_("Category Name"), "name"),
        (_("Badge Prefix"), "badge_id_prefix"),
        (_("Max Carryforward"), "max_carryforward_days"),
    ]

    action_method = "employee_category_list_actions"
    sortby_mapping = [
        (_("Category Name"), "name"),
        (_("Badge Prefix"), "badge_id_prefix"),
        (_("Max Carryforward"), "max_carryforward_days"),
    ]

    def get_queryset(self):
        """Get all categories for this company"""
        queryset = super().get_queryset()
        # Filter by company if needed
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.view_employeecategory"), name="dispatch")
class EmployeeCategoryDetailView(HorillaDetailedView):
    """
    Detailed view for a single employee category.
    Shows category details and count of employees in this category.
    """

    model = EmployeeCategory
    template_name = "cbv/leave_accrual/employee_category_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        context["category"] = category
        
        # Count employees in this category
        from employee.models import Employee
        if category.badge_id_prefix:
            employee_count = Employee.objects.filter(
                badge_id__startswith=category.badge_id_prefix
            ).count()
        else:
            employee_count = 0
        context["employee_count"] = employee_count
        
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.add_employeecategory"), name="dispatch")
class EmployeeCategoryCreateView(HorillaFormView):
    """
    Create a new employee category.
    HR/SuperAdmin only.
    """

    model = EmployeeCategory
    form_class = EmployeeCategoryForm
    template_name = "cbv/leave_accrual/employee_category_form.html"
    success_url = reverse_lazy("employee-category-list")

    def form_valid(self, form):
        """Save the category"""
        instance = form.save(commit=False)
        # Set company from request context if available
        if hasattr(self.request, "user") and hasattr(self.request.user, "employee_get"):
            employee = self.request.user.employee_get
            if employee and employee.company_id:
                instance.company_id = employee.company_id
        instance.save()
        messages.success(
            self.request,
            _(
                f"Employee category '{instance.name}' created. "
                f"Employees with prefix '{instance.badge_id_prefix}' "
                f"will have max {instance.max_carryforward_days} days carryforward."
            ),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = _("Create")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.change_employeecategory"), name="dispatch")
class EmployeeCategoryUpdateView(HorillaFormView):
    """
    Update an existing employee category.
    HR/SuperAdmin only.
    """

    model = EmployeeCategory
    form_class = EmployeeCategoryForm
    template_name = "cbv/leave_accrual/employee_category_form.html"
    success_url = reverse_lazy("employee-category-list")

    def form_valid(self, form):
        """Save the updated category"""
        instance = form.save()
        messages.success(
            self.request,
            _(
                f"Employee category '{instance.name}' updated. "
                f"Max carryforward now: {instance.max_carryforward_days} days."
            ),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = _("Update")
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="leave.delete_employeecategory"), name="dispatch")
class EmployeeCategoryDeleteView(HorillaFormView):
    """
    Delete an employee category.
    HR/SuperAdmin only. Careful - may affect active categories.
    """

    model = EmployeeCategory
    template_name = "cbv/leave_accrual/employee_category_confirm_delete.html"
    success_url = reverse_lazy("employee-category-list")

    def get(self, request, *args, **kwargs):
        from django.shortcuts import render
        self.object = self.get_object()
        # Count affected employees
        from employee.models import Employee
        if self.object.badge_id_prefix:
            affected_count = Employee.objects.filter(
                badge_id__startswith=self.object.badge_id_prefix
            ).count()
        else:
            affected_count = 0
        context = self.get_context_data(object=self.object)
        context["affected_count"] = affected_count
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        category_name = self.object.name
        self.object.delete()
        messages.warning(
            request,
            _(
                f"Employee category '{category_name}' deleted. "
                "Affected employees will use default carryforward rules."
            ),
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        return context
