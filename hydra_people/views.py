from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import redirect, render
from django.utils.translation import get_language, gettext_lazy as _

from hydra_people.forms import CandidateLinkForm, EmployeeConversionForm, PersonForm
from hydra_people.recruitment_selectors import linked_candidates_for_user
from hydra_people.selectors import (
    employee_conversion_for_user,
    person_for_user,
    search_people,
)
from hydra_people.models import PersonApplication
from hydra_people.services import (
    CONVERSION_PERMISSIONS,
    convert_person_to_employee,
    link_candidate,
    save_person,
)
from hydra_links.public_urls import resolve_public_links
from hydra_links.selectors import public_links_for_locations


@login_required
@permission_required("hydra_people.view_person", raise_exception=True)
def person_list(request):
    query = request.GET.get("q", "")
    visible_links = PersonApplication.objects.filter(
        candidate__in=linked_candidates_for_user(user=request.user)
    ).select_related("candidate")
    people = search_people(user=request.user, query=query).prefetch_related(
        Prefetch(
            "applications",
            queryset=visible_links,
            to_attr="visible_application_links",
        )
    )
    paginator = Paginator(people, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "hydra_people/person_list.html",
        {"page_obj": page_obj, "query": query},
    )


@login_required
@permission_required("hydra_people.view_person", raise_exception=True)
def person_detail(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    from hydra_coordination.models import PersonAssignment
    from hydra_coordination.selectors import teams_for_user

    visible_assignments = list(PersonAssignment.objects.filter(
        person=person,
        team__in=teams_for_user(user=request.user),
    ).select_related("team__section__location__company", "department"))
    visible_applications = linked_candidates_for_user(user=request.user).filter(
        hydra_person_link__person=person
    )
    conversion = employee_conversion_for_user(user=request.user, person=person)
    current_location_ids = {
        assignment.team.section.location_id
        for assignment in visible_assignments
        if assignment.is_current()
    }
    return render(
        request,
        "hydra_people/person_detail.html",
        {
            "person": person,
            "visible_assignments": visible_assignments,
            "visible_applications": visible_applications,
            "conversion": conversion,
            "public_links": resolve_public_links(
                links=public_links_for_locations(
                    user=request.user,
                    location_ids=current_location_ids,
                    include_global=True,
                ),
                language_code=get_language() or "ru",
            ),
        },
    )


@login_required
@permission_required("hydra_people.add_person", raise_exception=True)
def person_create(request):
    form = PersonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            person = save_person(person=form.save(commit=False), actor=request.user)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, _("Hydra person created."))
            return redirect(person)
    return render(
        request,
        "hydra_people/person_form.html",
        {"form": form, "page_title": _("Create person")},
    )


@login_required
@permission_required("hydra_people.change_person", raise_exception=True)
def person_update(request, person_uuid):
    person = person_for_user(
        user=request.user,
        person_uuid=person_uuid,
        permission="change_person",
    )
    form = PersonForm(request.POST or None, instance=person)
    if request.method == "POST" and form.is_valid():
        try:
            person = save_person(person=form.save(commit=False), actor=request.user)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, _("Hydra person updated."))
            return redirect(person)
    return render(
        request,
        "hydra_people/person_form.html",
        {"form": form, "person": person, "page_title": _("Edit person")},
    )


@login_required
@permission_required(
    (
        "hydra_people.view_person",
        "hydra_people.change_person",
        "hydra_people.link_candidate",
        "recruitment.view_candidate",
    ),
    raise_exception=True,
)
def candidate_link(request, person_uuid):
    person = person_for_user(
        user=request.user,
        person_uuid=person_uuid,
        permission="change_person",
    )
    form = CandidateLinkForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            link_candidate(
                person=person,
                candidate=form.cleaned_data["candidate"],
                actor=request.user,
            )
        except ValidationError as error:
            form.add_error("candidate", error)
        else:
            messages.success(request, _("Recruitment application linked."))
            return redirect(person)
    return render(
        request,
        "hydra_people/candidate_link_form.html",
        {"form": form, "person": person},
    )


@login_required
@permission_required(CONVERSION_PERMISSIONS, raise_exception=True)
def employee_conversion(request, person_uuid):
    person = person_for_user(
        user=request.user,
        person_uuid=person_uuid,
        permission="change_person",
    )
    if person.employee_id:
        messages.info(request, _("This Person is already linked to an employee."))
        return redirect(person)

    initial = {}
    if request.GET.get("candidate"):
        initial["candidate"] = request.GET["candidate"]
    form = EmployeeConversionForm(
        request.POST or None,
        actor=request.user,
        person=person,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        try:
            employee, conversion, created = convert_person_to_employee(
                person=person,
                candidate=form.cleaned_data["candidate"],
                work_email=form.cleaned_data["work_email"],
                phone=form.cleaned_data["phone"],
                joining_date=form.cleaned_data["joining_date"],
                actor=request.user,
            )
        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for field_name, field_errors in error.message_dict.items():
                    target = field_name if field_name in form.fields else None
                    for field_error in field_errors:
                        form.add_error(target, field_error)
            else:
                form.add_error(None, error)
        else:
            if created:
                messages.success(
                    request,
                    _("Horilla employee created and linked with an audit record."),
                )
            else:
                messages.success(
                    request,
                    _("Existing Horilla employee linked with an audit record."),
                )
            return redirect(conversion.person)
    return render(
        request,
        "hydra_people/employee_conversion_form.html",
        {"form": form, "person": person},
    )
