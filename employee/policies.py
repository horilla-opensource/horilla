"""
policies.py

This module is used to write operation related to policies
"""

import json
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from base.views import paginator_qry
from urllib.parse import parse_qs
from employee.filters import DisciplinaryActionFilter, PolicyFilter
from employee.forms import DisciplinaryActionForm, PolicyForm
from employee.models import Actiontype, DisciplinaryAction, Policy, PolicyMultipleFile
from horilla.decorators import permission_required, login_required
from django.utils.translation import gettext_lazy as _
from notifications.signals import notify
from base.methods import (
    get_key_instances,
)


@login_required
def view_policies(request):
    """
    Method is used render template to view all the policy records
    """
    policies = Policy.objects.all()
    if not request.user.has_perm("employee.view_policy"):
        policies = policies.filter(is_visible_to_all=True)
    return render(
        request,
        "policies/view_policies.html",
        {"policies": paginator_qry(policies, request.GET.get("page"))},
    )


@login_required
@permission_required("employee.add_policy")
def create_policy(request):
    """
    Method is used to create/update new policy
    """
    instance_id = request.GET.get("instance_id")
    instance = None
    if isinstance(eval(str(instance_id)), int):
        instance = Policy.objects.filter(id=instance_id).first()
    form = PolicyForm(instance=instance)
    if request.method == "POST":
        form = PolicyForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy saved")
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "policies/form.html", {"form": form})


@login_required
def search_policies(request):
    """
    This method is used to search in policies
    """
    policies = PolicyFilter(request.GET).qs
    if not request.user.has_perm("employee.view_policy"):
        policies = policies.filter(is_visible_to_all=True)
    return render(
        request,
        "policies/records.html",
        {
            "policies": paginator_qry(policies, request.GET.get("page")),
            "pd": request.GET.urlencode(),
        },
    )


@login_required
def view_policy(request):
    """
    This method is used to view the policy
    """
    instance_id = request.GET["instance_id"]
    policy = Policy.objects.filter(id=instance_id).first()
    return render(
        request,
        "policies/view_policy.html",
        {
            "policy": policy,
        },
    )


@login_required
@permission_required("employee.delete_policy")
def delete_policies(request):
    """
    This method is to delete policy
    """
    ids = request.GET.getlist("ids")
    Policy.objects.filter(id__in=ids).delete()
    messages.success(request, "Policies deleted")
    return redirect(view_policies)


@login_required
@permission_required("employee.change_policy")
def add_attachment(request):
    """
    This method is used to add attachment to policy
    """
    files = request.FILES.getlist("files")
    policy_id = request.GET["policy_id"]
    attachments = []
    for file in files:
        attachment = PolicyMultipleFile()
        attachment.attachment = file
        attachment.save()
        attachments.append(attachment)
    policy = Policy.objects.get(id=policy_id)
    policy.attachments.add(*attachments)
    messages.success(request, "Attachments added")
    return render(request, "policies/attachments.html", {"policy": policy})


@login_required
@permission_required("employee.delete_policy")
def remove_attachment(request):
    """
    This method is used to remove the attachments
    """
    ids = request.GET.getlist("ids")
    policy_id = request.GET["policy_id"]
    policy = Policy.objects.get(id=policy_id)
    PolicyMultipleFile.objects.filter(id__in=ids).delete()
    return render(request, "policies/attachments.html", {"policy": policy})


@login_required
def get_attachments(request):
    """
    This method is used to view all the attachments inside the policy
    """
    policy = request.GET["policy_id"]
    policy = Policy.objects.get(id=policy)
    return render(request, "policies/attachments.html", {"policy": policy})


@login_required
def disciplinary_actions(request):
    """
    This method is used to view all Disciplinaryaction
    """
    form = DisciplinaryActionFilter()
    queryset = DisciplinaryAction.objects.all()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    previous_data = request.GET.urlencode()

    return render(
        request,
        "disciplinary_actions/disciplinary_nav.html",
        {
            "data": page_obj,
            "pd": previous_data,
            "f": form,
        },
    )


@login_required
@permission_required("employee.add_disciplinaryaction")
def create_actions(request):
    """
    Method is used to create Disciplinaryaction
    """
    form = DisciplinaryActionForm()
    employees = []
    if request.method == "POST":
        form = DisciplinaryActionForm(request.POST, request.FILES)
        if form.is_valid():
            employee_ids = form.cleaned_data["employee_id"]

            for employee in employee_ids:
                user = employee.employee_user_id
                employees.append(user)
            form.save()
            messages.success(request, _("Disciplinary action taken."))
            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb="Disciplinary action is taken on you.",
                verb_ar="تم اتخاذ إجراء disziplinarisch ضدك.",
                verb_de="Disziplinarische Maßnahmen wurden gegen Sie ergriffen.",
                verb_es="Se ha tomado acción disciplinaria en tu contra.",
                verb_fr="Des mesures disciplinaires ont été prises à votre encontre.",
                redirect="/employee/disciplinary-actions/",
                icon="chatbox-ellipses",
            )

    return render(request, "disciplinary_actions/form.html", {"form": form})


@login_required
@permission_required("employee.change_disciplinaryaction")
def update_actions(request, action_id):
    """
    Method is used to update Disciplinaryaction
    """

    action = DisciplinaryAction.objects.get(id=action_id)
    form = DisciplinaryActionForm(instance = action)
    employees = []
    if request.method == "POST":
        form = DisciplinaryActionForm(request.POST, request.FILES, instance=action)

        if form.is_valid():
            emp = form.cleaned_data["employee_id"]

            for i in emp:
                name = i.employee_user_id
                employees.append(name)

            form.save()
            messages.success(request, _("Disciplinary action updated."))

            notify.send(
                request.user.employee_get,
                recipient=employees,
                verb="Disciplinary action is taken on you.",
                verb_ar="تم اتخاذ إجراء disziplinarisch ضدك.",
                verb_de="Disziplinarische Maßnahmen wurden gegen Sie ergriffen.",
                verb_es="Se ha tomado acción disciplinaria en tu contra.",
                verb_fr="Des mesures disciplinaires ont été prises à votre encontre.",
                redirect="/employee/disciplinary-actions/",
                icon="chatbox-ellipses",
            )
    return render(request, "disciplinary_actions/update_form.html", {"form": form})


@login_required
@permission_required("employee.delete_disciplinaryaction")
def delete_actions(request, action_id):
    """
    This method is used to delete Disciplinary action
    """

    DisciplinaryAction.objects.filter(id=action_id).delete()
    messages.success(request, _("Disciplinary action deleted."))
    return redirect(disciplinary_filter_view)


@login_required
def action_type_details(request):
    """
    This method is used to get the action type by the selection of title in the form.
    """
    action_id = request.POST["action_type"]
    action = Actiontype.objects.get(id=action_id)
    action_type = action.action_type
    return JsonResponse({"action_type": action_type})


@login_required
def disciplinary_filter_view(request):
    """
    This method is used to filter Disciplinary Action.
    """

    previous_data = request.GET.urlencode()
    dis_filter = DisciplinaryActionFilter(request.GET).qs
    page_number = request.GET.get("page")
    page_obj = paginator_qry(dis_filter, page_number)
    data_dict = parse_qs(previous_data)
    get_key_instances(DisciplinaryAction, data_dict)
    return render(
        request,
        "disciplinary_actions/disciplinary_records.html",
        {
            "data": page_obj,
            "pd": previous_data,
            "filter_dict": data_dict,
            "dashboard": request.GET.get("dashboard"),
        },
    )


@login_required
def search_disciplinary(request):
    """
    This method is used to search in Disciplinary Actions
    """
    disciplinary = DisciplinaryActionFilter(request.GET).qs
    return render(
        request,
        "disciplinary_actions/disciplinary_records.html",
        {
            "data": paginator_qry(disciplinary, request.GET.get("page")),
            "pd": request.GET.urlencode(),
        },
    )
