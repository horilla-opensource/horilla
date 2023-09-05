"""
actions.py

This module is used to register methods to delete/archive/un-archive instances
"""


import json
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from employee.models import Employee
from horilla.decorators import login_required, permission_required
from notifications.signals import notify
from recruitment.models import Candidate, Recruitment, Stage, StageNote
from recruitment.views.paginator_qry import paginator_qry


@login_required
@permission_required(perm="recruitment.delete_recruitment")
@require_http_methods(["POST"])
def recruitment_delete(request, rec_id):
    """
    This method is used to permanently delete the recruitment
    Args:
        id : recruitment_id
    """
    recruitment_obj = Recruitment.objects.get(id=rec_id)
    recruitment_mangers = recruitment_obj.recruitment_managers.all()
    all_stage_permissions = Permission.objects.filter(
        content_type__app_label="recruitment", content_type__model="stage"
    )
    all_candidate_permissions = Permission.objects.filter(
        content_type__app_label="recruitment", content_type__model="candidate"
    )
    for manager in recruitment_mangers:
        all_this_manger = manager.recruitment_set.all()
        if len(all_this_manger) == 1:
            for stage_permission in all_candidate_permissions:
                manager.employee_user_id.user_permissions.remove(stage_permission.id)
            for candidate_permission in all_stage_permissions:
                manager.employee_user_id.user_permissions.remove(
                    candidate_permission.id
                )
    try:
        recruitment_obj.delete()
        messages.success(request, _("Recruitment deleted successfully."))
    except Exception as error:
        messages.error(request, error)
        messages.error(request, _("You cannot delete this recruitment"))
    recruitment_obj = Recruitment.objects.all()
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required(perm="recruitment.delete_recruitment")
@require_http_methods(["POST"])
def recruitment_delete_pipeline(request, rec_id):
    """This method is used to delete the recruitment instance

    Args:
        id: recruitment instance id
    Returns:
        HttpResponseRedirect: Used to refresh the page
    """
    recruitment_obj = Recruitment.objects.get(id=rec_id)
    try:
        recruitment_obj.delete()
        messages.success(request, _("Recruitment deleted."))
    except Exception as error:
        messages.error(request, error)
        messages.error(request, _("Recruitment already in use."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required(perm="recruitment.delete_stagenote")
def note_delete(request, note_id):
    """
    This method is used to delete the stage note
    """
    note = StageNote.objects.get(id=note_id)
    candidate_obj = note.candidate_id
    try:
        note.delete()
        messages.success(request, _("Note deleted"))
    except Exception as error:
        messages.error(request, error)
        messages.error(request, _("You cannot delete this note."))
    return render(
        request, "pipeline/pipeline_components/view_note.html", {"cand": candidate_obj}
    )


@login_required
@require_http_methods(["DELETE"])
@permission_required(perm="recruitment.delete_stagenote")
def candidate_remark_delete(request, note_id):
    """
    This method is used to delete the candidate stage note
    Args:
        id : stage note instance id
    """
    stage_note = StageNote.objects.get(id=note_id)
    candidate_obj = stage_note.candidate_note_id.candidate_id
    try:
        stage_note.delete()
        messages.success(request, _("Note deleted"))
    except Exception as error:
        messages.error(request, error)
        messages.error(request, _("You cannot delete this note."))
    return render(
        request,
        "pipeline/pipeline_components/candidate_remark_view.html",
        {"cand": candidate_obj},
    )


@login_required
@permission_required(perm="recruitment.delete_stage")
@require_http_methods(["POST", "DELETE"])
def stage_delete(request, stage_id):
    """
    This method is used to delete stage permanently
    Args:
        id : stage_id
    """
    stage_obj = Stage.objects.get(id=stage_id)
    stage_managers = stage_obj.stage_managers.all()
    for manager in stage_managers:
        all_this_manger = manager.stage_set.all()
        if len(all_this_manger) == 1:
            view_recruitment = Permission.objects.get(codename="view_recruitment")
            manager.employee_user_id.user_permissions.remove(view_recruitment.id)
        initial_stage_manager = all_this_manger.filter(stage_type="initial")
        if len(initial_stage_manager) == 1:
            add_candidate = Permission.objects.get(codename="add_candidate")
            change_candidate = Permission.objects.get(codename="change_candidate")
            manager.employee_user_id.user_permissions.remove(add_candidate.id)
            manager.employee_user_id.user_permissions.remove(change_candidate.id)
        stage_obj.stage_managers.remove(manager)
    try:
        stage_obj.delete()
        messages.success(request, _("Stage deleted successfully."))
    except Exception as error:
        messages.error(request, error)
        messages.error(request, _("You cannot delete this stage"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required(perm="recruitment.delete_candidate")
@require_http_methods(["DELETE", "POST"])
def candidate_delete(request, cand_id):
    """
    This method is used to delete candidate permanently
    Args:
        id : candidate_id
    """
    try:
        Candidate.objects.get(id=cand_id).delete()
        messages.success(request, _("Candidate deleted successfully."))
    except Exception as error:
        messages.error(request, error)
        messages.error(request, _("You cannot delete this candidate"))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required(perm="recruitment.delete_candidate")
@require_http_methods(["POST"])
def candidate_bulk_delete(request):
    """
    This method is used to bulk delete candidates
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    for cand_id in ids:
        candidate_obj = Candidate.objects.get(id=cand_id)
        try:
            candidate_obj.delete()
            messages.success(
                request, _("%(candidate)s deleted.") % {"candidate": candidate_obj}
            )
        except Exception as error:
            messages.error(request, error)
            messages.error(
                request,
                _("You cannot delete %(candidate)s") % {"candidate": candidate_obj},
            )
    return JsonResponse({"message": "Success"})


@login_required
@permission_required(perm="recruitment.delete_candidate")
def candidate_archive(request, cand_id):
    """
    This method is used to archive or un-archive candidates
    """
    candidate_obj = Candidate.objects.get(id=cand_id)
    candidate_obj.is_active = not candidate_obj.is_active
    candidate_obj.save()
    message = "archived" if not candidate_obj.is_active else "un-archived"
    messages.success(request, f"Candidate is {message}")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required(perm="recruitment.delete_candidate")
@require_http_methods(["POST"])
def candidate_bulk_archive(request):
    """
    This method is used to archive/un-archive bulk candidates
    """
    ids = request.POST["ids"]
    ids = json.loads(ids)
    is_active = True
    message = "un-archived"
    if request.GET.get("is_active") == "False":
        is_active = False
        message = "archived"
    for cand_id in ids:
        candidate_obj = Candidate.objects.get(id=cand_id)
        candidate_obj.is_active = is_active
        candidate_obj.save()
        messages.success(request, f"{candidate_obj} is {message}")
    return JsonResponse({"message": "Success"})


@login_required
@permission_required(perm="recruitment.change_stage")
def remove_stage_manager(request, mid, sid):
    """
    This method is used to remove selected stage manager and also removing the  given
    permission if the employee is not exists in more stage manager or recruitment manager
    Args:
        mid : manager_id in the stage
        sid : stage_id
    """
    stage_obj = Stage.objects.get(id=sid)
    manager = Employee.objects.get(id=mid)
    notify.send(
        request.user.employee_get,
        recipient=manager.employee_user_id,
        verb=f"You are removed from stage managers from stage {stage_obj}",
        verb_ar=f"تمت إزالتك من مديري المرحلة من المرحلة {stage_obj}",
        verb_de=f"Sie wurden als Bühnenmanager von der Stufe {stage_obj} entfernt",
        verb_es=f"Has sido eliminado/a de los gerentes de etapa de la etapa {stage_obj}",
        verb_fr=f"Vous avez été supprimé(e) en tant que responsable de l'étape {stage_obj}",
        icon="person-remove",
        redirect="",
    )
    stage_obj.stage_managers.remove(manager)
    messages.success(request, _("Stage manager removed successfully."))
    stages = Stage.objects.all()
    previous_data = request.environ["QUERY_STRING"]
    return render(
        request,
        "stage/stage_component.html",
        {"data": paginator_qry(stages, request.GET.get("page")), "pd": previous_data},
    )


@login_required
@permission_required(perm="recruitment.change_recruitment")
@require_http_methods(["POST"])
def remove_recruitment_manager(request, mid, rid):
    """
    This method is used to remove selected manager from the recruitment,
    when remove the manager permissions also removed if the employee is not
    exists in more stage manager or recruitment manager

     Args:
        mid : employee manager_id in the recruitment
        rid : recruitment_id
    """
    recruitment_obj = Recruitment.objects.get(id=rid)
    manager = Employee.objects.get(id=mid)
    recruitment_obj.recruitment_managers.remove(manager)
    messages.success(request, _("Recruitment manager removed successfully."))
    notify.send(
        request.user.employee_get,
        recipient=manager.employee_user_id,
        verb=f"You are removed from recruitment manager from {recruitment_obj}",
        verb_ar=f"تمت إزالتك من وظيفة مدير التوظيف في {recruitment_obj}",
        verb_de=f"Sie wurden als Personalvermittler von {recruitment_obj} entfernt",
        verb_es=f"Has sido eliminado/a como gerente de contratación de {recruitment_obj}",
        verb_fr=f"Vous avez été supprimé(e) en tant que responsable\
                du recrutement de {recruitment_obj}",
        icon="person-remove",
        redirect="",
    )
    recruitment_queryset = Recruitment.objects.all()
    previous_data = request.environ["QUERY_STRING"]
    return render(
        request,
        "recruitment/recruitment_component.html",
        {
            "data": paginator_qry(recruitment_queryset, request.GET.get("page")),
            "pd": previous_data,
        },
    )
