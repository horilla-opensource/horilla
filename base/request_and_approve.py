"""
views.py

This module is used to map url patterns with request and approve methods in Dashboard.
"""

import json

from django.apps import apps
from django.shortcuts import render

from base.methods import filtersubordinates, paginator_qry
from base.models import ShiftRequest, WorkTypeRequest
from horilla.decorators import login_required


@login_required
def dashboard_shift_request(request):
    page_number = request.GET.get("page")
    previous_data = request.GET.urlencode()
    requests = ShiftRequest.objects.filter(
        approved=False, canceled=False, employee_id__is_active=True
    )
    requests = filtersubordinates(request, requests, "base.add_shiftrequest")
    requests_ids = json.dumps([instance.id for instance in requests])
    requests = paginator_qry(requests, page_number)
    return render(
        request,
        "request_and_approve/shift_request.html",
        {
            "requests": requests,
            "requests_ids": requests_ids,
            "pd": previous_data,
        },
    )


@login_required
def dashboard_work_type_request(request):
    page_number = request.GET.get("page")
    previous_data = request.GET.urlencode()
    requests = WorkTypeRequest.objects.filter(
        approved=False, canceled=False, employee_id__is_active=True
    )
    requests = filtersubordinates(request, requests, "base.add_worktyperequest")
    requests_ids = json.dumps([instance.id for instance in requests])
    requests = paginator_qry(requests, page_number)
    return render(
        request,
        "request_and_approve/work_type_request.html",
        {
            "requests": requests,
            "requests_ids": requests_ids,
            "pd": previous_data,
        },
    )
