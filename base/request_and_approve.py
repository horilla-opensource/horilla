"""
views.py

This module is used to map url patterns with request and approve methods in Dashboard.
"""

import json
from django.shortcuts import render
from base.models import ShiftRequest, WorkTypeRequest
from employee.not_in_out_dashboard import paginator_qry
from horilla.decorators import login_required


@login_required
def dashboard_shift_request(request):
    requests = ShiftRequest.objects.filter(approved= False,canceled = False)
    requests_ids = json.dumps(
        [
            instance.id for instance in requests
        ]
    )
    return render(request, "request_and_approve/shift_request.html",{"requests": requests,"requests_ids": requests_ids,})


@login_required
def dashboard_work_type_request(request):
    requests = WorkTypeRequest.objects.filter(approved= False,canceled = False)
    requests_ids = json.dumps(
        [
            instance.id for instance in requests
        ]
    )
    return render(request, "request_and_approve/work_type_request.html",{"requests": requests,"requests_ids": requests_ids,})