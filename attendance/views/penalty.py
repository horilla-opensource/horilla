"""
attendance/views/penalty.py

This module is used to write late come early out penatly methods
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from attendance.filters import PenaltyFilter
from attendance.forms import PenaltyAccountForm
from attendance.models import AttendanceLateComeEarlyOut, PenaltyAccount
from employee.models import Employee
from horilla.decorators import hx_request_required, login_required, manager_can_enter
from leave.models import AvailableLeave


@login_required
@hx_request_required
@manager_can_enter("leave.change_availableleave")
def cut_available_leave(request, instance_id):
    """
    This method is used to create the penalties
    """
    late_in_early_out_ids = (
        request.GET.get("instances_ids", None)
        if request.GET.get("instances_ids") != "None"
        else None
    )
    request_copy = request.GET.copy()
    request_copy.pop("instances_ids", None)
    previous_data = request_copy.urlencode()
    instance = AttendanceLateComeEarlyOut.objects.get(id=instance_id)
    form = PenaltyAccountForm(employee=instance.employee_id)
    available = AvailableLeave.objects.filter(employee_id=instance.employee_id)
    if request.method == "POST":
        form = PenaltyAccountForm(request.POST)
        if form.is_valid():
            penalty_instance = form.instance
            penalty = PenaltyAccount()
            # late come early out id
            penalty.late_early_id = instance
            penalty.deduct_from_carry_forward = (
                penalty_instance.deduct_from_carry_forward
            )
            penalty.employee_id = instance.employee_id
            penalty.leave_type_id = penalty_instance.leave_type_id
            penalty.minus_leaves = penalty_instance.minus_leaves
            penalty.penalty_amount = penalty_instance.penalty_amount
            penalty.save()
            messages.success(request, _("Penalty/Fine added"))
            form = PenaltyAccountForm()
    return render(
        request,
        "attendance/penalty/form.html",
        {
            "available": available,
            "late_in_early_out_ids": late_in_early_out_ids,
            "form": form,
            "instance": instance,
            "pd": previous_data,
        },
    )


@login_required
@hx_request_required
def view_penalties(request):
    """
    This method is used to filter or view the penalties
    """
    records = PenaltyFilter(request.GET).qs
    return render(request, "attendance/penalty/penalty_view.html", {"records": records})
