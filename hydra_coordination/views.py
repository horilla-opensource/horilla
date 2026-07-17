from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from hydra_coordination.forms import (
    EmployeeTeamAssignmentForm,
    LocationForm,
    OrganizationAccessEndForm,
    PersonAssignmentForm,
    ScopeGrantForm,
    SectionForm,
    TeamForm,
)
from hydra_coordination.brigadier_selectors import (
    BRIGADIER_PERMISSIONS,
    brigadier_roster_for_team,
    brigadier_teams_for_user,
)
from hydra_coordination.coordinator_selectors import (
    COORDINATOR_PERMISSIONS,
    coordinator_locations_for_user,
    coordinator_snapshot_for_location,
)
from hydra_coordination.models import PersonAssignment, ScopeGrant
from hydra_coordination.selectors import (
    locations_for_user,
    scope_grants_for_management,
    sections_for_user,
    teams_for_user,
)
from hydra_coordination.services import (
    assign_employee_to_team,
    assign_person,
    end_person_assignment,
    end_scope_grant,
    save_location,
    save_scope_grant,
    save_section,
    save_team,
)
from hydra_people.selectors import people_for_user, person_for_user
from hydra_links.public_urls import resolve_public_links
from hydra_links.selectors import public_links_for_location


@login_required
@permission_required(COORDINATOR_PERMISSIONS, raise_exception=True)
def coordinator_panel(request):
    today = timezone.localdate()
    requested_date = request.GET.get("date", "").strip()
    if requested_date:
        try:
            selected_date = date.fromisoformat(requested_date)
        except ValueError:
            return HttpResponseBadRequest("Invalid panel date.")
    else:
        selected_date = today
    if selected_date > today:
        return HttpResponseBadRequest("Panel date cannot be in the future.")

    locations = list(coordinator_locations_for_user(user=request.user))
    selected_location = locations[0] if locations else None
    requested_location = request.GET.get("location", "").strip()
    if requested_location:
        try:
            requested_location_id = int(requested_location)
        except ValueError as error:
            raise Http404 from error
        selected_location = next(
            (
                location
                for location in locations
                if location.pk == requested_location_id
            ),
            None,
        )
        if selected_location is None:
            raise Http404

    snapshot = (
        coordinator_snapshot_for_location(
            user=request.user,
            location=selected_location,
            day=selected_date,
        )
        if selected_location is not None
        else None
    )
    return render(
        request,
        "hydra_coordination/coordinator_panel.html",
        {
            "locations": locations,
            "selected_location": selected_location,
            "selected_date": selected_date,
            "today": today,
            "snapshot": snapshot,
            "public_links": resolve_public_links(
                links=(
                    public_links_for_location(
                        user=request.user,
                        location=selected_location,
                    )
                    if selected_location is not None
                    else []
                ),
                language_code=get_language() or "ru",
            ),
        },
    )


@login_required
@permission_required(BRIGADIER_PERMISSIONS, raise_exception=True)
def brigadier_panel(request):
    today = timezone.localdate()
    requested_date = request.GET.get("date", "").strip()
    if requested_date:
        try:
            selected_date = date.fromisoformat(requested_date)
        except ValueError:
            return HttpResponseBadRequest("Invalid panel date.")
    else:
        selected_date = today
    if selected_date > today:
        return HttpResponseBadRequest("Panel date cannot be in the future.")

    teams = list(brigadier_teams_for_user(user=request.user))
    selected_team = teams[0] if teams else None
    requested_team = request.GET.get("team", "").strip()
    if requested_team:
        try:
            requested_team_id = int(requested_team)
        except ValueError as error:
            raise Http404 from error
        selected_team = next(
            (team for team in teams if team.pk == requested_team_id),
            None,
        )
        if selected_team is None:
            raise Http404

    query = request.GET.get("q", "").strip()[:100]
    rows = (
        brigadier_roster_for_team(
            user=request.user,
            team=selected_team,
            day=selected_date,
            query=query,
        )
        if selected_team is not None
        else []
    )
    summary = {
        "roster": len(rows),
        "no_attendance": sum(row.no_attendance for row in rows),
        "approved_leave": sum(bool(row.approved_leave) for row in rows),
        "at_work": sum(row.at_work for row in rows),
        "needs_review": sum(row.has_exception for row in rows),
    }
    page_obj = Paginator(rows, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "hydra_coordination/brigadier_panel.html",
        {
            "teams": teams,
            "selected_team": selected_team,
            "selected_date": selected_date,
            "today": today,
            "query": query,
            "summary": summary,
            "page_obj": page_obj,
            "public_links": resolve_public_links(
                links=(
                    public_links_for_location(
                        user=request.user,
                        location=selected_team.section.location,
                    )
                    if selected_team is not None
                    else []
                ),
                language_code=get_language() or "ru",
            ),
        },
    )


@login_required
@permission_required("hydra_coordination.view_location", raise_exception=True)
def organization(request):
    locations = list(locations_for_user(user=request.user))
    sections = (
        list(sections_for_user(user=request.user))
        if request.user.has_perm("hydra_coordination.view_section")
        else []
    )
    teams = (
        list(teams_for_user(user=request.user))
        if request.user.has_perm("hydra_coordination.view_team")
        else []
    )
    sections_by_location = {location.pk: [] for location in locations}
    teams_by_section = {section.pk: [] for section in sections}
    for team in teams:
        teams_by_section.setdefault(team.section_id, []).append(team)
    for section in sections:
        section.visible_teams = teams_by_section.get(section.pk, [])
        sections_by_location.setdefault(section.location_id, []).append(section)
    for location in locations:
        location.visible_sections = sections_by_location.get(location.pk, [])

    grants = None
    if request.user.has_perm("hydra_coordination.view_scopegrant"):
        paginator = Paginator(scope_grants_for_management(user=request.user), 50)
        grants = paginator.get_page(request.GET.get("grant_page"))
    return render(
        request,
        "hydra_coordination/organization.html",
        {"locations": locations, "scope_grants": grants},
    )


def _create(
    request, *, form_class, service, service_keyword, page_title, success_message
):
    form = form_class(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            service(**{service_keyword: form.save(commit=False)}, actor=request.user)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, success_message)
            return redirect("hydra-organization")
    return render(
        request,
        "hydra_coordination/model_form.html",
        {"form": form, "page_title": page_title},
    )


@login_required
@permission_required("hydra_coordination.add_location", raise_exception=True)
def location_create(request):
    return _create(
        request,
        form_class=LocationForm,
        service=save_location,
        service_keyword="location",
        page_title=_("Create location"),
        success_message=_("Location created."),
    )


@login_required
@permission_required("hydra_coordination.add_section", raise_exception=True)
def section_create(request):
    return _create(
        request,
        form_class=SectionForm,
        service=save_section,
        service_keyword="section",
        page_title=_("Create section / stage"),
        success_message=_("Section created."),
    )


@login_required
@permission_required("hydra_coordination.add_team", raise_exception=True)
def team_create(request):
    return _create(
        request,
        form_class=TeamForm,
        service=save_team,
        service_keyword="team",
        page_title=_("Create team"),
        success_message=_("Team created."),
    )


@login_required
@permission_required("hydra_coordination.add_scopegrant", raise_exception=True)
def scope_grant_create(request):
    return _create(
        request,
        form_class=ScopeGrantForm,
        service=save_scope_grant,
        service_keyword="grant",
        page_title=_("Grant organization scope"),
        success_message=_("Organization scope granted."),
    )


@login_required
@permission_required(
    (
        "hydra_coordination.view_scopegrant",
        "hydra_coordination.change_scopegrant",
    ),
    raise_exception=True,
)
def scope_grant_end(request, grant_id):
    grant = get_object_or_404(
        scope_grants_for_management(user=request.user), pk=grant_id
    )
    form = OrganizationAccessEndForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            end_scope_grant(
                grant_id=grant.pk,
                action=form.cleaned_data["action"],
                last_day=form.cleaned_data["last_day"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            if hasattr(error, "error_dict"):
                for field, errors in error.error_dict.items():
                    for item in errors:
                        form.add_error(field if field in form.fields else None, item)
            else:
                form.add_error(None, error)
        else:
            messages.success(request, _("Organization scope access updated."))
            return redirect("hydra-organization")
    return render(
        request,
        "hydra_coordination/access_end_form.html",
        {
            "form": form,
            "page_title": _("End organization scope"),
            "subject_label": grant.user,
            "target_label": grant.target,
            "valid_from": grant.valid_from,
            "valid_until": grant.valid_until,
            "cancel_url": reverse("hydra-organization"),
        },
    )


@login_required
@permission_required(
    (
        "hydra_people.view_person",
        "hydra_coordination.change_personassignment",
        "hydra_coordination.assign_person",
    ),
    raise_exception=True,
)
def person_assignment_end(request, assignment_id):
    assignment = get_object_or_404(
        PersonAssignment.objects.select_related(
            "person", "team__section__location", "department"
        ).filter(person__in=people_for_user(user=request.user)),
        pk=assignment_id,
    )
    form = OrganizationAccessEndForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            end_person_assignment(
                assignment_id=assignment.pk,
                action=form.cleaned_data["action"],
                last_day=form.cleaned_data["last_day"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            if hasattr(error, "error_dict"):
                for field, errors in error.error_dict.items():
                    for item in errors:
                        form.add_error(field if field in form.fields else None, item)
            else:
                form.add_error(None, error)
        else:
            messages.success(request, _("Organization assignment updated."))
            return redirect(assignment.person)
    return render(
        request,
        "hydra_coordination/access_end_form.html",
        {
            "form": form,
            "page_title": _("End organization assignment"),
            "subject_label": assignment.person,
            "target_label": assignment.team,
            "valid_from": assignment.valid_from,
            "valid_until": assignment.valid_until,
            "cancel_url": assignment.person.get_absolute_url(),
        },
    )


@login_required
@permission_required(
    (
        "hydra_people.view_person",
        "hydra_coordination.add_personassignment",
        "hydra_coordination.assign_person",
    ),
    raise_exception=True,
)
def person_assign(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    if person.employee_id:
        if not request.user.has_perms(
            (
                "employee.view_employee",
                "employee.change_employeeworkinformation",
            )
        ):
            raise PermissionDenied
        form = EmployeeTeamAssignmentForm(request.POST or None, actor=request.user)
        if request.method == "POST" and form.is_valid():
            try:
                assign_employee_to_team(
                    person=person,
                    team=form.cleaned_data["team"],
                    valid_from=form.cleaned_data["valid_from"],
                    actor=request.user,
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, _("Employee assigned to the team."))
                return redirect(person)
        return render(
            request,
            "hydra_coordination/person_assignment_form.html",
            {"form": form, "person": person, "employee_assignment": True},
        )

    assignment = PersonAssignment(person=person)
    form = PersonAssignmentForm(
        request.POST or None,
        instance=assignment,
        actor=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            assign_person(assignment=form.save(commit=False), actor=request.user)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, _("Person assigned to the organization."))
            return redirect(person)
    return render(
        request,
        "hydra_coordination/person_assignment_form.html",
        {"form": form, "person": person},
    )
