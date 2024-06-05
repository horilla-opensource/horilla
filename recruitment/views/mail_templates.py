"""
offerletter.py

This module is related offerletter feature in Horilla
"""

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from horilla.decorators import hx_request_required, login_required, permission_required
from recruitment.forms import OfferLetterForm
from recruitment.models import Candidate, RecruitmentMailTemplate


@login_required
@permission_required("recruitment.view_recruitmentmailtemplate")
def view_mail_templates(request):
    """
    This method will render template to disply the offerletter templates
    """
    templates = RecruitmentMailTemplate.objects.all()
    form = OfferLetterForm()
    if templates.exists():
        template = "offerletter/view_templates.html"
    else:
        template = "offerletter/empty_mail_template.html"
    searchWords = form.get_template_language()
    return render(
        request,
        template,
        {"templates": templates, "form": form, "searchWords": searchWords},
    )


@login_required
@hx_request_required
@permission_required("recruitment.change_recruitmentmailtemplate")
def view_letter(request, obj_id):
    """
    This method is used to display the template/form to edit
    """
    template = RecruitmentMailTemplate.objects.get(id=obj_id)
    form = OfferLetterForm(instance=template)
    searchWords = form.get_template_language()
    if request.method == "POST":
        form = OfferLetterForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, "Template updated")
            return HttpResponse("<script>window.location.reload()</script>")

    return render(
        request,
        "offerletter/htmx/form.html",
        {"form": form, "duplicate": False, "searchWords": searchWords},
    )


@login_required
@require_http_methods(["POST"])
@permission_required("recruitment.add_recruitmentmailtemplate")
def create_letter(request):
    """
    This method is used to create offerletter template
    """
    if request.method == "POST":
        form = OfferLetterForm(request.POST)
        if form.is_valid():
            instance = form.save()
            instance.save()
            messages.success(request, "Template created")
            return HttpResponse("<script>window.location.reload()</script>")
    return redirect(view_mail_templates)


@login_required
@permission_required("recruitment.delete_recruitmentmailtemplate")
def delete_mail_templates(request):
    ids = request.GET.getlist("ids")
    result = RecruitmentMailTemplate.objects.filter(id__in=ids).delete()
    messages.success(request, "Template deleted")
    return redirect(view_mail_templates)


from django import template


@login_required
def get_template(request, obj_id=None):
    """
    This method is used to return the mail template
    """
    if obj_id:
        body = RecruitmentMailTemplate.objects.get(id=obj_id).body
        template_bdy = template.Template(body)
    if request.GET.get("word"):
        word = request.GET.get("word")
        template_bdy = template.Template("{{" + word + "}}")
    candidate_id = request.GET.get("candidate_id")
    if candidate_id:
        candidate_obj = Candidate.objects.get(id=candidate_id)
        context = template.Context(
            {"instance": candidate_obj, "self": request.user.employee_get}
        )
        body = template_bdy.render(context) or " "
    return JsonResponse({"body": body})
