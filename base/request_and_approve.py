"""
views.py

This module is used to map url patterns with request and approve methods in Dashboard.
"""

import json

from django.apps import apps
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from base.methods import filtersubordinates
from base.models import ShiftRequest, WorkTypeRequest
from horilla.decorators import login_required


def paginator_qry(qryset, page_number):
    """
    This method is used to paginate query set
    """
    paginator = Paginator(qryset, 10)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
def dashboard_shift_request(request):
    requests = ShiftRequest.objects.filter(
        approved=False, canceled=False, employee_id__is_active=True
    )
    requests = filtersubordinates(request, requests, "base.add_shiftrequest")
    requests_ids = json.dumps([instance.id for instance in requests])
    return render(
        request,
        "request_and_approve/shift_request.html",
        {
            "requests": requests,
            "requests_ids": requests_ids,
        },
    )


@login_required
def dashboard_work_type_request(request):
    requests = WorkTypeRequest.objects.filter(
        approved=False, canceled=False, employee_id__is_active=True
    )
    requests = filtersubordinates(request, requests, "base.add_worktyperequest")
    requests_ids = json.dumps([instance.id for instance in requests])
    return render(
        request,
        "request_and_approve/work_type_request.html",
        {
            "requests": requests,
            "requests_ids": requests_ids,
        },
    )
