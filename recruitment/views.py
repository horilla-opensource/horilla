from django.shortcuts import render, redirect
from .models import Recruitment, Candidate, Stage
from horilla.decorators import permission_required, login_required, hx_request_required
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from employee.models import Employee
from recruitment.forms import RecruitmentCreationForm, CandidateCreationForm, StageCreationForm, ApplicationForm, RecruitmentDropDownForm, StageDropDownForm, CandidateDropDownForm, StageNoteForm
from django.contrib.auth.models import User, Permission, Group
from django.core import serializers
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from recruitment.filters import CandidateFilter, RecruitmentFilter, StageFilter
from django.views.decorators.http import require_http_methods
from django.forms import formset_factory
from recruitment.filters import RecruitmentFilter
from recruitment.models import StageNote
import json
from django.core.mail import send_mail
from horilla import settings
from django.db.models import Q
from recruitment.methods import is_recruitmentmanager, is_stagemanager, recruitment_manages, stage_manages
from base.methods import sortby
from recruitment.decorators import manager_can_enter, recruitment_manager_can_enter
from notifications.signals import notify
from django.utils.translation import gettext_lazy as _

# Create your views here.


def is_stagemanager(request, stage_id=False):
    """
    This method is used to identify the employee is a stage manager or not, if stage_id is passed through args, method will 
    check the employee is manager to the corresponding stage, return tuple with boolean and all stages that employee is manager.
    if called this method without stage_id args it will return boolean with all the stage that the employee is stage manager
    Args:
        request : django http request
        stage_id : stage instance id
    """
    user = request.user
    employee = user.employee_get
    if not stage_id:
        return (employee.stage_set.exists() or user.is_superuser,  employee.stage_set.all())
    stage = Stage.objects.get(id=stage_id)
    return employee in stage.stage_managers.all() or user.is_superuser or is_recruitmentmanager(request, rec_id=stage.recruitment_id.id)[0], employee.stage_set.all()


def is_recruitmentmanager(request, rec_id=False):
    """
    This method is used to identify the employee is a recruitment manager or not, if rec_id is passed through args, method will 
    check the employee is manager to the corresponding recruitment, return tuple with boolean and all recruitment that employee is manager.
    if called this method without recruitment args it will return boolean with all the recruitment that the employee is recruitment manager
    Args:
        request : django http request
        rec_id : recruitment instance id
    """
    user = request.user
    employee = user.employee_get
    if not rec_id:
        return employee.recruitment_set.exists() or user.is_superuser,  employee.recruitment_set.all()
    recruitment = Recruitment.objects.get(id=rec_id)
    return employee in recruitment.recruitment_managers.all() or user.is_superuser, employee.recruitment_set.all()


def stages_create(recruitment: object):
    """
    This method is used to create some default stages when create recruitment
    Args:
        id : recruitment instance
    """
    new_stage = Stage.objects.create(
        recruitment_id=recruitment,
        stage='New',
        sequence=1,
        stage_type='initial'
    )

    interview_stage = Stage.objects.create(
        recruitment_id=recruitment,
        stage='Interview',
        sequence=2,
        stage_type='interview'
    )
    hired_stage = Stage.objects.create(
        recruitment_id=recruitment,
        stage='Hired',
        sequence=3,
        stage_type='hired'
    )
    return


def paginator_qry(qryset, page_number):
    """
    This method is used to generate common paginator limit.
    """
    paginator = Paginator(qryset, 50)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@permission_required('recruitment.add_recruitment')
def recruitment(request):
    """
    This method is used to create recruitment, when create recruitment this method
    add  recruitment view,create candidate, change stage sequence and so on, some of
    the permission is checking manually instead of using django permission permission
    to the  recruitment managers
    """
    form = RecruitmentCreationForm()
    if request.method == 'POST':
        form = RecruitmentCreationForm(request.POST)
        if form.is_valid():
            recruitment = form.save()
            messages.success(request, _('Recruitment added.'))
            try:
                managers = recruitment.recruitment_managers.select_related(
                    'employee_user_id')
                users = [employee.employee_user_id for employee in managers]
                notify.send(request.user.employee_get, recipient=users, verb="You are chosen as one of recruitment manager",
                            icon="people-circle", redirect="/recruitment/pipeline")
            except Exception as e:
                pass
            response = render(
                request, 'recruitment/recruitment_form.html', {'form': form})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'recruitment/recruitment_form.html', {'form': form})


@login_required
@permission_required('recruitment.change_recruitment')
@require_http_methods(['POST'])
def remove_recruitment_manager(request, mid, rid):
    """
    This method is used to remove selected manager from the recruitment,
     when remove the manager permissions also removed if the employee is not
     exists in more stage manager or recruitment manager

     Args:
        mid : employee manager_id in the recruitment
        rid : recruitment_id
     """
    recruitment = Recruitment.objects.get(id=rid)
    manager = Employee.objects.get(id=mid)
    recruitment.recruitment_managers.remove(manager)
    messages.success(request, _('Recruitment manager removed successfully.'))
    notify.send(request.user.employee_get, recipient=manager.employee_user_id,
                verb=f"You are removed from recruitment manager from {recruitment}", icon="person-remove", redirect="")
    recruitment = Recruitment.objects.all()
    previous_data = request.environ['QUERY_STRING']
    return render(request, 'recruitment/recruitment_component.html', {'data': paginator_qry(recruitment, request.GET.get('page')), 'pd': previous_data})


@login_required
@permission_required('recruitment.view_recruitment')
def recruitment_view(request):
    """
    This method is used to  render all recruitment to view
    """
    if not request.GET:
        request.GET.copy().update({'is_active': 'on'})
    form = RecruitmentCreationForm()
    filter = RecruitmentFilter(request.GET, queryset=Recruitment.objects.all())
    return render(request, 'recruitment/recruitment_view.html', {'data': paginator_qry(filter.qs, request.GET.get('page')), 'f': filter, 'form': form})


@login_required
@permission_required('recruitment.view_recruitment')
def recruitment_search(request):
    """
    This method is used to search recruitment
    """
    filter = RecruitmentFilter(request.GET)
    previous_data = request.environ['QUERY_STRING']
    recruitment = sortby(request, filter.qs, 'orderby')
    return render(request, 'recruitment/recruitment_component.html', {
        'data': paginator_qry(recruitment, request.GET.get('page')),
        'pd': previous_data})


@login_required
@permission_required('recruitment.change_recruitment')
@hx_request_required
def recruitment_update(request, id):
    """
    This method is used to update the recruitment, when updating the recruitment,
    any changes in manager is exists then permissions also assigned to the manager
    Args:
        id : recruitment_id
    """
    recruitment = Recruitment.objects.get(id=id)
    form = RecruitmentCreationForm(instance=recruitment)
    if request.method == 'POST':
        form = RecruitmentCreationForm(
            request.POST, instance=recruitment)
        if form.is_valid():
            recruitment = form.save()
            messages.success(request, _('Recruitment Updated.'))
            response = render(
                request, 'recruitment/recruitment_form.html', {'form': form})
            try:
                managers = recruitment.recruitment_managers.select_related(
                    'employee_user_id')
                users = [employee.employee_user_id for employee in managers]
                notify.send(request.user.employee_get, recipient=users,
                            verb=f"{recruitment} is updated, You are chosen as one of managers", icon="people-circle", redirect="/recruitment/pipeline")
            except Exception as e:
                pass
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'recruitment/recruitment_update_form.html', {'form': form})


@login_required
@permission_required('recruitment.delete_recruitment')
@require_http_methods(['POST'])
def recruitment_delete(request, id):
    """
    This method is used to permanently delete the recruitment
    Args:
        id : recruitment_id
    """
    recruitment = Recruitment.objects.get(id=id)
    recruitment_mangers = recruitment.recruitment_managers.all()
    all_stage_permissions = Permission.objects.filter(
        content_type__app_label='recruitment', content_type__model='stage')
    all_candidate_permissions = Permission.objects.filter(
        content_type__app_label='recruitment', content_type__model='candidate')
    for manager in recruitment_mangers:
        all_this_manger = manager.recruitment_set.all()
        if len(all_this_manger) == 1:
            for stage_permission in all_candidate_permissions:
                manager.employee_user_id.user_permissions.remove(
                    stage_permission.id)
            for candidate_permission in all_stage_permissions:
                manager.employee_user_id.user_permissions.remove(
                    candidate_permission.id)
    try:
        recruitment.delete()
        messages.success(request, _('Recruitment deleted successfully.'))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _("You cannot delete this recruitment"))
    recruitment = Recruitment.objects.all()
    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))


@login_required
@manager_can_enter('recruitment.view_recruitment')
def recruitment_pipeline(request):
    """
    This method is used to filter out candidate through pipeline structure
    """
    view = request.GET.get('view')
    template = 'pipeline/pipeline.html'
    if view == 'card':
        template = 'pipeline/pipeline_card.html'
    recruitment_form = RecruitmentDropDownForm()
    stage_form = StageDropDownForm()
    candidate_form = CandidateDropDownForm()
    recruitment = Recruitment.objects.filter(is_active=True, closed=False)
    if request.method == 'POST':
        if request.POST.get('recruitment_managers') is not None and request.user.has_perm('add_recruitment'):
            recruitment_form = RecruitmentDropDownForm(request.POST)
            if recruitment_form.is_valid():
                recruitment = recruitment_form.save()
                recruitment_form = RecruitmentDropDownForm()
                messages.success(request, _('Recruitment added.'))
                try:
                    managers = recruitment.recruitment_managers.select_related(
                        'employee_user_id')
                    users = [employee.employee_user_id for employee in managers]
                    notify.send(request.user.employee_get, recipient=users,
                                verb=f"You are chosen as recruitment manager for the recruitment {recruitment}", icon="people-circle", redirect="/recruitment/pipeline")
                except Exception as e:
                    pass
                return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
        elif request.FILES.get('resume') is not None:
            if request.user.has_perm('add_candidate') or is_stagemanager(request,):
                candidate_form = CandidateDropDownForm(
                    request.POST, request.FILES)
                if candidate_form.is_valid():
                    candidate = candidate_form.save()
                    candidate_form = CandidateDropDownForm()
                    try:
                        managers = candidate.stage_id.stage_managers.select_related(
                            'employee_user_id')
                        users = [
                            employee.employee_user_id for employee in managers]
                        notify.send(request.user.employee_get, recipient=users,
                                    verb=f"New candidate arrived on stage {stage.stage}", icon="person-add", redirect="/recruitment/pipeline")
                    except Exception as e:
                        pass
                    messages.success(request, _('Candidate added.'))
                    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
        elif request.POST.get('stage_managers') and request.user.has_perm('add_stage'):
            stage_form = StageDropDownForm(request.POST)
            if stage_form.is_valid():
                if recruitment_manages(request, stage_form.instance.recruitment_id) or request.user.has_perm('recruitment.add_stage'):
                    stage = stage_form.save()
                    stage_form = StageDropDownForm()
                    messages.success(request, _('Stage added.'))
                    try:
                        managers = stage.stage_managers.select_related(
                            'employee_user_id')
                        users = [
                            employee.employee_user_id for employee in managers]
                        notify.send(request.user.employee_get, recipient=users,
                                    verb=f"You are chosen as a stage manager on the stage {stage.stage} in recruitment {stage.recruitment_id}", icon="people-circle", redirect="/recruitment/pipeline")
                    except Exception as e:
                        pass
                    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
                messages.info(request, _('You dont have access'))

    return render(request, template, {'recruitment': recruitment, 'recruitment_form': recruitment_form, 'stage_form': stage_form, 'candidate_form': candidate_form})


@login_required
@permission_required('recruitment.view_recruitment')
def recruitment_pipeline_card(request):
    """
    This method is used to render pipeline card structure.
    """
    search = request.GET.get('search')
    search = search if search != None else ''
    recruitment = Recruitment.objects.all()
    candidates = Candidate.objects.filter(
        name__icontains=search, is_active=True)
    stages = Stage.objects.all()
    return render(request, 'pipeline/pipeline_components/pipeline_card_view.html', {'recruitment': recruitment, 'candidates': candidates, 'stages': stages})


@login_required
@permission_required('recruitment.view_candidate')
def pipeline_candidate_search(request):
    """
    This method is used to search  candidate
    """
    search = request.GET['search']
    template = 'pipeline/pipeline_components/kanban_tabs.html'
    if request.GET.get('view') == 'card':
        template = 'pipeline/pipeline_components/kanban_tabs.html'
    return render(request, template)


@login_required
@recruitment_manager_can_enter('recruitment.change_stage')
def stage_update_pipeline(request, id):
    """
    This method is used to update stage from pipeline view
    """
    stage = Stage.objects.get(id=id)
    form = StageCreationForm(instance=stage)
    if request.POST:
        form = StageCreationForm(request.POST, instance=stage)
        if form.is_valid():
            stage = form.save()
            messages.success(request, _('Stage updated.'))
            try:
                managers = stage.stage_managers.select_related(
                    'employee_user_id')
                users = [employee.employee_user_id for employee in managers]
                notify.send(request.user.employee_get, recipient=users,
                            verb=f"{stage.stage} stage in recruitment {stage.recruitment_id} is updated, You are chosen as one of managers", icon="people-circle", redirect="/recruitment/pipeline")
            except Exception as e:
                pass
            return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))

    return render(request, 'pipeline/form/stage_update.html', {'form': form})


@login_required
@recruitment_manager_can_enter('recruitment.change_recruitment')
def recruitment_update_pipeline(request, id):
    """
    This method is used to update recruitment from pipeline view
    """
    recruitment = Recruitment.objects.get(id=id)
    form = RecruitmentCreationForm(instance=recruitment)
    if request.POST:
        form = RecruitmentCreationForm(request.POST, instance=recruitment)
        if form.is_valid():
            recruitment = form.save()
            messages.success(request, _('Recruitment updated.'))
            try:
                managers = recruitment.recruitment_managers.select_related(
                    'employee_user_id')
                users = [employee.employee_user_id for employee in managers]
                notify.send(request.user.employee_get, recipient=users,
                            verb=f"{recruitment} is updated, You are chosen as one of managers", icon="people-circle", redirect="/recruitment/pipeline")
            except Exception as e:
                pass
            return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
    return render(request, 'pipeline/form/recruitment_update.html', {'form': form})


@login_required
@permission_required('recruitment.delete_recruitment')
@require_http_methods(['POST'])
def recruitment_delete_pipeline(request, id):
    recruitment = Recruitment.objects.get(id=id)
    try:
        recruitment.delete()
        messages.success(request, _('Recruitment deleted.'))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _('Recruitment already in use.'))
    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))


@login_required
@manager_can_enter('recruitment.change_candidate')
def candidate_stage_update(request, id):
    """
    This method is a ajax method used to update candidate stage when drag and drop
    the candidate from one stage to another on the pipeline template
    Args:
        id : candidate_id
    """
    stage_id = request.POST['stageId']
    candidate = Candidate.objects.get(id=id)
    candidate_history = candidate.candidate_history.all().first()
    stage = Stage.objects.get(id=stage_id)
    previous_stage = candidate_history.stage_id
    if previous_stage == stage:
        return JsonResponse({'type': 'info', 'message': _('No change detected.')})
    """
    Here set the last updated schedule date on this stage if schedule exists in history
    """
    candidate_history = candidate.candidate_history.filter(stage_id=stage)
    schedule_date = None
    if candidate_history.exists():
        # this condition is executed when a candidate dropped back to any previous
        # stage, if there any scheduled date then set it back
        schedule_date = candidate_history.first().schedule_date
    stage_manager_on_this_recruitment = is_stagemanager(
        request)[1].filter(recruitment_id=stage.recruitment_id).exists()
    if stage_manager_on_this_recruitment or request.user.is_superuser or is_recruitmentmanager(rec_id=stage.recruitment_id.id)[0]:
        candidate.stage_id = stage
        candidate.schedule_date = None
        candidate.hired = False
        candidate.schedule_date = schedule_date
        candidate.start_onboard = False
        if stage.stage_type == 'hired':
            candidate.hired = True
        candidate.save()
        try:
            managers = stage.stage_managers.select_related('employee_user_id')
            users = [employee.employee_user_id for employee in managers]
            notify.send(request.user.employee_get, recipient=users,
                        verb=f"New candidate arrived on stage {stage.stage}", icon="person-add", redirect="/recruitment/pipeline")
        except Exception as e:
            pass
    return JsonResponse({'type': 'success', 'message': _('Candidate stage updated')})


@login_required
@hx_request_required
@manager_can_enter('recruitment.add_stagenote')
def add_note(request, id=None):
    """
    This method renders template component to add candidate remark
    """
    form = StageNoteForm(initial={'candidate_id': id})
    if request.method == 'POST':
        form = StageNoteForm(request.POST,)
        if form.is_valid():
            note = form.save(commit=False)
            note.stage_id = note.candidate_id.stage_id
            note.updated_by = request.user.employee_get
            note.save()
            messages.success(request, _('Note added successfully..'))
            response = render(
                request, 'pipeline/pipeline_components/add_note.html', {'form': form})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'pipeline/pipeline_components/add_note.html', {'note_form': form, })


@login_required
@hx_request_required
@manager_can_enter('recruitment.view_stagenote')
def view_note(request, id):
    """
    This method renders a template components to view candidate remark or note
    Args:  
        id : candidate instance id
    """
    candidate = Candidate.objects.get(id=id)
    return render(request, 'pipeline/pipeline_components/view_note.html', {'cand': candidate})


@login_required
@permission_required('recruitment.change_stagenote')
def note_update(request, id):
    """
    This method is used to update the stage not 
    Args:
        id : stage note instance id
    """
    note = StageNote.objects.get(id=id)
    form = StageNoteForm(instance=note)
    if request.POST:
        form = StageNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, _('Note updated successfully...'))
            response = render(
                request, 'pipeline/pipeline_components/update_note.html', {'form': form})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'pipeline/pipeline_components/update_note.html', {'form': form})


@login_required
@permission_required('recruitment.delete_stagenote')
def note_delete(request, id):
    """
    This method is used to delete the stage note
    """
    note = StageNote.objects.get(id=id)
    candidate = note.candidate_id
    try:
        note.delete()
        messages.success(request, _('Note deleted'))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _('You cannot delete this note.'))
    return render(request, 'pipeline/pipeline_components/view_note.html', {'cand': candidate})


@login_required
@require_http_methods(['DELETE'])
@permission_required('recruitment.delete_stagenote')
def candidate_remark_delete(request, id):
    """
    This method is used to delete the candidate stage note
    Args:
        id : stage note instance id
    """

    stage_note = StageNote.objects.get(id=id)
    candidate = stage_note.candidate_note_id.candidate_id
    try:
        stage_note.delete()
        messages.success(request, _('Note deleted'))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _('You cannot delete this note.'))
    return render(request, 'pipeline/pipeline_components/candidate_remark_view.html', {'cand': candidate})


@login_required
@permission_required('recruitment.change_candidate')
def candidate_schedule_date_update(request):
    """
    This is a an ajax method to update schedule date for a candidate
    """
    candidate_id = request.POST['candidateId']
    schedule_date = request.POST['date']
    candidate = Candidate.objects.get(id=candidate_id)
    candidate.schedule_date = schedule_date
    candidate.save()
    return JsonResponse({'message': 'congratulations'})


@login_required
@permission_required('recruitment.add_stage')
def stage(request):
    """
    This method is used to create stages, also several permission assigned to the stage managers
    """
    form = StageCreationForm()
    if request.method == 'POST':
        form = StageCreationForm(request.POST)
        if form.is_valid():
            stage = form.save()
            recruitment = stage.recruitment_id
            rec_stages = Stage.objects.filter(
                recruitment_id=recruitment, is_active=True).order_by('sequence').last()
            if rec_stages.sequence is None:
                stage.sequence = 1
            else:
                stage.sequence = rec_stages.sequence + 1
            stage.save()
            messages.success(request, _('Stage added.'))
            try:
                managers = stage.stage_managers.select_related(
                    'employee_user_id')
                users = [employee.employee_user_id for employee in managers]
                notify.send(request.user.employee_get, recipient=users,
                            verb=f"Stage {stage} is updated on recruitment {stage.recruitment_id}, You are chosen as one of managers", icon="people-circle", redirect="/recruitment/pipeline")
            except Exception as e:
                pass
            response = render(request, 'stage/stage_form.html', {'form': form})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'stage/stage_form.html', {'form': form})


@login_required
@permission_required('recruitment.view_stage')
def stage_view(request):
    """
    This method is used to render all stages to a template
    """
    stages = Stage.objects.filter()
    filter = StageFilter()
    form = StageCreationForm()
    return render(request, 'stage/stage_view.html', {
        'data': paginator_qry(stages, request.GET.get('page')), 'form': form,
        'f': filter})


@login_required
@permission_required('recruitment.view_stage')
def stage_search(request):
    """
    This method is used to search stage
    """
    
    stages = StageFilter(request.GET).qs
    previous_data = request.environ['QUERY_STRING']
    stages = sortby(request, stages, 'orderby')
    return render(request, 'stage/stage_component.html', {'data': paginator_qry(stages, request.GET.get('page')), 'pd': previous_data})


@login_required
@permission_required('recruitment.change_stage')
def remove_stage_manager(request, mid, sid):
    """
    This method is used to remove selected stage manager and also removing the  given 
    permission if the employee is not exists in more stage manager or recruitment manager
    Args:
        mid : manager_id in the stage
        sid : stage_id
    """
    stage = Stage.objects.get(id=sid)
    manager = Employee.objects.get(id=mid)
    notify.send(request.user.employee_get, recipient=manager.employee_user_id,
                verb=f"You are removed from stage managers from stage {stage}", icon="person-remove", redirect="")
    stage.stage_managers.remove(manager)
    messages.success(request, _('Stage manager removed successfully.'))
    stages = Stage.objects.all()
    previous_data = request.environ['QUERY_STRING']
    return render(request, 'stage/stage_component.html', {'data': paginator_qry(stages, request.GET.get('page')), 'pd': previous_data})


@login_required
@require_http_methods(['POST'])
@permission_required('recruitment.change_stage')
def stage_sequence_update(request):
    """
    This is also a ajax method used to update sequence of stage while drag and drop stage in pipeline template,
    """
    stages = json.loads(json.loads(request.POST['stages']))
    sequences = json.loads(request.POST['newSequences'])
    # for index,stage_id in enumerate(stages):
    #     stage = Stage.objects.get(id=stage_id)
    #     stage.sequence = sequences[index]
    #     stage.save()
    return JsonResponse({'message': 'Congratulations'})


@login_required
@permission_required('recruitment.change_stage')
@hx_request_required
def stage_update(request, id):
    """
    This method is used to update stage, if the managers changed then permission assigned to new managers also
    Args:
        id : stage_id

    """
    stages = Stage.objects.get(id=id)
    form = StageCreationForm(instance=stages)
    if request.method == 'POST':
        form = StageCreationForm(request.POST, instance=stages)
        if form.is_valid():
            stage = form.save()
            messages.success(request, _('Stage updated.'))
            response = render(
                request, 'recruitment/recruitment_form.html', {'form': form})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'stage/stage_update_form.html', {'form': form})


@login_required
@require_http_methods(['POST'])
@hx_request_required
def stage_name_update(request, id):
    """	
    This method is used to update the name of recruitment stage	
    """
    stage = Stage.objects.get(id=id)
    stage.stage = request.POST['stage']
    stage.save()
    return HttpResponse({'message': 'success'})


@login_required
@permission_required('recruitment.delete_stage')
@require_http_methods(['POST', 'DELETE'])
def stage_delete(request, id):
    """
    This method is used to delete stage permanently
    Args:
        id : stage_id
    """
    stage = Stage.objects.get(id=id)
    stage_managers = stage.stage_managers.all()
    for manager in stage_managers:
        all_this_manger = manager.stage_set.all()
        if len(all_this_manger) == 1:
            view_recruitment = Permission.objects.get(
                codename='view_recruitment')
            manager.employee_user_id.user_permissions.remove(
                view_recruitment.id)
        initial_stage_manager = all_this_manger.filter(stage_type='initial')
        if len(initial_stage_manager) == 1:
            add_candidate = Permission.objects.get(codename='add_candidate')
            change_candidate = Permission.objects.get(
                codename='change_candidate')
            manager.employee_user_id.user_permissions.remove(add_candidate.id)
            manager.employee_user_id.user_permissions.remove(
                change_candidate.id)
        stage.stage_managers.remove(manager)
    try:
        stage.delete()
        messages.success(request, _('Stage deleted successfully.'))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _('You cannot delete this stage'))
    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))


@login_required
@permission_required('recruitment.add_candidate')
def candidate(request):
    """
    This method used to create candidate
    """
    form = CandidateCreationForm()
    open_recruitment = Recruitment.objects.filter(closed=False, is_active=True)
    if request.method == 'POST':
        form = CandidateCreationForm(request.POST, request.FILES)
        if form.is_valid():
            candidate = form.save(commit=False)
            candidate.start_onboard = False
            if candidate.stage_id is None:
                candidate.stage_id = Stage.objects.filter(
                    recruitment_id=candidate.recruitment_id, stage_type="initial").first()
            candidate.save()
            messages.success(request, _('Candidate added.'))
            return redirect('/recruitment/candidate-view')

    return render(request, 'candidate/candidate_create_form.html', {'form': form, 'open_recruitment': open_recruitment})


@login_required
@permission_required('recruitment.add_candidate')
def recruitment_stage_get(request, id):
    """
    This method returns all stages as json
    Args:
        id: recruitment_id
    """
    recruitment = Recruitment.objects.get(id=id)
    all_stages = recruitment.stage_set.all()
    all_stage_json = serializers.serialize('json', all_stages)
    return JsonResponse({'stages': all_stage_json})


@login_required
@permission_required('recruitment.view_candidate')
def candidate_view(request):
    """
    This method render all candidate to the template
    """
    previous_data = request.environ['QUERY_STRING']
    candidates = Candidate.objects.filter(is_active=True)
    filter = CandidateFilter(queryset=candidates)
    return render(request, 'candidate/candidate_view.html', {
        'data': paginator_qry(filter.qs, request.GET.get('page')),
        'pd': previous_data,
        'f': filter
    })


@login_required
@permission_required('recruitment.view_candidate')
def candidate_filter_view(request):
    """
    This method is used for filter,pagination and search candidate.
    """
    previous_data = request.environ['QUERY_STRING']
    filter = CandidateFilter(
        request.GET, queryset=Candidate.objects.filter(is_active=True))
    paginator = Paginator(filter.qs, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'candidate/candidate_card.html', {'data': page_obj, 'pd': previous_data})


@login_required
@permission_required('recruitment.view_candidate')
def candidate_search(request):
    """
    This method is used to search candidate model and return matching objects
    """
    previous_data = request.environ['QUERY_STRING']
    search = request.GET.get('search')
    if search is None:
        search = ''
    candidates = Candidate.objects.filter(name__icontains=search)
    candidates = CandidateFilter(request.GET, queryset=candidates).qs
    template = 'candidate/candidate_card.html'
    if request.GET.get('view') == 'list':
        template = 'candidate/candidate_list.html'
    candidates = sortby(request, candidates, 'orderby')
    candidates = paginator_qry(candidates, request.GET.get('page'))
    return render(request, template, {'data': candidates, 'pd': previous_data})


@login_required
@permission_required('recruitment.view_candidate')
def candidate_view_list(request):
    """
    This method renders all candidate on candidate_list.html template
    """
    previous_data = request.environ['QUERY_STRING']
    candidates = Candidate.objects.all()
    if request.GET.get('is_active') is None:
        candidates = candidates.filter(is_active=True)
    candidates = CandidateFilter(request.GET, queryset=candidates).qs
    return render(request, 'candidate/candidate_list.html', {
        'data': paginator_qry(candidates, request.GET.get('page')),
        'pd': previous_data}
    )


@login_required
@permission_required('recruitment.view_candidate')
def candidate_view_card(request):
    """
    This method renders all candidate on candidate_card.html template
    """
    previous_data = request.environ['QUERY_STRING']
    candidates = Candidate.objects.all()
    if request.GET.get('is_active') is None:
        candidates = candidates.filter(is_active=True)
    candidates = CandidateFilter(request.GET, queryset=candidates).qs
    return render(request, 'candidate/candidate_card.html', {'data': paginator_qry(candidates, request.GET.get('page')), 'pd': previous_data})


@login_required
@permission_required('recruitment.view_candidate')
def candidate_view_individual(request, id):
    """
    This method is used to view profile of candidate.
    """
    candidate = Candidate.objects.get(id=id)
    return render(request, 'candidate/individual.html', {'candidate': candidate})


@login_required
@manager_can_enter('recruitment.change_candidate')
def candidate_update(request, id):
    """
    Used to update or change the candidate
    Args:
        id : candidate_id
    """
    candidate = Candidate.objects.get(id=id)
    form = CandidateCreationForm(instance=candidate)
    if request.method == 'POST':
        form = CandidateCreationForm(
            request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            candidate = form.save()
            if candidate.stage_id is None:
                candidate.stage_id = Stage.objects.filter(
                    recruitment_id=candidate.recruitment_id, stage_type="initial").first()
            if candidate.stage_id.recruitment_id != candidate.recruitment_id:
                candidate.stage_id = candidate.recruitment_id.stage_set.filter(stage_type="initial").first()
            candidate.save()
            messages.success(request, _('Candidate Updated Successfully.'))
            return redirect('/recruitment/candidate-view')
    return render(request, 'candidate/candidate_create_form.html', {'form': form})


@login_required
@permission_required('recruitment.delete_candidate')
@require_http_methods(['DELETE', 'POST'])
def candidate_delete(request, id):
    """
    This method is used to delete candidate permanently
    Args:
        id : candidate_id
    """
    try:

        Candidate.objects.get(id=id).delete()
        messages.success(request, _('Candidate deleted successfully.'))
    except Exception as e:
        messages.error(request, e)
        messages.error(request, _('You cannot delete this candidate'))
    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))


@login_required
@permission_required('recruitment.delete_candidate')
def candidate_archive(request, id):
    """
    This method is used to archive or un-archive candidates
    """
    candidate = Candidate.objects.get(id=id)
    candidate.is_active = not candidate.is_active
    candidate.save()
    return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))


@login_required
@permission_required('recruitment.delete_candidate')
@require_http_methods(['POST'])
def candidate_bulk_delete(request):
    """
    This method is used to bulk delete candidates
    """
    ids = request.POST['ids']
    ids = json.loads(ids)
    for id in ids:
        candidate = Candidate.objects.get(id=id)
        try:
            candidate.delete()
            messages.success(request, _('%(candidate)s deleted.') % {'candidate':candidate})
        except Exception as e:
            messages.error(request, _('You cannot delete %(candidate)s') % {'candidate':candidate})
            messages.error(request, e)
    return JsonResponse({'message': 'Success'})


@login_required
@permission_required('recruitment.delete_candidate')
@require_http_methods(['POST'])
def candidate_bulk_archive(request):
    """
    This method is used to archive/un-archive bulk candidates
    """
    ids = request.POST['ids']
    ids = json.loads(ids)
    is_active = True
    message = 'un-archived'
    if request.GET.get('is_active') == 'False':
        is_active = False
        message = 'archived'

    for id in ids:
        candidate = Candidate.objects.get(id=id)
        candidate.is_active = is_active
        candidate.save()
        messages.success(request, f'{candidate} is {message}')

    return JsonResponse({'message': 'Success'})


@login_required
@permission_required('recruitment.view_history')
def candidate_history(request, id):
    """
    This method is used to view candidate stage changes
    Args:
        id : candidate_id

    """
    candidate = Candidate.objects.get(id=id)
    candidate_history = candidate.history.all()
    return render(request, 'candidate/candidate_history.html', {'history': candidate_history})


def application_form(request):
    """
    This method renders candidate form to create candidate"""

    form = ApplicationForm()
    if request.POST:
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            candidate = form.save(commit=False)
            recruitment = candidate.recruitment_id
            stages = recruitment.stage_set.all()
            if stages.filter(stage_type='initial').exists():
                candidate.stage_id = stages.filter(
                    stage_type='initial').first()
            else:
                candidate.stage_id = stages.order_by('sequence').first()
            candidate.save()
            messages.success(request, _('Application saved.'))
            return HttpResponseRedirect(request. META. get('HTTP_REFERER', '/'))
    return render(request, 'candidate/application_form.html', {'form': form})


@login_required
@hx_request_required
@manager_can_enter('recruitment.change_candidate')
def form_send_mail(request, id):
    """
    This method is used to render the bootstrap modal content body form
    """
    candidate = Candidate.objects.get(id=id)
    return render(request, 'pipeline/pipeline_components/send_mail.html', {'cand': candidate})


@login_required
@manager_can_enter('recruitment.change_candidate')
def send_acknowledgement(request):
    """
    This method is used to send acknowledgement mail to the candidate
    """
    try:
        to = request.POST.get('to')
        subject = request.POST.get('subject')
        bdy = request.POST.get('body')
        res = send_mail(subject, bdy, settings.EMAIL_HOST_USER,
                        [to], fail_silently=False)
        if (res == 1):
            return HttpResponse("""

        <div class="oh-alert-container">
            <div class="oh-alert oh-alert--animated oh-alert--success">
                Mail send.
            </div>
        </div>
    """)
    except:
        pass
    return HttpResponse("""

        <div class="oh-alert-container">
            <div class="oh-alert oh-alert--animated oh-alert--danger">
                Sorry, Something went wrong.
            </div>
        </div>
    """
                        )

@login_required
@manager_can_enter('view.recruitment')
def dashboard(request):
    
    """
    This method is used to render individual dashboard for recruitment module
    """
    candidates = Candidate.objects.all()
    hired_candidates = candidates.filter(hired=True)
    total_candidates = len(candidates)
    total_hired_candidates = len(hired_candidates)
    hire_ratio = 0
    if total_candidates != 0:
        hire_ratio = "%.1f" % ((total_hired_candidates/total_candidates)*100)

    return render(request, 'dashboard/dashboard.html', {
        'total_candidates': total_candidates,
        'total_hired_candidates': total_hired_candidates,
        'hire_ratio': hire_ratio,
        'onboard_candidates': hired_candidates.filter(start_onboard=True),
    })


def stage_type_candidate_count(rec, type):
    """
    This method is used find the count of candidate in recruitment
    """
    candidates_count = 0
    for stage in rec.stage_set.filter(stage_type=type):
        candidates_count = candidates_count + \
            len(stage.candidate_set.filter(is_active=True))
    return candidates_count


@login_required
@manager_can_enter('view.recruitment')
def dashboard_pipeline(request):
    """
    This method is used generate recruitment dataset for the dashboard
    """
    recruitment = Recruitment.objects.filter(closed=False)
    data_set = []
    labels = [type[1] for type in Stage.stage_types]
    for rec in recruitment:
        data = [stage_type_candidate_count(
            rec, type[0]) for type in Stage.stage_types]
        data_set.append({
            'label': rec.__str__(),
            'data': data,
        })
    return JsonResponse({'dataSet': data_set, 'labels': labels})
