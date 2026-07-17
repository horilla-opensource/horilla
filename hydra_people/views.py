from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import get_language, gettext_lazy as _

from hydra_people.duplicate_services import (
    DISMISS_PERMISSIONS,
    MERGE_PERMISSIONS,
    REVIEW_PERMISSIONS,
    assert_merge_plan_access,
    build_merge_plan,
    dismiss_duplicate_suggestion,
    merge_duplicate_people,
    validate_selected_fields,
)
from hydra_people.forms import (
    CandidateLinkForm,
    DuplicateDismissForm,
    DuplicateMergeCommitForm,
    DuplicateMergeSelectionForm,
    EmployeeConversionForm,
    PersonForm,
)
from hydra_people.recruitment_selectors import linked_candidates_for_user
from hydra_people.selectors import (
    duplicate_suggestion_for_user,
    duplicate_suggestions_for_user,
    employee_conversion_for_user,
    person_for_user,
    person_merge_events_for_user,
    search_people,
)
from hydra_people.models import PersonApplication
from hydra_people.services import (
    CONVERSION_PERMISSIONS,
    convert_person_to_employee,
    link_candidate,
    save_person,
)
from hydra_people.timeline import person_timeline_for_user
from hydra_links.public_urls import resolve_public_links
from hydra_links.selectors import public_links_for_locations


MERGE_PAYLOAD_SALT = "hydra-people-merge-preview-v1"
MERGE_PAYLOAD_MAX_AGE_SECONDS = 30 * 60


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
    person = person_for_user(
        user=request.user,
        person_uuid=person_uuid,
        include_merged_alias=True,
    )
    if person.merged_into_id:
        messages.info(
            request,
            _("This source identifier was merged into the canonical Person."),
        )
        return redirect(person.merged_into)
    from hydra_coordination.models import PersonAssignment
    from hydra_coordination.selectors import teams_for_user
    from hydra_housing.selectors import (
        housing_assignment_events_for_user,
        housing_assignments_for_user,
    )

    visible_assignments = list(PersonAssignment.objects.filter(
        person=person,
        team__in=teams_for_user(user=request.user),
    ).select_related("team__section__location__company", "department"))
    visible_applications = linked_candidates_for_user(user=request.user).filter(
        hydra_person_link__person=person
    )
    conversion = employee_conversion_for_user(user=request.user, person=person)
    visible_housing_assignments = housing_assignments_for_user(
        user=request.user
    ).filter(person=person)
    visible_housing_events = housing_assignment_events_for_user(
        user=request.user
    ).filter(assignment__person=person)[:100]
    from hydra_tasks.models import HydraTask
    from hydra_tasks.selectors import tasks_for_user

    visible_tasks = tasks_for_user(user=request.user).filter(
        person=person,
        status__in=(HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS),
    )[:50]
    from hydra_onboarding.selectors import assignments_for_user

    visible_course_assignments = assignments_for_user(user=request.user).filter(
        person=person
    )[:50]
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
            "merge_events": person_merge_events_for_user(
                user=request.user,
                person=person,
            ),
            "visible_housing_assignments": visible_housing_assignments,
            "visible_housing_events": visible_housing_events,
            "visible_tasks": visible_tasks,
            "visible_course_assignments": visible_course_assignments,
            "visible_timeline": person_timeline_for_user(
                user=request.user,
                person=person,
            ),
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
@permission_required(REVIEW_PERMISSIONS, raise_exception=True)
def duplicate_suggestion_list(request):
    suggestions = duplicate_suggestions_for_user(user=request.user)
    paginator = Paginator(suggestions, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "hydra_people/duplicate_suggestion_list.html",
        {"page_obj": page_obj},
    )


def _duplicate_review_context(*, request, suggestion, plan, selection_form=None):
    can_merge = request.user.has_perms(MERGE_PERMISSIONS)
    if can_merge:
        try:
            assert_merge_plan_access(actor=request.user, plan=plan)
        except PermissionDenied:
            can_merge = False
    can_dismiss = request.user.has_perms(DISMISS_PERMISSIONS)
    if selection_form is None and can_merge:
        selection_form = DuplicateMergeSelectionForm(
            person_a=plan["person_a"],
            person_b=plan["person_b"],
            auto_id="id_merge_%s",
        )
    return {
        "suggestion": suggestion,
        "plan": plan,
        "selection_form": selection_form,
        "dismiss_form": (
            DuplicateDismissForm(auto_id="id_dismiss_%s") if can_dismiss else None
        ),
        "can_merge": can_merge,
        "can_dismiss": can_dismiss,
        "visible_reference_counts": plan["reference_counts"] if can_merge else (),
        "visible_conflicts": plan["conflicts"] if can_merge else (),
    }


@login_required
@permission_required(REVIEW_PERMISSIONS, raise_exception=True)
def duplicate_suggestion_detail(request, suggestion_uuid):
    suggestion = duplicate_suggestion_for_user(
        user=request.user,
        suggestion_uuid=suggestion_uuid,
    )
    plan = build_merge_plan(suggestion=suggestion)
    return render(
        request,
        "hydra_people/duplicate_suggestion_detail.html",
        _duplicate_review_context(
            request=request,
            suggestion=suggestion,
            plan=plan,
        ),
    )


@login_required
@permission_required(MERGE_PERMISSIONS, raise_exception=True)
@require_POST
def duplicate_merge_preview(request, suggestion_uuid):
    suggestion = duplicate_suggestion_for_user(
        user=request.user,
        suggestion_uuid=suggestion_uuid,
    )
    base_plan = build_merge_plan(suggestion=suggestion)
    form = DuplicateMergeSelectionForm(
        request.POST,
        person_a=base_plan["person_a"],
        person_b=base_plan["person_b"],
        auto_id="id_merge_%s",
    )
    if not form.is_valid():
        return render(
            request,
            "hydra_people/duplicate_suggestion_detail.html",
            _duplicate_review_context(
                request=request,
                suggestion=suggestion,
                plan=base_plan,
                selection_form=form,
            ),
            status=400,
        )
    plan = build_merge_plan(
        suggestion=suggestion,
        survivor_id=form.cleaned_data["canonical_person"],
    )
    assert_merge_plan_access(actor=request.user, plan=plan)
    try:
        validate_selected_fields(plan=plan, field_sources=form.field_sources)
    except ValidationError as error:
        for message in error.messages:
            form.add_error(None, message)
        return render(
            request,
            "hydra_people/duplicate_suggestion_detail.html",
            _duplicate_review_context(
                request=request,
                suggestion=suggestion,
                plan=plan,
                selection_form=form,
            ),
            status=400,
        )
    if plan["conflicts"]:
        form.add_error(
            None,
            _("Resolve every reported conflict before creating a merge preview."),
        )
        return render(
            request,
            "hydra_people/duplicate_suggestion_detail.html",
            _duplicate_review_context(
                request=request,
                suggestion=suggestion,
                plan=plan,
                selection_form=form,
            ),
            status=409,
        )
    payload = signing.dumps(
        {
            "suggestion_uuid": str(suggestion.uuid),
            "survivor_id": plan["survivor"].pk,
            "field_sources": form.field_sources,
            "reason": form.cleaned_data["reason"],
            "version_token": plan["version_token"],
        },
        salt=MERGE_PAYLOAD_SALT,
        compress=True,
    )
    commit_form = DuplicateMergeCommitForm(initial={"payload": payload})
    selected_values = []
    source_people = {"person_a": plan["person_a"], "person_b": plan["person_b"]}
    for comparison in plan["comparison_rows"]:
        source_key = form.field_sources[comparison["field"]]
        selected_values.append(
            {
                "label": comparison["label"],
                "source": source_people[source_key].hydra_id,
                "value": (
                    comparison["person_a"]
                    if source_key == "person_a"
                    else comparison["person_b"]
                ),
            }
        )
    return render(
        request,
        "hydra_people/duplicate_merge_preview.html",
        {
            "suggestion": suggestion,
            "plan": plan,
            "selected_values": selected_values,
            "reason": form.cleaned_data["reason"],
            "commit_form": commit_form,
        },
    )


@login_required
@permission_required(MERGE_PERMISSIONS, raise_exception=True)
@require_POST
def duplicate_merge_commit(request, suggestion_uuid):
    form = DuplicateMergeCommitForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Confirm the reviewed merge preview."))
        return redirect("hydra-duplicate-detail", suggestion_uuid=suggestion_uuid)
    try:
        payload = signing.loads(
            form.cleaned_data["payload"],
            salt=MERGE_PAYLOAD_SALT,
            max_age=MERGE_PAYLOAD_MAX_AGE_SECONDS,
        )
    except signing.BadSignature:
        messages.error(request, _("The merge preview expired or is invalid. Create it again."))
        return redirect("hydra-duplicate-detail", suggestion_uuid=suggestion_uuid)
    if payload.get("suggestion_uuid") != str(suggestion_uuid):
        messages.error(request, _("The merge preview does not match this suggestion."))
        return redirect("hydra-duplicate-detail", suggestion_uuid=suggestion_uuid)
    suggestion = duplicate_suggestion_for_user(
        user=request.user,
        suggestion_uuid=suggestion_uuid,
    )
    try:
        event = merge_duplicate_people(
            suggestion=suggestion,
            survivor_id=payload["survivor_id"],
            field_sources=payload["field_sources"],
            reason=payload["reason"],
            expected_version_token=payload["version_token"],
            actor=request.user,
        )
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        detail = "; ".join(getattr(error, "messages", (str(error),)))
        messages.error(request, detail)
        return redirect("hydra-duplicate-detail", suggestion_uuid=suggestion_uuid)
    messages.success(
        request,
        _("Duplicate merged into the canonical Person with immutable audit evidence."),
    )
    return redirect(event.survivor)


@login_required
@permission_required(DISMISS_PERMISSIONS, raise_exception=True)
@require_POST
def duplicate_suggestion_dismiss(request, suggestion_uuid):
    suggestion = duplicate_suggestion_for_user(
        user=request.user,
        suggestion_uuid=suggestion_uuid,
    )
    form = DuplicateDismissForm(request.POST, auto_id="id_dismiss_%s")
    if not form.is_valid():
        plan = build_merge_plan(suggestion=suggestion)
        context = _duplicate_review_context(
            request=request,
            suggestion=suggestion,
            plan=plan,
        )
        context["dismiss_form"] = form
        return render(
            request,
            "hydra_people/duplicate_suggestion_detail.html",
            context,
            status=400,
        )
    dismiss_duplicate_suggestion(
        suggestion=suggestion,
        actor=request.user,
        reason=form.cleaned_data["reason"],
    )
    messages.success(request, _("Duplicate suggestion dismissed with a recorded reason."))
    return redirect("hydra-duplicate-list")


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
