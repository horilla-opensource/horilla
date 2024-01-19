"""
policies.py

This module is used to write operation related to policies
"""


from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from base.views import paginator_qry
from employee.filters import PolicyFilter
from employee.forms import PolicyForm
from employee.models import Policy, PolicyMultipleFile
from horilla.decorators import permission_required, login_required


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
