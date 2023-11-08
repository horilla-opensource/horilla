"""
views.py

This module contains the view functions for handling HTTP requests and rendering
responses in your application.

Each view function corresponds to a specific URL route and performs the necessary
actions to handle the request, process data, and generate a response.

This module is part of the recruitment project and is intended to
provide the main entry points for interacting with the application's functionality.
"""
from urllib.parse import parse_qs
import json, contextlib, random, secrets
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from base.models import JobPosition
from notifications.signals import notify
from horilla import settings
from horilla.decorators import login_required, hx_request_required
from horilla.decorators import permission_required
from base.methods import get_key_instances
from recruitment.models import Candidate, Recruitment
from recruitment.filters import CandidateFilter
from employee.models import Employee, EmployeeWorkInformation, EmployeeBankDetails
from django.db.models import ProtectedError
from onboarding.forms import (
    OnboardingCandidateForm,
    UserCreationForm,
    OnboardingViewTaskForm,
    OnboardingViewStageForm,
    EmployeeCreationForm,
    BankDetailsCreationForm,
)
from onboarding.models import (
    OnboardingStage,
    OnboardingTask,
    CandidateStage,
    CandidateTask,
    OnboardingPortal,
)
from onboarding.decorators import (
    all_manager_can_enter,
    stage_manager_can_enter,
    recruitment_manager_can_enter,
)


@login_required
@hx_request_required
@recruitment_manager_can_enter("onboarding.add_onboardingstage")
def stage_creation(request, obj_id):
    """
    function used to create onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : recruitment id

    Returns:
    GET : return onboarding stage creation form template
    POST : return stage save function
    """
    form = OnboardingViewStageForm()
    if request.method == "POST":
        recruitment = Recruitment.objects.get(id=obj_id)
        form = OnboardingViewStageForm(request.POST)
        if form.is_valid():
            return stage_save(form, recruitment, request, obj_id)
    return render(request, "onboarding/stage_form.html", {"form": form, "id": obj_id})


def stage_save(form, recruitment, request, rec_id):
    """
    function used to save onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    recruitment : recruitment object
    rec_id : recruitment id

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
        verb="You are chosen as onboarding stage manager",
        verb_ar="لقد تم اختيارك كمدير مرحلة التدريب.",
        verb_de="Sie wurden als Onboarding-Stage-Manager ausgewählt.",
        verb_es="Ha sido seleccionado/a como responsable de etapa de incorporación.",
        verb_fr="Vous avez été choisi(e) en tant que responsable de l'étape d'intégration.",
        icon="people-circle",
        redirect="/onboarding/onboarding-view",
    )
    response = render(
        request, "onboarding/stage_form.html", {"form": form, "id": rec_id}
    )
    return HttpResponse(
        response.content.decode("utf-8") + "<script>location.reload();</script>"
    )


@login_required
@hx_request_required
@recruitment_manager_can_enter("onboarding.change_onboardingstage")
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
    if request.method == "POST":
        form = OnboardingViewStageForm(request.POST, instance=onboarding_stage)
        if form.is_valid():
            stage = form.save()
            messages.info(request, _("Stage is updated successfully.."))
            users = [employee.employee_user_id for employee in stage.employee_id.all()]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are chosen as onboarding stage manager",
                verb_ar="لقد تم اختيارك كمدير مرحلة التدريب.",
                verb_de="Sie wurden als Onboarding-Stage-Manager ausgewählt.",
                verb_es="Ha sido seleccionado/a como responsable de etapa de incorporación.",
                verb_fr="Vous avez été choisi(e) en tant que responsable de l'étape d'intégration.",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
            response = render(
                request,
                "onboarding/stage_update.html",
                {"form": form, "stage_id": stage_id, "recruitment_id": recruitment_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(
        request,
        "onboarding/stage_update.html",
        {"form": form, "stage_id": stage_id, "recruitment_id": recruitment_id},
    )


@login_required
@permission_required("onboarding.delete_onboardingstage")
@recruitment_manager_can_enter("onboarding.delete_onboardingstage")
def stage_delete(request, stage_id):
    """
    function used to delete onboarding stage.

    Parameters:
    request (HttpRequest): The HTTP request object.
    stage_id : stage id

    Returns:
    GET : return onboarding view
    """
    try:
        OnboardingStage.objects.get(id=stage_id).delete()
        messages.success(request, _("The stage deleted successfully..."))

    except OnboardingStage.DoesNotExist:
        messages.error(request, _("Stage not found."))
    except ProtectedError:
        messages.error(request, _("There are candidates in this stage..."))
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@hx_request_required
@stage_manager_can_enter("onboarding.add_onboardingtask")
def task_creation(request, obj_id):
    """
    function used to create onboarding task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : recruitment id

    Returns:
    GET : return onboarding task creation form template
    POST : return onboarding view
    """
    form = OnboardingViewTaskForm()
    if request.method == "POST":
        recruitment = Recruitment.objects.get(id=obj_id)
        form_data = OnboardingViewTaskForm(request.POST)
        if form_data.is_valid():
            task = form_data.save()
            task.recruitment_id.add(recruitment)
            task.save()
            for candidate in recruitment.candidate.filter(
                hired=True, start_onboard=True
            ):
                CandidateTask(candidate_id=candidate, onboarding_task_id=task).save()

            messages.success(request, _("New task created successfully..."))
            users = [employee.employee_user_id for employee in task.employee_id.all()]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are chosen as an onboarding task manager",
                verb_ar="لقد تم اختيارك كمدير مهام التدريب.",
                verb_de="Sie wurden als Onboarding-Aufgabenmanager ausgewählt.",
                verb_es="Ha sido seleccionado/a como responsable de tareas de incorporación.",
                verb_fr="Vous avez été choisi(e) en tant que responsable des tâches d'intégration.",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
            response = render(
                request, "onboarding/task_form.html", {"form": form, "id": obj_id}
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    return render(request, "onboarding/task_form.html", {"form": form, "id": obj_id})


@login_required
@hx_request_required
@stage_manager_can_enter("onboarding.change_onboardingtask")
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
    if request.method == "POST":
        form = OnboardingViewTaskForm(request.POST, instance=onboarding_task)
        if form.is_valid():
            task = form.save()
            messages.info(request, _("Task updated successfully.."))
            users = [employee.employee_user_id for employee in task.employee_id.all()]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb="You are chosen as an onboarding task manager",
                verb_ar="لقد تم اختيارك كمدير مهام التدريب.",
                verb_de="Sie wurden als Onboarding-Aufgabenmanager ausgewählt.",
                verb_es="Ha sido seleccionado/a como responsable de tareas de incorporación.",
                verb_fr="Vous avez été choisi(e) en tant que responsable des tâches d'intégration.",
                icon="people-circle",
                redirect="/onboarding/onboarding-view",
            )
            response = render(
                request,
                "onboarding/task_update.html",
                {"form": form, "task_id": task_id, "recruitment_id": recruitment_id},
            )
            return HttpResponse(
                response.content.decode("utf-8") + "<script>location.reload();</script>"
            )
    form = OnboardingViewTaskForm(instance=onboarding_task)
    return render(
        request,
        "onboarding/task_update.html",
        {"form": form, "task_id": task_id, "recruitment_id": recruitment_id},
    )


@login_required
@permission_required("onboarding.delete_onboardingtask")
@stage_manager_can_enter("onboarding.delete_onboardingtask")
def task_delete(request, task_id):
    """
    function used to delete onboarding task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    task_id : task id


    Returns:
    GET : return onboarding view
    """
    try:
        OnboardingTask.objects.get(id=task_id).delete()
        messages.success(request, _("The task deleted successfully..."))
    except OnboardingTask.DoesNotExist:
        messages.error(request, _("Task not found."))
    except ProtectedError:
        messages.error(
            request,
            _(
                "You cannot delete this task because some candidates are associated with it."
            ),
        )
    return redirect(onboarding_view)


@login_required
@permission_required("recruitment.add_candidate")
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
    if request.method == "POST":
        form = OnboardingCandidateForm(request.POST, request.FILES)
        if form.is_valid():
            candidate = form.save()
            candidate.hired = True
            candidate.save()
            messages.success(request, _("New candidate created successfully.."))
            return redirect(candidates_view)
    return render(request, "onboarding/candidate_creation.html", {"form": form})


@login_required
@permission_required("recruitment.change_candidate")
def candidate_update(request, obj_id):
    """
    function used to update hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : recruitment id

    Returns:
    GET : return candidate update form template
    POST : return candidate view
    """
    candidate = Candidate.objects.get(id=obj_id)
    form = OnboardingCandidateForm(instance=candidate)
    if request.method == "POST":
        form = OnboardingCandidateForm(request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            form.save()
            messages.info(request, _("Candidate detail is updated successfully.."))
            return redirect(candidates_view)
    return render(request, "onboarding/candidate_update.html", {"form": form})


@login_required
@permission_required("recruitment.delete_candidate")
def candidate_delete(request, obj_id):
    """
    function used to delete hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : recruitment id

    Returns:
    GET : return candidate view
    """
    try:
        Candidate.objects.get(id=obj_id).delete()
        messages.success(request, _("Candidate deleted successfully.."))
    except Candidate.DoesNotExist:
        messages.error(request, _("Candidate not found."))
    except ProtectedError as e:
        models_verbose_name_sets = set()
        for obj in e.protected_objects:
            models_verbose_name_sets.add(__(obj._meta.verbose_name))
        models_verbose_name_str = (", ").join(models_verbose_name_sets)
        messages.error(
            request,
            _(
                "You cannot delete this candidate. The candidate is included in the {}".format(
                    models_verbose_name_str
                )
            ),
        )
    return redirect(candidates_view)


@login_required
@permission_required("recruitment.view_candidate")
def candidates_single_view(request, id, **kwargs):
    """
    Candidate individual view for the onboarding candidates
    """
    candidate = Candidate.objects.get(id=id)
    if not CandidateStage.objects.filter(candidate_id=candidate).exists():
        try:
            onboarding_stage = OnboardingStage.objects.filter(
                recruitment_id=candidate.recruitment_id
            ).order_by("sequence")[0]
            CandidateStage(
                candidate_id=candidate, onboarding_stage_id=onboarding_stage
            ).save()
        except Exception:
            messages.error(
                request,
                _("%(recruitment)s has no stage..")
                % {"recruitment": candidate.recruitment_id},
            )
        if tasks := OnboardingTask.objects.filter(
            recruitment_id=candidate.recruitment_id
        ):
            for task in tasks:
                if not CandidateTask.objects.filter(
                    candidate_id=candidate, onboarding_task_id=task
                ).exists():
                    CandidateTask(
                        candidate_id=candidate, onboarding_task_id=task
                    ).save()

    recruitment = candidate.recruitment_id
    choices = CandidateTask.choice
    context = {
        "recruitment": recruitment,
        "choices": choices,
        "candidate": candidate,
    }
    return render(
        request,
        "onboarding/single_view.html",
        context,
    )


def paginator_qry(qryset, page_number):
    """
    function used to paginate query set
    """
    paginator = Paginator(qryset, 25)
    qryset = paginator.get_page(page_number)
    return qryset


@login_required
@permission_required("candidate.view_candidate")
def candidates_view(request):
    """
    function used to view hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return candidate view  template
    """
    queryset = Candidate.objects.filter(hired=True, start_onboard=False)
    candidate_filter_obj = CandidateFilter()
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    page_obj = paginator_qry(queryset, page_number)
    return render(
        request,
        "onboarding/candidates_view.html",
        {
            "candidates": page_obj,
            "form": candidate_filter_obj.form,
            "pd": previous_data,
        },
    )


@login_required
@permission_required(perm="recruitment.view_candidate")
def hired_candidate_view(request):
    previous_data = request.GET.urlencode()
    candidates = Candidate.objects.filter(hired=True)
    if request.GET.get("is_active") is None:
        candidates = candidates.filter(is_active=True)
    candidates = CandidateFilter(request.GET, queryset=candidates).qs
    return render(
        request,
        "candidate/candidate_card.html",
        {
            "data": paginator_qry(candidates, request.GET.get("page")),
            "pd": previous_data,
        },
    )


@login_required
@permission_required("candidate.view_candidate")
def candidate_filter(request):
    """
    function used to filter hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return candidate view template
    """
    queryset = Candidate.objects.filter(hired=True, start_onboard=False)
    candidate_filter_obj = CandidateFilter(request.GET, queryset).qs
    previous_data = request.GET.urlencode()
    page_number = request.GET.get("page")
    data_dict = parse_qs(previous_data)
    get_key_instances(Candidate, data_dict)
    page_obj = paginator_qry(candidate_filter_obj, page_number)
    return render(
        request,
        "onboarding/candidates.html",
        {"candidates": page_obj, "pd": previous_data, "filter_dict": data_dict},
    )


@login_required
def email_send(request):
    """
    function used to send onboarding portal for hired candidates .

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return json response
    """
    if request.method != "POST":
        return JsonResponse("", safe=False)
    candidates = request.POST.get("candidates")
    json_list = json.loads(candidates)
    if len(json_list) <= 0:
        return JsonResponse(
            {"message": _("No candidate has chosen."), "tags": "danger"}
        )
    for cand_id in json_list:
        candidate = Candidate.objects.get(id=cand_id)
        if candidate.start_onboard is False:
            token = secrets.token_hex(15)
            existing_portal = OnboardingPortal.objects.filter(candidate_id=candidate)
            if existing_portal.exists():
                new_portal = existing_portal.first()
                new_portal.token = token
                new_portal.used = False
                new_portal.save()
            else:
                OnboardingPortal(candidate_id=candidate, token=token).save()
            send_mail(
                "Onboarding Portal",
                f"{request.get_host()}/onboarding/user-creation/{token}",
                "from@example.com",
                [candidate.email],
                fail_silently=False,
            )
            candidate.start_onboard = True
            candidate.save()
    return JsonResponse({"message": _("Email send successfully"), "tags": "success"})


@login_required
@all_manager_can_enter("onboarding.view_candidatestage")
def onboarding_view(request):
    """
    function used to view onboarding main view.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return onboarding view template
    """
    candidates = Candidate.objects.filter(hired=True, start_onboard=True)
    job_positions = JobPosition.objects.all()
    for candidate in candidates:
        if not CandidateStage.objects.filter(candidate_id=candidate).exists():
            try:
                onboarding_stage = OnboardingStage.objects.filter(
                    recruitment_id=candidate.recruitment_id
                ).order_by("sequence")[0]
                CandidateStage(
                    candidate_id=candidate, onboarding_stage_id=onboarding_stage
                ).save()
            except Exception:
                messages.error(
                    request,
                    _("%(recruitment)s has no stage..")
                    % {"recruitment": candidate.recruitment_id},
                )
        if tasks := OnboardingTask.objects.filter(
            recruitment_id=candidate.recruitment_id
        ):
            for task in tasks:
                if not CandidateTask.objects.filter(
                    candidate_id=candidate, onboarding_task_id=task
                ).exists():
                    CandidateTask(
                        candidate_id=candidate, onboarding_task_id=task
                    ).save()

    recruitments = Recruitment.objects.filter(closed=False)
    status = "closed"
    if request.GET.get("closed") == "closed":
        recruitments = Recruitment.objects.filter(closed=True)
        status = ""

    onboarding_stages = OnboardingStage.objects.all()
    choices = CandidateTask.choice
    return render(
        request,
        "onboarding/onboarding_view.html",
        {
            "recruitments": recruitments,
            "onboarding_stages": onboarding_stages,
            "choices": choices,
            "job_positions": job_positions,
            "status": status,
        },
    )


@login_required
@all_manager_can_enter("onboarding.view_candidatestage")
def kanban_view(request):
    candidates = Candidate.objects.filter(hired=True, start_onboard=True)
    job_positions = JobPosition.objects.all()
    for candidate in candidates:
        if not CandidateStage.objects.filter(candidate_id=candidate).exists():
            try:
                onboarding_stage = OnboardingStage.objects.filter(
                    recruitment_id=candidate.recruitment_id
                ).order_by("sequence")[0]
                CandidateStage(
                    candidate_id=candidate, onboarding_stage_id=onboarding_stage
                ).save()
            except Exception:
                messages.error(
                    request,
                    _("%(recruitment)s has no stage..")
                    % {"recruitment": candidate.recruitment_id},
                )
        if tasks := OnboardingTask.objects.filter(
            recruitment_id=candidate.recruitment_id
        ):
            for task in tasks:
                if not CandidateTask.objects.filter(
                    candidate_id=candidate, onboarding_task_id=task
                ).exists():
                    CandidateTask(
                        candidate_id=candidate, onboarding_task_id=task
                    ).save()

    recruitments = Recruitment.objects.filter(closed=False)
    status = "closed"
    if request.GET.get("closed") == "closed":
        recruitments = Recruitment.objects.filter(closed=True)
        status = ""
    onboarding_stages = OnboardingStage.objects.all()
    choices = CandidateTask.choice
    stage_form = OnboardingViewStageForm()
    return render(
        request,
        "onboarding/kanban/kanban.html",
        {
            "recruitments": recruitments,
            "onboarding_stages": onboarding_stages,
            "choices": choices,
            "job_positions": job_positions,
            "stage_form": stage_form,
            "status": status,
            "choices": choices,
        },
    )


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
        candidate = onboarding_portal.candidate_id
        user = User.objects.filter(username=candidate.email).first()

        form = UserCreationForm(instance=user)
        if (
            not onboarding_portal
            or onboarding_portal.used is True
            and request.user.is_anonymous
        ):
            return HttpResponse("Denied")
        try:
            if request.method == "POST":
                form = UserCreationForm(request.POST, instance=user)
                if form.is_valid():
                    return user_save(form, onboarding_portal, request, token)
        except Exception:
            messages.error(request, _("User with email-id already exists.."))
        return render(
            request,
            "onboarding/user_creation.html",
            {
                "form": form,
                "company": onboarding_portal.candidate_id.recruitment_id.company_id,
            },
        )
    except Exception as error:
        return HttpResponse(error)


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
    onboarding_portal.count = 1
    messages.success(request, _("Account created successfully.."))
    return redirect("profile-view", token)


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
    onboarding_portal = OnboardingPortal.objects.filter(token=token).first()
    if onboarding_portal is None:
        return HttpResponse("Denied")
    candidate = onboarding_portal.candidate_id
    user = User.objects.get(username=candidate.email)
    if request.method == "POST":
        profile = request.FILES.get("profile")
        if profile is not None:
            candidate.profile = profile
            candidate.save()
            onboarding_portal.count = 2
            messages.success(request, _("Profile picture updated successfully.."))
    return render(
        request,
        "onboarding/profile_view.html",
        {
            "candidate": candidate,
            "token": token,
            "company": candidate.recruitment_id.company_id,
        },
    )


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
    onboarding_portal = OnboardingPortal.objects.filter(token=token).first()
    if onboarding_portal is None:
        return HttpResponse("Denied.")
    candidate = onboarding_portal.candidate_id
    initial = {
        "employee_first_name": candidate.name,
        "phone": candidate.mobile,
        "address": candidate.address,
        "dob": candidate.dob,
    }
    user = User.objects.filter(username=candidate.email).first()
    if Employee.objects.filter(employee_user_id=user).first() is not None:
        initial = Employee.objects.filter(employee_user_id=user).first().__dict__

    form = EmployeeCreationForm(
        initial,
    )
    form.errors.clear()
    if request.method == "POST":
        instance = Employee.objects.filter(employee_user_id=user).first()
        form_data = EmployeeCreationForm(
            request.POST,
            instance=instance,
        )
        if form_data.is_valid():
            employee_personal_info = form_data.save(commit=False)
            employee_personal_info.employee_user_id = user
            employee_personal_info.email = candidate.email
            employee_personal_info.employee_profile = candidate.profile
            employee_personal_info.save()
            job_position = onboarding_portal.candidate_id.job_position_id
            work_info = EmployeeWorkInformation.objects.get_or_create(
                employee_id=employee_personal_info,
                job_position_id=job_position,
            )
            work_info[0].date_joining = candidate.joining_date
            work_info[0].save()
            onboarding_portal.count = 3
            onboarding_portal.save()
            messages.success(
                request, _("Employee personal details created successfully..")
            )
            return redirect("employee-bank-details", token)
    onboarding_portal.count += 1
    onboarding_portal.save()
    return render(
        request,
        "onboarding/employee_creation.html",
        {"form": form, "employee": candidate.recruitment_id.company_id},
    )


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
    user = User.objects.filter(username=onboarding_portal.candidate_id.email).first()
    employee = Employee.objects.filter(employee_user_id=user).first()
    form = BankDetailsCreationForm(
        instance=EmployeeBankDetails.objects.filter(employee_id=employee).first()
    )
    if request.method == "POST":
        form = BankDetailsCreationForm(
            request.POST,
            instance=EmployeeBankDetails.objects.filter(employee_id=employee).first(),
        )
        if form.is_valid():
            return employee_bank_details_save(form, request, onboarding_portal)
        return redirect(welcome_aboard)
    return render(
        request,
        "onboarding/employee_bank_details.html",
        {
            "form": form,
            "company": onboarding_portal.candidate_id.recruitment_id.company_id,
        },
    )


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
        employee_user_id=request.user
    )
    employee_bank_detail.save()
    onboarding_portal.count = 4
    onboarding_portal.save()
    messages.success(request, _("Employee bank details created successfully.."))
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
    return render(request, "onboarding/welcome_aboard.html")


@login_required
@hx_request_required
@require_http_methods(["POST"])
@all_manager_can_enter("onboarding.change_candidatetask")
def candidate_task_update(request, obj_id):
    """
    function used to update candidate task.

    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : candidate task id

    Returns:
    POST : return candidate task template
    """
    status = request.POST.get("task")
    candidate_task = CandidateTask.objects.get(id=obj_id)
    candidate_task.status = status
    candidate_task.save()
    users = [
        employee.employee_user_id
        for employee in candidate_task.onboarding_task_id.employee_id.all()
    ]
    notify.send(
        request.user.employee_get,
        recipient=users,
        verb=f"The task {candidate_task.onboarding_task_id} of\
            {candidate_task.candidate_id} was updated to {candidate_task.status}.",
        verb_ar=f"تم تحديث المهمة {candidate_task.onboarding_task_id} للمرشح {candidate_task.candidate_id} إلى {candidate_task.status}.",
        verb_de=f"Die Aufgabe {candidate_task.onboarding_task_id} des Kandidaten {candidate_task.candidate_id} wurde auf {candidate_task.status} aktualisiert.",
        verb_es=f"La tarea {candidate_task.onboarding_task_id} del candidato {candidate_task.candidate_id} se ha actualizado a {candidate_task.status}.",
        verb_fr=f"La tâche {candidate_task.onboarding_task_id} du candidat {candidate_task.candidate_id} a été mise à jour à {candidate_task.status}.",
        icon="people-circle",
        redirect="/onboarding/onboarding-view",
    )
    choices = CandidateTask.choice
    return render(
        request,
        "onboarding/candidate_task.html",
        {"choices": choices, "task": candidate_task},
    )


@login_required
@require_http_methods(["POST"])
@stage_manager_can_enter("onboarding.change_candidatestage")
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
    stage_id = request.POST.get("stage")
    recruitment = Recruitment.objects.get(id=recruitment_id)
    stage = OnboardingStage.objects.get(id=stage_id)
    candidate = Candidate.objects.get(id=candidate_id)
    candidate_stage = CandidateStage.objects.get(candidate_id=candidate)
    candidate_stage.onboarding_stage_id = stage
    candidate_stage.save()
    onboarding_stages = OnboardingStage.objects.all()
    choices = CandidateTask.choice
    users = [
        employee.employee_user_id
        for employee in candidate_stage.onboarding_stage_id.employee_id.all()
    ]
    if request.POST.get("is_ajax") is None:
        notify.send(
            request.user.employee_get,
            recipient=users,
            verb=f"The stage of {candidate_stage.candidate_id} \
                was updated to {candidate_stage.onboarding_stage_id}.",
            verb_ar=f"تم تحديث مرحلة المرشح {candidate_stage.candidate_id} إلى {candidate_stage.onboarding_stage_id}.",
            verb_de=f"Die Phase des Kandidaten {candidate_stage.candidate_id} wurde auf {candidate_stage.onboarding_stage_id} aktualisiert.",
            verb_es=f"La etapa del candidato {candidate_stage.candidate_id} se ha actualizado a {candidate_stage.onboarding_stage_id}.",
            verb_fr=f"L'étape du candidat {candidate_stage.candidate_id} a été mise à jour à {candidate_stage.onboarding_stage_id}.",
            icon="people-circle",
            redirect="/onboarding/onboarding-view",
        )
        return render(
            request,
            "onboarding/onboarding_table.html",
            {
                "recruitment": recruitment,
                "onboarding_stages": onboarding_stages,
                "choices": choices,
            },
        )
    return JsonResponse(
        {"message": _("Candidate onboarding stage updated"), "type": "success"}
    )


@login_required
@require_http_methods(["POST"])
@stage_manager_can_enter("onboarding.change_candidatestage")
def candidate_stage_bulk_update(request):
    candiate_ids = request.POST["ids"]
    recrutment_id = request.POST["recruitment"]
    candidate_id_list = json.loads(candiate_ids)
    stage = request.POST["stage"]
    onboarding_stages = OnboardingStage.objects.all()
    recruitment = Recruitment.objects.get(id=int(recrutment_id))
    choices = CandidateTask.choice

    count = CandidateStage.objects.filter(
        candidate_id__id__in=candidate_id_list
    ).update(onboarding_stage_id=stage)

    response = render(
        request,
        "onboarding/onboarding_table.html",
        {
            "recruitment": recruitment,
            "onboarding_stages": onboarding_stages,
            "choices": choices,
        },
    )

    return HttpResponse(
        response.content.decode("utf-8")
        + '<div><div class="oh-alert-container"><div class="oh-alert oh-alert--animated oh-alert--info">candidate stage updated successfully</div> </div></div>'
    )


@login_required
@require_http_methods(["POST"])
@all_manager_can_enter("onboarding.change_candidatetask")
def candidate_task_bulk_update(request):
    candiate_ids = request.POST["ids"]
    candidate_id_list = json.loads(candiate_ids)
    task = request.POST["task"]
    status = request.POST["status"]

    count = CandidateTask.objects.filter(
        candidate_id__id__in=candidate_id_list, onboarding_task_id=task
    ).update(status=status)
    # messages.success(request,f"{count} candidate's task status updated successfully")

    return JsonResponse(
        {"message": _("Candidate onboarding stage updated"), "type": "success"}
    )


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
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)
        background_color.append(f"rgba({red}, {green}, {blue}, 0.2")
        border_color.append(f"rgb({red}, {green}, {blue})")
        labels.append(f"{recruitment}")
        data.append(recruitment.candidate.filter(hired=True).count())
    return JsonResponse(
        {
            "labels": labels,
            "data": data,
            "background_color": background_color,
            "border_color": border_color,
            "message": _("No data Found..."),
        },
        safe=False,
    )


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
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)
        background_color.append(f"rgba({red}, {green}, {blue}, 0.2")
        border_color.append(f"rgb({red}, {green}, {blue})")
        labels.append(recruitment.title)
        data.append(
            recruitment.candidate.filter(hired=True, start_onboard=True).count()
        )
    return JsonResponse(
        {
            "labels": labels,
            "data": data,
            "background_color": background_color,
            "border_color": border_color,
            "message": _("No data Found..."),
        },
        safe=False,
    )


@login_required
@permission_required("candidate.view_candidate")
def update_joining(request):
    """
    Ajax method to update joinng date
    """
    cand_id = request.POST["candId"]
    date = request.POST["date"]
    candidate_obj = Candidate.objects.get(id=cand_id)
    candidate_obj.joining_date = date
    candidate_obj.save()
    return JsonResponse(
        {
            "type": "success",
            "message": _("{candidate}'s Date of joining updated sussefully").format(
                candidate=candidate_obj.name
            ),
        }
    )


@login_required
@permission_required("candidate.view_candidate")
def view_dashboard(request):
    recruitment = Recruitment.objects.all().values_list("title", flat=True)
    candidates = Candidate.objects.all()
    hired = candidates.filter(start_onboard=True)
    onboard_candidates = Candidate.objects.filter(start_onboard=True)
    job_positions = onboard_candidates.values_list(
        "job_position_id__job_position", flat=True
    )

    context = {
        "recruitment": list(recruitment),
        "candidates": candidates,
        "hired": hired,
        "onboard_candidates": onboard_candidates,
        "job_positions": list(set(job_positions)),
    }
    return render(request, "onboarding/dashboard.html", context=context)


@login_required
@permission_required("candidate.view_candidate")
def dashboard_stage_chart(request):
    recruitment = request.GET.get("recruitment")
    labels = OnboardingStage.objects.filter(
        recruitment_id__title=recruitment
    ).values_list("stage_title", flat=True)
    labels = list(labels)
    candidate_counts = []
    border_color = []
    background_color = []
    for label in labels:
        red = random.randint(0, 255)
        green = random.randint(0, 255)
        blue = random.randint(0, 255)
        background_color.append(f"rgba({red}, {green}, {blue}, 0.3")
        border_color.append(f"rgb({red}, {green}, {blue})")
        count = CandidateStage.objects.filter(
            onboarding_stage_id__stage_title=label,
            onboarding_stage_id__recruitment_id__title=recruitment,
        ).count()
        candidate_counts.append(count)

    response = {
        "labels": labels,
        "data": candidate_counts,
        "recruitment": recruitment,
        "background_color": background_color,
        "border_color": border_color,
        "message": _("No candidates started onboarding...."),
    }
    return JsonResponse(response)


@login_required
@stage_manager_can_enter("recruitment.change_candidate")
def candidate_sequence_update(request):
    """
    This method is used to update the sequence of candidate
    """
    sequence_data = json.loads(request.POST["sequenceData"])
    updated = False
    for cand_id, seq in sequence_data.items():
        cand = CandidateStage.objects.get(id=cand_id)
        if cand.sequence != seq:
            cand.sequence = seq
            cand.save()
            updated = True
    if updated:
        return JsonResponse(
            {"message": _("Candidate sequence updated"), "type": "info"}
        )
    return JsonResponse({"type": "fail"})


@login_required
@stage_manager_can_enter("recruitment.change_stage")
def stage_sequence_update(request):
    """
    This method is used to update the sequence of the stages
    """
    sequence_data = json.loads(request.POST["sequenceData"])
    updated = False

    for stage_id, seq in sequence_data.items():
        stage = OnboardingStage.objects.get(id=stage_id)
        if stage.sequence != seq:
            stage.sequence = seq
            stage.save()
            updated = True

    if updated:
        return JsonResponse({"type": "success", "message": _("Stage sequence updated")})
    return JsonResponse({"type": "fail"})


@login_required
@require_http_methods(["POST"])
@hx_request_required
def stage_name_update(request, stage_id):
    """
    This method is used to update the name of recruitment stage
    """
    stage_obj = OnboardingStage.objects.get(id=stage_id)
    stage_obj.stage_title = request.POST["stage"]
    stage_obj.save()
    message = _("The stage title has been updated successfully")
    return HttpResponse(
        f'<div class="oh-alert-container"><div class="oh-alert oh-alert--animated oh-alert--success">{message}</div></div>'
    )


@login_required
@stage_manager_can_enter("recruitment.change_candidate")
def onboarding_send_mail(request, candidate_id):
    """
    This method is used to send mail to the candidate from onboarding view
    """
    candidate = Candidate.objects.get(id=candidate_id)
    candidate_mail = candidate.email
    response = render(
        request, "onboarding/send_mail_form.html", {"candidate": candidate}
    )
    if request.method == "POST":
        subject = request.POST["subject"]
        body = request.POST["body"]
        with contextlib.suppress(Exception):
            res = send_mail(
                subject,
                body,
                settings.EMAIL_HOST_USER,
                [candidate_mail],
                fail_silently=False,
            )
            if res == 1:
                messages.success(request, _("Mail sent successfully"))
            else:
                messages.error(request, _("Something went wrong"))
        return HttpResponse(
            response.content.decode("utf-8") + "<script>location.reload();</script>"
        )

    return response
