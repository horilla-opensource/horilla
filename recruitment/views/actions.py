"""
actions.py

This module is used to register methods to delete/archive/un-archive instances
"""

import json

from django import template
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.db.models import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from base.models import HorillaMailTemplate
from employee.models import Employee
from horilla.decorators import login_required, permission_required
from horilla.group_by import group_by_queryset
from notifications.signals import notify
from recruitment.decorators import (
    candidate_login_required,
    manager_can_enter,
    recruitment_manager_can_enter,
)
from recruitment.filters import StageFilter
from recruitment.forms import StageCreationForm
from recruitment.models import Candidate, Recruitment, Stage, StageNote
from recruitment.views.linkedin import delete_post
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
    try:
        try:
            recruitment_obj = Recruitment.objects.get(id=rec_id)
        except Recruitment.DoesNotExist:
            messages.error(request, _("Recruitment not found."))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
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
                    manager.employee_user_id.user_permissions.remove(
                        stage_permission.id
                    )
                for candidate_permission in all_stage_permissions:
                    manager.employee_user_id.user_permissions.remove(
                        candidate_permission.id
                    )
        try:
            if delete_post(recruitment_obj):
                messages.success(request, _("Recruitment deleted successfully."))
            else:
                messages.info(
                    request, _("Couldn’t delete the recruitment post from LinkedIn.")
                )
            recruitment_obj.delete()

        except ProtectedError as e:
            model_verbose_name_sets = set()
            for obj in e.protected_objects:
                model_verbose_name_sets.add(__(obj._meta.verbose_name.capitalize()))
            model_verbose_name_str = (",").join(model_verbose_name_sets)
            messages.error(
                request,
                _(
                    "You cannot delete this recruitment as it is using in {}".format(
                        model_verbose_name_str
                    )
                ),
            )
        recruitment_obj = Recruitment.objects.all()
    except (Recruitment.DoesNotExist, OverflowError):
        messages.error(request, _("Recruitment Does not exists.."))
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
    try:
        recruitment_obj = Recruitment.objects.get(id=rec_id)
        recruitment_obj.delete()
        messages.success(request, _("Recruitment deleted."))
    except Recruitment.DoesNotExist:
        messages.error(request, _("Recruitment not found."))
    except ProtectedError as e:
        models_verbose_name_sets = set()
        for obj in e.protected_objects:
            models_verbose_name_sets.add(__(obj._meta.verbose_name.capitalize()))
        models_verbose_name_str = (",").join(models_verbose_name_sets)
        messages.error(
            request,
            _("Recruitment already in use for {}.".format(models_verbose_name_str)),
        )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@manager_can_enter(perm="recruitment.delete_stagenote")
def note_delete(request, note_id):
    """
    This method is used to delete the stage note
    """
    try:
        note = StageNote.objects.get(id=note_id)
        candidate_id = note.candidate_id.id
        note.delete()
        messages.success(request, _("Note deleted"))
        script = ""
    except StageNote.DoesNotExist:
        messages.error(request, _("Note not found."))
        script = "<script>window.location.reload()</script>"
    except ProtectedError:
        messages.error(request, _("You cannot delete this note."))
        script = f"""
            <span hx-trigger='load' hx-get='/recruitment/view-note/{candidate_id}/' hx-target='#activitySidebar'></span>
            """
    return HttpResponse(script)


@candidate_login_required
# @manager_can_enter(perm="recruitment.delete_stagenote")
def note_delete_individual(request, note_id):
    """
    This method is used to delete the stage note
    """
    script = ""
    note = StageNote.objects.get(id=note_id)
    note.delete()
    messages.success(request, _("Note deleted."))
    return HttpResponse(script)


@login_required
@manager_can_enter(perm="recruitment.delete_stage")
@require_http_methods(["POST", "DELETE"])
def stage_delete(request, stage_id):
    """
    This method is used to delete stage permanently
    Args:
        id : stage_id
    """
    try:
        try:
            stage_obj = Stage.objects.get(id=stage_id)
            recruitment_id = stage_obj.recruitment_id.id
        except Stage.DoesNotExist:
            messages.error(request, _("Stage not found."))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

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
        except ProtectedError as e:
            models_verbose_name_sets = set()
            for obj in e.protected_objects:
                models_verbose_name_sets.add(__(obj._meta.verbose_name.capitalize()))
            models_verbose_name_str = (",").join(models_verbose_name_sets)
            messages.error(
                request,
                _(
                    "You cannot delete this stage while it's in use for {}".format(
                        models_verbose_name_str
                    )
                ),
            )
    except (Stage.DoesNotExist, OverflowError):
        messages.error(request, _("Stage Does not exists.."))
    hx_request = request.META.get("HTTP_HX_REQUEST")
    hx_current_url = request.META.get("HTTP_HX_CURRENT_URL")
    if hx_request and hx_request == "true" and "stage-view" in hx_current_url:
        return redirect(f"/recruitment/stage-data/{recruitment_id}/")
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
        try:
            Candidate.objects.get(id=cand_id).delete()
            messages.success(request, _("Candidate deleted successfully."))
        except Candidate.DoesNotExist:
            messages.error(request, _("Candidate not found."))
        except ProtectedError as e:
            models_verbose_name_set = set()
            for obj in e.protected_objects:
                models_verbose_name_set.add(__(obj._meta.verbose_name.capitalize()))
            models_verbose_name_str = (",").join(models_verbose_name_set)
            messages.error(
                request,
                _(
                    "You cannot delete this candidate because the candidate is in {}.".format(
                        models_verbose_name_str
                    )
                ),
            )
    except (Candidate.DoesNotExist, OverflowError):
        messages.error(request, _("Candidate Does not exists."))
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
        try:
            candidate_obj = Candidate.objects.get(id=cand_id)
            candidate_obj.delete()
            messages.success(
                request, _("%(candidate)s deleted.") % {"candidate": candidate_obj}
            )
        except Candidate.DoesNotExist:
            messages.error(request, _("Candidate not found."))
        except ProtectedError:
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
    try:
        candidate_obj = Candidate.objects.get(id=cand_id)
        candidate_obj.is_active = not candidate_obj.is_active
        candidate_obj.save()
        message = _("archived") if not candidate_obj.is_active else _("un-archived")
        messages.success(request, _("Candidate is %(message)s") % {"message": message})
    except (Candidate.DoesNotExist, OverflowError):
        messages.error(request, _("Candidate Does not exists."))
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
    message = _("un-archived")
    if request.GET.get("is_active") == "False":
        is_active = False
        message = _("archived")
    for cand_id in ids:
        candidate_obj = Candidate.objects.get(id=cand_id)
        candidate_obj.is_active = is_active
        candidate_obj.save()
        messages.success(
            request,
            _("{candidate} is {message}").format(
                candidate=candidate_obj, message=message
            ),
        )
    return JsonResponse({"message": "Success"})


@login_required
@manager_can_enter(perm="recruitment.change_stage")
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
    stages = stages.filter(recruitment_id__is_active=True)
    recruitments = group_by_queryset(
        stages,
        "recruitment_id",
        request.GET.get("rpage"),
    )
    filter_obj = StageFilter()
    form = StageCreationForm()
    previous_data = request.GET.urlencode()
    return render(
        request,
        "stage/stage_group.html",
        {
            "data": paginator_qry(stages, request.GET.get("page")),
            "pd": previous_data,
            "form": form,
            "f": filter_obj,
            "recruitments": recruitments,
        },
    )


@login_required
@manager_can_enter(perm="recruitment.change_recruitment")
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
    previous_data = request.GET.urlencode()
    return render(
        request,
        "recruitment/recruitment_component.html",
        {
            "data": paginator_qry(recruitment_queryset, request.GET.get("page")),
            "pd": previous_data,
        },
    )


@login_required
def get_template(request, obj_id=None):
    """
    This method is used to return the mail template
    """
    body = ""
    if obj_id:
        body = HorillaMailTemplate.objects.get(id=obj_id).body
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
        # body = template_bdy.render(context) or " "
    return JsonResponse({"body": body})


@login_required
def get_template_hint(request, obj_id=None):
    """
    This method is used to return the mail template
    """
    if obj_id:
        body = HorillaMailTemplate.objects.get(id=obj_id).body
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


@login_required
def get_mail_preview(request):
    """
    Returns the mail template preview as HTML.
    """
    body = request.POST.get("body")
    if not body:
        return HttpResponse("No body provided", status=400)

    candidate_id = request.GET.get("candidate_id")
    candidate_ids = request.POST.getlist("candidates")  # 875

    # Fetch one candidate for preview if provided
    candidate_obj = None
    if candidate_id or candidate_ids:
        ids = [candidate_id] if candidate_id else candidate_ids
        candidate_obj = Candidate.objects.filter(id__in=ids).first()
        if not candidate_obj:
            return HttpResponse("Candidate not found", status=404)

    # Build context
    context = {
        "instance": candidate_obj,
        "model_instance": candidate_obj,
        "self": getattr(request.user, "employee_get", None),
        "request": request,
    }

    # Render template
    rendered_body = template.Template(body).render(template.Context(context)) or " "

    # Add preview note if multiple candidates
    if candidate_ids and len(candidate_ids) > 1 and candidate_obj:
        rendered_body = (
            f"<p style='color:gray; font-size:13px;'>"
            f"Preview shown for {candidate_obj.name}. "
            f"Mail will be personalized for {len(candidate_ids)} candidates."
            f"</p>{rendered_body}"
        )

    # Wrap in styled div
    textarea_field = (
        f'<div class="oh-input oh-input--textarea" '
        f'style="border: solid .1px #dbd7d7; padding:5px;">{rendered_body}</div>'
    )

    return HttpResponse(textarea_field, content_type="text/html")
