from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from hydra_templates.forms import MessageTemplateForm, TemplateDataExportForm
from hydra_templates.models import MessageTemplate, TemplateDataExport
from hydra_templates.placeholders import PLACEHOLDERS
from hydra_templates.selectors import search_templates, template_for_user
from hydra_templates.services import (
    EXPORT_PERMISSIONS,
    create_template_data_export,
    preview_message_template,
    save_message_template,
)


def _template_form_view(request, *, template, page_title):
    form = MessageTemplateForm(
        request.POST or None,
        instance=template,
        actor=request.user,
    )
    preview = None
    if request.method == "POST" and form.is_valid():
        if request.POST.get("action") == "preview":
            preview = preview_message_template(
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"],
            )
        else:
            try:
                template = save_message_template(
                    template=form.save(commit=False),
                    actor=request.user,
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, _("Message template saved."))
                return redirect("hydra-template-list")
    return render(
        request,
        "hydra_templates/template_form.html",
        {
            "form": form,
            "message_template": template,
            "page_title": page_title,
            "placeholders": PLACEHOLDERS,
            "preview": preview,
        },
    )


@login_required
@permission_required("hydra_templates.view_messagetemplate", raise_exception=True)
def template_list(request):
    query = request.GET.get("q", "")
    recent_exports = TemplateDataExport.objects.none()
    if request.user.has_perm("hydra_templates.view_templatedataexport"):
        recent_exports = TemplateDataExport.objects.select_related("actor")
        if not request.user.is_superuser:
            recent_exports = recent_exports.filter(actor=request.user)
        recent_exports = recent_exports[:10]
    return render(
        request,
        "hydra_templates/template_list.html",
        {
            "templates": search_templates(user=request.user, query=query),
            "query": query,
            "placeholders": PLACEHOLDERS,
            "export_form": TemplateDataExportForm(actor=request.user),
            "recent_exports": recent_exports,
        },
    )


@login_required
@permission_required("hydra_templates.add_messagetemplate", raise_exception=True)
def template_create(request):
    return _template_form_view(
        request,
        template=MessageTemplate(),
        page_title=_("Create message template"),
    )


@login_required
@permission_required("hydra_templates.change_messagetemplate", raise_exception=True)
def template_update(request, template_uuid):
    template = template_for_user(
        user=request.user,
        template_uuid=template_uuid,
        permission="change_messagetemplate",
    )
    return _template_form_view(
        request,
        template=template,
        page_title=_("Edit message template"),
    )


@login_required
@require_POST
@permission_required(EXPORT_PERMISSIONS, raise_exception=True)
def template_data_export(request):
    form = TemplateDataExportForm(request.POST, actor=request.user)
    if not form.is_valid():
        messages.error(request, _("Choose a company from your active scope."))
        return redirect("hydra-template-list")
    try:
        payload, audit = create_template_data_export(
            actor=request.user,
            company=form.cleaned_data["company"],
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("hydra-template-list")
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{audit.filename}"'
    response["Content-Length"] = str(len(payload))
    response["Cache-Control"] = "no-store, private"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response
