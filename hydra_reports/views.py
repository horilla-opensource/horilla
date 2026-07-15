from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from hydra_people.models import Person
from hydra_reports.forms import OperationalReportFilterForm
from hydra_reports.models import OperationalReportExport
from hydra_reports.selectors import (
    REPORT_VIEW_PERMISSIONS,
    OperationalReportSummary,
    operational_people_for_user,
    operational_report_rows,
    operational_report_summary,
)
from hydra_reports.services import (
    EXPORT_PERMISSIONS,
    create_operational_report_export,
)


REPORT_PAGE_SIZE = 50


@login_required
@permission_required(REPORT_VIEW_PERMISSIONS, raise_exception=True)
def operational_report(request):
    form = OperationalReportFilterForm(request.GET, actor=request.user)
    if form.is_valid():
        people = operational_people_for_user(
            user=request.user,
            filters=form.cleaned_data,
        )
        summary = operational_report_summary(user=request.user, people=people)
    else:
        people = Person.objects.none()
        summary = OperationalReportSummary(0, 0, 0, 0)

    page_obj = Paginator(people, REPORT_PAGE_SIZE).get_page(request.GET.get("page"))
    rows = operational_report_rows(
        user=request.user,
        people=page_obj.object_list,
        filters=form.cleaned_data if not form.errors else {},
    )
    query_parameters = request.GET.copy()
    query_parameters.pop("page", None)

    recent_exports = OperationalReportExport.objects.none()
    if request.user.has_perm("hydra_reports.view_operationalreportexport"):
        recent_exports = OperationalReportExport.objects.select_related("actor")
        if not request.user.is_superuser:
            recent_exports = recent_exports.filter(actor=request.user)
        recent_exports = recent_exports[:10]

    return render(
        request,
        "hydra_reports/operational_report.html",
        {
            "form": form,
            "filters_valid": not form.errors,
            "summary": summary,
            "rows": rows,
            "page_obj": page_obj,
            "query_parameters": query_parameters.urlencode(),
            "recent_exports": recent_exports,
        },
    )


@login_required
@require_POST
@permission_required(EXPORT_PERMISSIONS, raise_exception=True)
def operational_report_export(request):
    form = OperationalReportFilterForm(request.POST, actor=request.user)
    if not form.is_valid():
        messages.error(
            request,
            _("Report export filters must remain inside your active Hydra scope."),
        )
        return redirect("hydra-operational-report")
    try:
        payload, audit = create_operational_report_export(
            actor=request.user,
            filters=form.cleaned_data,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("hydra-operational-report")

    response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{audit.filename}"'
    response["Content-Length"] = str(len(payload))
    response["Cache-Control"] = "no-store, private"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response
