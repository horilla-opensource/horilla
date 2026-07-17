from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from hydra_people.selectors import person_for_user
from hydra_tasks.forms import (
    TaskCreateForm,
    TaskReassignForm,
    TaskTransitionForm,
    TaskUpdateForm,
)
from hydra_tasks.models import HydraTask
from hydra_tasks.selectors import (
    task_events_for_user,
    task_for_user,
    tasks_for_user,
)
from hydra_tasks.services import (
    ALLOWED_TRANSITIONS,
    create_task,
    reassign_task,
    transition_task,
    update_task,
)
from hydra_tasks.targets import target_url_for_user


def _add_service_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            target = field if field in form.fields else None
            for message in errors:
                form.add_error(target, message)
    else:
        for message in error.messages:
            form.add_error(None, message)


@login_required
@permission_required("hydra_tasks.view_hydratask", raise_exception=True)
@never_cache
def task_list(request):
    filters = {
        "query": request.GET.get("q", ""),
        "status": request.GET.get("status", ""),
        "priority": request.GET.get("priority", ""),
        "ownership": request.GET.get("ownership", ""),
        "due": request.GET.get("due", ""),
    }
    queryset = tasks_for_user(user=request.user, **filters)
    page_obj = Paginator(queryset, 50).get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(
        request,
        "hydra_tasks/task_list.html",
        {
            "page_obj": page_obj,
            "tasks": page_obj.object_list,
            "filters": filters,
            "status_choices": HydraTask.Status.choices,
            "priority_choices": HydraTask.Priority.choices,
            "filter_query": query_params.urlencode(),
        },
    )


@login_required
@permission_required("hydra_tasks.view_hydratask", raise_exception=True)
@never_cache
def task_detail(request, task_uuid):
    task = task_for_user(user=request.user, task_uuid=task_uuid)
    allowed_statuses = ALLOWED_TRANSITIONS.get(task.status, set())
    can_operate = task.assignee_id == request.user.pk or (
        request.user.is_superuser
        or request.user.has_perm("hydra_tasks.view_all_hydratask")
    )
    if not can_operate or (
        task.status in (HydraTask.Status.COMPLETED, HydraTask.Status.CANCELLED)
        and not request.user.has_perm("hydra_tasks.reopen_hydratask")
    ):
        allowed_statuses = set()
    return render(
        request,
        "hydra_tasks/task_detail.html",
        {
            "task": task,
            "events": task_events_for_user(user=request.user, task=task),
            "target_url": target_url_for_user(user=request.user, task=task),
            "allowed_statuses": allowed_statuses,
        },
    )


@login_required
@permission_required("hydra_tasks.add_hydratask", raise_exception=True)
@never_cache
@require_http_methods(["GET", "POST"])
def task_create(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    form = TaskCreateForm(
        request.POST or None,
        user=request.user,
        person=person,
    )
    if request.method == "POST" and form.is_valid():
        try:
            task = create_task(
                actor=request.user,
                person_uuid=person.uuid,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _add_service_errors(form, error)
        else:
            messages.success(request, _("Task created."))
            return redirect(task)
    return render(
        request,
        "hydra_tasks/task_form.html",
        {"form": form, "person": person, "heading": _("Create task")},
    )


@login_required
@permission_required("hydra_tasks.change_hydratask", raise_exception=True)
@never_cache
@require_http_methods(["GET", "POST"])
def task_update(request, task_uuid):
    task = task_for_user(user=request.user, task_uuid=task_uuid)
    form = TaskUpdateForm(request.POST or None, task=task)
    if request.method == "POST" and form.is_valid():
        try:
            task = update_task(
                actor=request.user,
                task_uuid=task.uuid,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _add_service_errors(form, error)
        else:
            messages.success(request, _("Task updated."))
            return redirect(task)
    return render(
        request,
        "hydra_tasks/task_form.html",
        {
            "form": form,
            "person": task.person,
            "task": task,
            "heading": _("Edit task"),
        },
    )


@login_required
@permission_required("hydra_tasks.assign_hydratask", raise_exception=True)
@never_cache
@require_http_methods(["GET", "POST"])
def task_reassign(request, task_uuid):
    task = task_for_user(user=request.user, task_uuid=task_uuid)
    form = TaskReassignForm(request.POST or None, task=task)
    if request.method == "POST" and form.is_valid():
        try:
            task = reassign_task(
                actor=request.user,
                task_uuid=task.uuid,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _add_service_errors(form, error)
        else:
            messages.success(request, _("Task reassigned."))
            return redirect(task)
    return render(
        request,
        "hydra_tasks/task_form.html",
        {
            "form": form,
            "person": task.person,
            "task": task,
            "heading": _("Reassign task"),
        },
    )


@login_required
@permission_required("hydra_tasks.transition_hydratask", raise_exception=True)
@never_cache
@require_http_methods(["GET", "POST"])
def task_transition(request, task_uuid):
    task = task_for_user(user=request.user, task_uuid=task_uuid)
    if task.assignee_id != request.user.pk and not (
        request.user.is_superuser
        or request.user.has_perm("hydra_tasks.view_all_hydratask")
    ):
        raise PermissionDenied
    if task.status in (HydraTask.Status.COMPLETED, HydraTask.Status.CANCELLED) and not (
        request.user.is_superuser
        or request.user.has_perm("hydra_tasks.reopen_hydratask")
    ):
        raise PermissionDenied
    allowed_statuses = ALLOWED_TRANSITIONS.get(task.status, set())
    form = TaskTransitionForm(
        request.POST or None,
        task=task,
        allowed_statuses=allowed_statuses,
    )
    if request.method == "POST" and form.is_valid():
        try:
            task = transition_task(
                actor=request.user,
                task_uuid=task.uuid,
                **form.cleaned_data,
            )
        except ValidationError as error:
            _add_service_errors(form, error)
        else:
            messages.success(request, _("Task status updated."))
            return redirect(task)
    return render(
        request,
        "hydra_tasks/task_form.html",
        {
            "form": form,
            "person": task.person,
            "task": task,
            "heading": _("Change status"),
        },
    )
