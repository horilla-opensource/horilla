from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _
from django.views.decorators.http import require_POST

from hydra_arrivals.forms import (
    ArrivalFilterForm,
    ArrivalPlanForm,
    ArrivalTransitionForm,
)
from hydra_arrivals.models import ArrivalPlan
from hydra_arrivals.selectors import (
    ARRIVAL_VIEW_PERMISSIONS,
    arrival_plan_for_user,
    arrival_plans_for_user,
)
from hydra_arrivals.services import (
    create_arrival_plan,
    transition_arrival_plan,
    update_arrival_plan,
)
from hydra_people.selectors import person_for_user
from hydra_links.public_urls import resolve_public_links
from hydra_links.selectors import public_links_for_location


def _add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error(None, error)


def _can_manage_plan(user, plan):
    return user == plan.coordinator or user.has_perm(
        "hydra_arrivals.assign_arrivalplan"
    )


def _detail_context(*, request, plan, transition_form=None):
    can_manage = _can_manage_plan(request.user, plan)
    can_transition = (
        plan.status == ArrivalPlan.Status.PLANNED
        and can_manage
        and request.user.has_perm("hydra_arrivals.transition_arrivalplan")
    )
    can_edit = (
        plan.status == ArrivalPlan.Status.PLANNED
        and can_manage
        and request.user.has_perm("hydra_arrivals.change_arrivalplan")
    )
    history = (
        plan.status_history.select_related("actor")
        if request.user.has_perm("hydra_arrivals.view_arrivalstatushistory")
        else plan.status_history.none()
    )
    return {
        "plan": plan,
        "transition_form": transition_form or ArrivalTransitionForm(),
        "can_transition": can_transition,
        "can_edit": can_edit,
        "status_history": history,
        "public_links": resolve_public_links(
            links=public_links_for_location(
                user=request.user,
                location=plan.destination_location,
                include_global=True,
            ),
            language_code=get_language() or "ru",
        ),
    }


@login_required
@permission_required(ARRIVAL_VIEW_PERMISSIONS, raise_exception=True)
def arrival_list(request):
    filter_form = ArrivalFilterForm(request.GET or None)
    filters = {"query": "", "status": "", "day": None}
    if filter_form.is_valid():
        filters = {
            "query": filter_form.cleaned_data["q"],
            "status": filter_form.cleaned_data["status"],
            "day": filter_form.cleaned_data["day"],
        }
    plans = arrival_plans_for_user(user=request.user, **filters)
    today_plans = arrival_plans_for_user(user=request.user).filter(
        planned_at__date=timezone.localdate()
    )
    return render(
        request,
        "hydra_arrivals/arrival_list.html",
        {
            "filter_form": filter_form,
            "page_obj": Paginator(plans, 25).get_page(request.GET.get("page")),
            "today_planned": today_plans.filter(
                status=ArrivalPlan.Status.PLANNED
            ).count(),
            "today_confirmed": today_plans.filter(
                status=ArrivalPlan.Status.CONFIRMED
            ).count(),
            "today_no_show": today_plans.filter(
                status=ArrivalPlan.Status.NO_SHOW
            ).count(),
        },
    )


@login_required
@permission_required(ARRIVAL_VIEW_PERMISSIONS, raise_exception=True)
def arrival_detail(request, plan_uuid):
    plan = arrival_plan_for_user(user=request.user, plan_uuid=plan_uuid)
    return render(
        request,
        "hydra_arrivals/arrival_detail.html",
        _detail_context(request=request, plan=plan),
    )


@login_required
@permission_required(
    ARRIVAL_VIEW_PERMISSIONS + ("hydra_arrivals.add_arrivalplan",),
    raise_exception=True,
)
def arrival_create(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    form = ArrivalPlanForm(
        request.POST or None,
        actor=request.user,
        person=person,
    )
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.person = person
        try:
            plan = create_arrival_plan(plan=plan, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Arrival planned."))
            return redirect(plan)
    return render(
        request,
        "hydra_arrivals/arrival_form.html",
        {"form": form, "person": person, "page_title": _("Plan arrival")},
    )


@login_required
@permission_required(
    ARRIVAL_VIEW_PERMISSIONS + ("hydra_arrivals.change_arrivalplan",),
    raise_exception=True,
)
def arrival_update(request, plan_uuid):
    plan = arrival_plan_for_user(user=request.user, plan_uuid=plan_uuid)
    if not _can_manage_plan(request.user, plan):
        raise PermissionDenied
    form = ArrivalPlanForm(
        request.POST or None,
        instance=plan,
        actor=request.user,
        person=plan.person,
    )
    if request.method == "POST" and form.is_valid():
        try:
            plan = update_arrival_plan(
                plan=form.save(commit=False),
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Arrival plan updated."))
            return redirect(plan)
    return render(
        request,
        "hydra_arrivals/arrival_form.html",
        {
            "form": form,
            "person": plan.person,
            "plan": plan,
            "page_title": _("Edit arrival plan"),
        },
    )


@login_required
@require_POST
@permission_required(
    ARRIVAL_VIEW_PERMISSIONS + ("hydra_arrivals.transition_arrivalplan",),
    raise_exception=True,
)
def arrival_transition(request, plan_uuid):
    plan = arrival_plan_for_user(user=request.user, plan_uuid=plan_uuid)
    form = ArrivalTransitionForm(request.POST)
    if form.is_valid():
        try:
            plan = transition_arrival_plan(
                plan_uuid=plan.uuid,
                target_status=form.cleaned_data["target_status"],
                actual_arrived_at=form.cleaned_data["actual_arrived_at"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Arrival outcome recorded."))
            return redirect(plan)
    return render(
        request,
        "hydra_arrivals/arrival_detail.html",
        _detail_context(request=request, plan=plan, transition_form=form),
        status=400,
    )
