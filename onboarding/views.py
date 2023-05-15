import secrets
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.contrib.auth import login
from horilla.decorators import login_required, hx_request_required
from django.http import HttpResponse, JsonResponse
from .forms import *
from recruitment.models import Candidate, Recruitment
from employee.models import Employee
from onboarding.models import OnboardingStage, OnboardingTask, CandidateStage, CandidateTask, OnboardingPortal
import json
from horilla.decorators import permission_required
from recruitment.filters import CandidateFilter
from django.contrib import messages
from django.core.paginator import Paginator
import random
from .decorators import all_manager_can_enter, stage_manager_can_enter, recruitment_manager_can_enter
from notifications.signals import notify


@login_required
@hx_request_required
@recruitment_manager_can_enter('onboarding.add_onboardingstage')
def stage_creation(request, id):
    """
    function used to create onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : recruitment id 

    Returns:
    GET : return onboarding stage creation form template
    POST : return stage save function
    """
    form = OnboardingViewStageForm()
    if request.method == "POST":
        recruitment = Recruitment.objects.get(id=id)
        form = OnboardingViewStageForm(request.POST)
        if form.is_valid():
            return stage_save(form, recruitment, request, id)
    return render(request, 'onboarding/stage-form.html', {'form': form, 'id': id})


def stage_save(form, recruitment, request, id):
    """
    function used to save onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    recruitment : recruitment object
    id : recruitment id 

    Returns:
    GET : return onboarding view 
    """
    stage = form.save()
    stage.recruitment_id.add(recruitment)
    stage.save()
    messages.success(request, _("New stage created successfully.."))
    users = [employee.employee_user_id for employee in stage.employee_id.all()]
    notify.send(
        request.user.employee_get,
        recipient=users,
        verb="You are choosen as onboarding stage manager",
        icon="people-circle",
        redirect="/onboarding/onboarding-view",
    )
    response = render(request, 'onboarding/stage-form.html',
                      {'form': form, 'id': id})
    return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')


@login_required
@hx_request_required
@recruitment_manager_can_enter('onboarding.change_onboardingstage')
def stage_update(request, stage_id, recruitment_id):
    """
    function used to update onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    stage_id : stage id
    recruitment_id : recruitment id 

    Returns:
    GET : return onboarding stage update form template
    POST : return onboarding view
    """
    onboarding_stage = OnboardingStage.objects.get(id=stage_id)
    form = OnboardingViewStageForm(instance=onboarding_stage)
    if request.method == 'POST':
        form = OnboardingViewStageForm(request.POST, instance=onboarding_stage)
        if form.is_valid():
            stage = form.save()
            messages.info(request, _('Stage is updated successfully..'))
            users = [
                employee.employee_user_id for employee in stage.employee_id.all()]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are choosen as onboarding stage manager",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
            response = render(request, 'onboarding/stage-update.html',
                              {'form': form, 'stage_id': stage_id, 'recruitment_id': recruitment_id})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'onboarding/stage-update.html', {'form': form, 'stage_id': stage_id, 'recruitment_id': recruitment_id})


@login_required
@permission_required('onboarding.delete_onboardingstage')
@recruitment_manager_can_enter('onboarding.delete_onboardingstage')
def stage_delete(request, stage_id):
    """  
    function used to delete onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    stage_id : stage id

    Returns:
    GET : return onboarding view
    """
    onboarding_stage = OnboardingStage.objects.get(id=stage_id)
    if not onboarding_stage.candidate.exists():
        onboarding_stage.delete()
        messages.success(request, _("the stage deleted successfully..."))
    else:
        messages.error(request, _("There are candidates in this stage..."))
    return redirect(onboarding_view)


@login_required
@hx_request_required
@stage_manager_can_enter('onboarding.add_onboardingtask')
def task_creation(request, id):
    """
    function used to create onboarding task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : recruitment id 

    Returns:
    GET : return onboarding task creation form template
    POST : return onboarding view
    """
    form = OnboardingViewTaskForm()
    if request.method == "POST":
        recruitment = Recruitment.objects.get(id=id)
        form_data = OnboardingViewTaskForm(request.POST)
        if form_data.is_valid():
            task = form_data.save()
            task.recruitment_id.add(recruitment)
            task.save()
            for candidate in recruitment.candidate.filter(hired=True, start_onboard=True):
                CandidateTask(candidate_id=candidate,
                              onboarding_task_id=task).save()

            messages.success(request, _("New task created successfully..."))
            users = [
                employee.employee_user_id for employee in task.employee_id.all()]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are choosen as onboarding task manager",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
            response = render(request, 'onboarding/task-form.html',
                              {'form': form, 'id': id})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    return render(request, 'onboarding/task-form.html', {'form': form, 'id': id})


@login_required
@hx_request_required
@stage_manager_can_enter('onboarding.change_onboardingtask')
def task_update(request, task_id, recruitment_id):
    """
    function used to update onboarding task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    task_id : task id
    recruitment_id : recruitment id 

    Returns:
    GET : return onboarding task update form template
    POST : return onboarding view
    """
    onboarding_task = OnboardingTask.objects.get(id=task_id)
    if request.method == 'POST':
        form = OnboardingViewTaskForm(request.POST, instance=onboarding_task)
        if form.is_valid():
            task = form.save()
            messages.info(request, _('Task updated successfully..'))
            users = [
                employee.employee_user_id for employee in task.employee_id.all()]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are choosen as onboarding task manager",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
            response = render(request, 'onboarding/task-update.html',
                              {'form': form, 'task_id': task_id, 'recruitment_id': recruitment_id})
            return HttpResponse(response.content.decode('utf-8') + '<script>location.reload();</script>')
    form = OnboardingViewTaskForm(instance=onboarding_task)
    return render(request, 'onboarding/task-update.html', {'form': form, 'task_id': task_id, 'recruitment_id': recruitment_id})


@login_required
@permission_required('onboarding.delete_onboardingtask')
@stage_manager_can_enter('onboarding.delete_onboardingtask')
def task_delete(request, task_id):
    """
    function used to delete onboarding task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    task_id : task id


    Returns:
    GET : return onboarding view
    """
    onboarding_task = OnboardingTask.objects.get(id=task_id)
    onboarding_task.delete()
    messages.success(request, _("The task deleted successfully..."))
    return redirect(onboarding_view)


@login_required
@permission_required('recruitment.add_candidate')
def candidate_creation(request):
    """
    function used to create hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return candidate creation form template
    POST : return candidate view
    """
    form = OnboardingCandidateForm()
    if request.method == 'POST':
        form = OnboardingCandidateForm(request.POST, request.FILES)
        if form.is_valid():
            candidate = form.save()
            candidate.hired = True
            candidate.save()
            messages.success(request, _(
                'New candidate created successfully..'))
            return redirect(candidates_view)
    return render(request, 'onboarding/candidate-creation.html', {'form': form})


@login_required
@permission_required('recruitment.change_candidate')
def candidate_update(request, id):
    """
    function used to update hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : recruitment id

    Returns:
    GET : return candidate update form template
    POST : return candidate view
    """
    candidate = Candidate.objects.get(id=id)
    form = OnboardingCandidateForm(instance=candidate)
    if request.method == 'POST':
        form = OnboardingCandidateForm(
            request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            form.save()
            messages.info(
                request, _('Candidate detail is updated successfully..'))
            return redirect(candidates_view)
    return render(request, 'onboarding/candidate-update.html', {'form': form})


@login_required
@permission_required('recruitment.delete_candidate')
def candidate_delete(request, id):
    """
    function used to delete hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : recruitment id

    Returns:
    GET : return candidate view
    """
    Candidate.objects.get(id=id).delete()
    messages.success(request, _('Candidate deleted successfully..'))
    return redirect(candidates_view)


def paginator_qry(qryset, page_number):
    """
    function used to paginate query set
    """
    paginator = Paginator(qryset, 25)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@permission_required('candidate.view_candidate')
def candidates_view(request):
    """
    function used to view hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return candidate view  template
    """
    queryset = Candidate.objects.filter(hired=True, start_onboard=False)
    candidate_filter = CandidateFilter()
    previous_data = request.environ['QUERY_STRING']
    page_number = request.GET.get('page')
    page_obj = paginator_qry(queryset, page_number)
    return render(request, 'onboarding/candidates-view.html', {'candidates': page_obj, 'form': candidate_filter.form, 'pd': previous_data})


@login_required
@permission_required('candidate.view_candidate')
def candidate_filter(request):
    """
    function used to filter hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return candidate view template 
    """
    queryset = Candidate.objects.filter(hired=True, start_onboard=False)
    candidate_filter = CandidateFilter(request.GET, queryset).qs
    previous_data = request.environ['QUERY_STRING']
    page_number = request.GET.get('page')
    page_obj = paginator_qry(candidate_filter, page_number)
    return render(request, 'onboarding/candidates.html', {'candidates': page_obj, 'pd': previous_data})


@login_required
def email_send(request):
    """
    function used to send onboarding portal for hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return json response
    """
    if request.method != 'POST':
        return JsonResponse('', safe=False)
    candidates = request.POST.get('candidates')
    json_mylist = json.loads(candidates)
    if len(json_mylist) <= 0:
        return JsonResponse({'message': _('No candidate choosed'), 'tags': 'danger'})
    for id in json_mylist:
        candidate = Candidate.objects.get(id=id)
        if candidate.start_onboard == False:
            token = secrets.token_hex(15)
            OnboardingPortal(candidate_id=candidate, token=token).save()
            send_mail(
                'Onboarding Portal',
                f'{request.get_host()}/onboarding/user-creation/{token}',
                'from@example.com',
                [candidate.email],
                fail_silently=False,
            )
            candidate.start_onboard = True
            candidate.save()
    return JsonResponse({'message': _('Email send successfully'), 'tags': 'success'})


@login_required
@all_manager_can_enter('onboarding.view_candidatestage')
def onboarding_view(request):
    """
    function used to view onboarding main view.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return onboarding view template
    """
    candidates = Candidate.objects.filter(hired=True, start_onboard=True)
    for candidate in candidates:
        if not CandidateStage.objects.filter(candidate_id=candidate).exists():
            try:
                onboarding_stage = OnboardingStage.objects.filter(
                    recruitment_id=candidate.recruitment_id).order_by('sequence')[0]
                CandidateStage(candidate_id=candidate,
                               onboarding_stage_id=onboarding_stage).save()
            except Exception as e:
                messages.error(request, _('%(recruitment)s has no stage..') % {
                               'recruitment': candidate.recruitment_id})
        if tasks := OnboardingTask.objects.filter(
            recruitment_id=candidate.recruitment_id
        ):
            for task in tasks:
                if not CandidateTask.objects.filter(candidate_id=candidate, onboarding_task_id=task).exists():
                    CandidateTask(candidate_id=candidate,
                                  onboarding_task_id=task).save()
    recruitments = Recruitment.objects.all()
    onboarding_stages = OnboardingStage.objects.all()
    choices = CandidateTask.Choice
    return render(request, 'onboarding/onboarding-view.html', {'recruitments': recruitments, 'onboarding_stages': onboarding_stages, 'choices': choices})


def user_creation(request, token):
    """
    function used to create user account in onboarding portal.

    Parameters:
    request (HttpRequest): The HTTP request object.
    token : random generated onboarding portal token

    Returns:
    GET : return user creation form template
    POST : return user_save function
    """
    try:
        onboarding_portal = OnboardingPortal.objects.get(token=token)
        form = UserCreationForm()
        if not onboarding_portal or onboarding_portal.used != False:
            return HttpResponse('Denied')
        try:
            if request.method == 'POST':
                form = UserCreationForm(request.POST)
                if form.is_valid():
                    return user_save(form, onboarding_portal, request, token)
        except Exception as e:
            messages.error(request, _('User with email-id already exists..'))
        return render(request, 'onboarding/user-creation.html', {'form': form})
    except Exception as e:
        return HttpResponse(e)


def user_save(form, onboarding_portal, request, token):
    """
    function used to save user.

    Parameters:
    request (HttpRequest): The HTTP request object.
    onboarding_portal : onboarding portal object
    token : random generated onboarding portal token

    Returns:
    GET : return profile view
    """
    user = form.save(commit=False)
    user.username = onboarding_portal.candidate_id.email
    user.save()
    onboarding_portal.used = True
    onboarding_portal.save()
    login(request, user)
    onboarding_portal.count += 1
    onboarding_portal.save()
    messages.success(request, _("Account created successfully.."))
    return redirect('profile-view', token)


def profile_view(request, token):
    """
    function used to view user profile.

    Parameters:
    request (HttpRequest): The HTTP request object.
    token : random generated onboarding portal token

    Returns:
    GET : return user profile template
    POST : update profile image of the user
    """
    candidate = Candidate.objects.get(email=request.user)
    if request.method == 'POST':
        profile = request.FILES.get('profile')
        if profile is not None:
            candidate.profile = profile
            candidate.save()
            messages.success(request, _(
                'Profile picture updated successfully..'))
    return render(request, 'onboarding/profile-view.html', {'candidate': candidate, 'token': token})


def employee_creation(request, token):
    """
    function used to create employee.

    Parameters:
    request (HttpRequest): The HTTP request object.
    token : random generated onboarding portal token.

    Returns:
    GET : return employee creation profile template.
    POST : return employee bank detail creation template.
    """
    candidate = Candidate.objects.get(email=request.user)
    onboarding_portal = OnboardingPortal.objects.get(token=token)
    form = EmployeeCreationForm(initial={
                                "employee_first_name": candidate.name, 'phone': candidate.mobile, 'address': candidate.address})
    if not Employee.objects.filter(employee_user_id=request.user).exists():
        if request.method == 'POST':
            form_data = EmployeeCreationForm(request.POST)
            if form_data.is_valid():
                employee_personal_info = form_data.save(commit=False)
                employee_personal_info.employee_user_id = request.user
                employee_personal_info.email = candidate.email
                employee_personal_info.employee_profile = candidate.profile
                employee_personal_info.save()
                onboarding_portal.count += 1
                onboarding_portal.save()
                messages.success(request, _(
                    "Employee personal details created successfully.."))
                return redirect('employee-bank-details', token)
        onboarding_portal.count += 1
        onboarding_portal.save()
        return render(request, 'onboarding/employee-creation.html', {'form': form})
    return redirect('employee-bank-details', token)


def employee_bank_details(request, token):
    """
    function used to create employee bank details creation.

    Parameters:
    request (HttpRequest): The HTTP request object.
    token : random generated onboarding portal token

    Returns:
    GET : return bank details creation template
    POST : return employee_bank_details_save function
    """
    onboarding_portal = OnboardingPortal.objects.get(token=token)
    form = BankDetailsCreationForm()
    employee_id = request.user.employee_get
    if not EmployeeBankDetails.objects.filter(employee_id=employee_id).exists():
        if request.method == 'POST':
            form = BankDetailsCreationForm(request.POST)
            if form.is_valid():
                return employee_bank_details_save(
                    form, request, onboarding_portal
                )
        return render(request, 'onboarding/employee-bank-details.html', {'form': form})
    return redirect(welcome_aboard)


# TODO Rename this here and in `employee_bank_details`
def employee_bank_details_save(form, request, onboarding_portal):
    """
    function used to save employee bank details.

    Parameters:
    request (HttpRequest): The HTTP request object.
    form : Form object.
    onboarding_portal : Onboarding portal object.

    Returns:
    GET : return welcome onboard view
    """
    employee_bank_detail = form.save(commit=False)
    employee_bank_detail.employee_id = Employee.objects.get(
        employee_user_id=request.user)
    employee_bank_detail.save()
    onboarding_portal.count += 1
    onboarding_portal.save()
    messages.success(request, _(
        "Employee bank details created successfully.."))
    return redirect(welcome_aboard)


@login_required
def welcome_aboard(request):
    """
    function used to view welcome aboard.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return welcome onboard view
    """
    return render(request, 'onboarding/welcome-aboard.html')


@login_required
@hx_request_required
@all_manager_can_enter('onboarding.change_candidatetask')
def candidate_task_update(request, id):
    """
    function used to update candidate task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    id : candidate task id

    Returns:
    POST : return candidate task template
    """
    if request.method == "POST":
        status = request.POST.get('task')
        candidate_task = CandidateTask.objects.get(id=id)
        candidate_task.status = status
        candidate_task.save()
        users = [employee.employee_user_id for employee in candidate_task.onboarding_task_id.employee_id.all()]
        notify.send(
                request.user.employee_get,
                recipient=users,
                verb=f"The task {candidate_task.onboarding_task_id} of {candidate_task.candidate_id} was updated to {candidate_task.status}.",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
        messages.info(request, _('Candidate task updated successfully..'))
        choices = CandidateTask.Choice
        return render(request, 'onboarding/candidate-task.html', {'choices': choices, 'task': candidate_task})


@login_required
@hx_request_required
@stage_manager_can_enter('onboarding.change_candidatestage')
def candidate_stage_update(request, candidate_id, recruitment_id):
    """
    function used to update candidate stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    candidate_id : Candidate id
    recruitment_id : Recruitment id

    Returns:
    POST : return candidate task template
    """
    if request.method == "POST":
        stage_id = request.POST.get('stage')
        recruitment = Recruitment.objects.get(id=recruitment_id)
        stage = OnboardingStage.objects.get(id=stage_id)
        candidate = Candidate.objects.get(id=candidate_id)
        candidate_stage = CandidateStage.objects.get(candidate_id=candidate)
        candidate_stage.onboarding_stage_id = stage
        candidate_stage.save()
        onboarding_stages = OnboardingStage.objects.all()
        choices = CandidateTask.Choice
        messages.info(request, _('Candidate stage updated successfully...'))
        users = [employee.employee_user_id for employee in candidate_stage.onboarding_stage_id.employee_id.all()]
        notify.send(
                request.user.employee_get,
                recipient=users,
                verb=f"The stage of {candidate_stage.candidate_id} was updated to {candidate_stage.onboarding_stage_id}.",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
        return render(request, 'onboarding/onboarding-table.html', {'recruitment': recruitment, 'onboarding_stages': onboarding_stages, 'choices': choices})


@login_required
def hired_candidate_chart(request):
    """
    function used to show hired candidates in all recruitments.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response labels, data, background_color, border_color.
    """
    labels = []
    data = []
    background_color = []
    border_color = []
    recruitments = Recruitment.objects.all()
    for recruitment in recruitments:
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        background_color.append(f"rgba({r}, {g}, {b}, 0.2")
        border_color.append(f"rgb({r}, {g}, {b})")
        labels.append(f"{recruitment}")
        data.append(recruitment.candidate.filter(
            hired=True).count())
    return JsonResponse({'labels': labels, 'data': data, 'background_color': background_color, 'border_color': border_color}, safe=False)


@login_required
def onboard_candidate_chart(request):
    """
    function used to show onboard started candidates in recruitments.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return Json response labels, data, background_color, border_color.
    """
    labels = []
    data = []
    background_color = []
    border_color = []
    recruitments = Recruitment.objects.all()
    for recruitment in recruitments:
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        background_color.append(f"rgba({r}, {g}, {b}, 0.2")
        border_color.append(f"rgb({r}, {g}, {b})")
        labels.append(
            f"{recruitment.job_position_id.job_position} | {recruitment.start_date}")
        data.append(recruitment.candidate.filter(
            hired=True, start_onboard=True).count())
    return JsonResponse({'labels': labels, 'data': data, 'background_color': background_color, 'border_color': border_color}, safe=False)
