import json

from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from horilla.decorators import login_required
from report.models import ReportTemplate


@login_required
@require_http_methods(["GET"])
def list_report_templates(request):
    """
    List the current user's saved templates for a given report (identified
    by report_slug, e.g. "employee_report").
    """
    report_slug = request.GET.get("report_slug")
    templates = ReportTemplate.objects.filter(
        report_slug=report_slug, created_by=request.user
    ).values("id", "name")
    return JsonResponse({"templates": list(templates)})


@login_required
@require_http_methods(["POST"])
def save_report_template(request):
    """
    Save (or overwrite, if the same name already exists for this user and
    report) the current field arrangement as a named template.
    """
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    report_slug = body.get("report_slug")
    name = (body.get("name") or "").strip()
    config = body.get("config")

    if not report_slug or not name or config is None:
        messages.error(request, _("report_slug, name and config are all required."))
        return JsonResponse(
            {"error": "report_slug, name and config are all required."}, status=400
        )

    template, _created = ReportTemplate.objects.update_or_create(
        report_slug=report_slug,
        name=name,
        created_by=request.user,
        defaults={"config": config},
    )
    messages.success(request, _("Template saved."))
    return JsonResponse({"id": template.id, "name": template.name})


@login_required
@require_http_methods(["GET"])
def get_report_template(request, template_id):
    """
    Fetch a saved template's field arrangement so it can be re-applied to
    the pivot table.
    """
    template = ReportTemplate.objects.filter(
        id=template_id, created_by=request.user
    ).first()
    if not template:
        return JsonResponse({"error": "Template not found."}, status=404)
    return JsonResponse(
        {"id": template.id, "name": template.name, "config": template.config}
    )


@login_required
@require_http_methods(["POST"])
def delete_report_template(request, template_id):
    deleted, _deleted_details = ReportTemplate.objects.filter(
        id=template_id, created_by=request.user
    ).delete()
    if not deleted:
        messages.error(request, _("Template not found."))
        return JsonResponse({"error": "Template not found."}, status=404)
    messages.success(request, _("Template deleted."))
    return JsonResponse({"success": True})
