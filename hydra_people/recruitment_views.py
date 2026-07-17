from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from hydra_people.forms import (
    CandidatePersonLinkForm,
    CandidateStageTransitionForm,
    HydraCandidateApplicationForm,
)
from hydra_people.models import CandidateStageTransition, PersonApplication
from hydra_people.recruitment_selectors import (
    linked_candidate_for_user,
    linked_candidates_for_user,
    unlinked_candidate_for_user,
    unlinked_candidates_for_user,
)
from hydra_people.selectors import person_for_user
from hydra_people.recruitment_workflow import (
    transition_candidate,
    transition_rules_for_candidate,
)
from hydra_people.services import create_candidate_application, link_candidate


def _add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field_name, errors in error.error_dict.items():
            target = field_name if field_name in form.fields else None
            for field_error in errors:
                form.add_error(target, field_error)
    else:
        form.add_error(None, error)


@login_required
@permission_required(
    ("recruitment.view_candidate", "hydra_people.view_person"),
    raise_exception=True,
)
def recruitment_list(request):
    query = request.GET.get("q", "")
    candidates = linked_candidates_for_user(user=request.user, query=query)
    page_obj = Paginator(candidates, 25).get_page(request.GET.get("page"))
    can_backfill = request.user.has_perms(
        ("hydra_people.change_person", "hydra_people.link_candidate")
    )
    unlinked_queryset = (
        unlinked_candidates_for_user(user=request.user)
        if can_backfill
        else None
    )
    return render(
        request,
        "hydra_people/recruitment_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "unlinked_candidates": unlinked_queryset[:10] if unlinked_queryset else [],
            "unlinked_count": unlinked_queryset.count() if unlinked_queryset else 0,
        },
    )


@login_required
@permission_required(
    ("recruitment.view_candidate", "hydra_people.view_person"),
    raise_exception=True,
)
def recruitment_detail(request, candidate_id):
    candidate = linked_candidate_for_user(
        user=request.user,
        candidate_id=candidate_id,
    )
    can_transition = request.user.has_perm("recruitment.change_candidate") and (
        transition_rules_for_candidate(candidate=candidate).exists()
    )
    transitions = (
        CandidateStageTransition.objects.filter(candidate=candidate)
        .select_related("from_stage", "to_stage", "actor")[:50]
        if request.user.has_perm("hydra_people.view_candidatestagetransition")
        else []
    )
    return render(
        request,
        "hydra_people/recruitment_detail.html",
        {
            "candidate": candidate,
            "person": candidate.hydra_person_link.person,
            "can_transition": can_transition,
            "transitions": transitions,
        },
    )


@login_required
@permission_required(
    (
        "recruitment.view_candidate",
        "recruitment.change_candidate",
        "hydra_people.view_person",
    ),
    raise_exception=True,
)
def recruitment_transition(request, candidate_id):
    candidate = linked_candidate_for_user(
        user=request.user,
        candidate_id=candidate_id,
    )
    form = CandidateStageTransitionForm(
        request.POST or None,
        actor=request.user,
        candidate=candidate,
    )
    if request.method == "POST" and form.is_valid():
        try:
            transition_candidate(
                candidate=candidate,
                target_stage=form.cleaned_data["target_stage"],
                actor=request.user,
                reason=form.cleaned_data["reason"],
                schedule_date=form.cleaned_data["schedule_date"],
                joining_date=form.cleaned_data["joining_date"],
                override=form.cleaned_data.get("override", False),
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Recruitment stage updated."))
            return redirect("hydra-recruitment-detail", candidate_id=candidate.pk)
    return render(
        request,
        "hydra_people/recruitment_transition_form.html",
        {"candidate": candidate, "person": candidate.hydra_person_link.person, "form": form},
    )


@login_required
@permission_required(
    (
        "hydra_people.change_person",
        "hydra_people.link_candidate",
        "hydra_people.view_person",
        "recruitment.add_candidate",
        "recruitment.view_candidate",
        "recruitment.view_recruitment",
    ),
    raise_exception=True,
)
def recruitment_create(request, person_uuid):
    person = person_for_user(
        user=request.user,
        person_uuid=person_uuid,
        permission="change_person",
    )
    form = HydraCandidateApplicationForm(
        request.POST or None,
        request.FILES or None,
        actor=request.user,
        person=person,
    )
    if request.method == "POST" and form.is_valid():
        try:
            candidate, application_link = create_candidate_application(
                person=person,
                candidate=form.save(commit=False),
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Recruitment application created."))
            return redirect("hydra-recruitment-detail", candidate_id=candidate.pk)
    return render(
        request,
        "hydra_people/recruitment_form.html",
        {"form": form, "person": person},
    )


@login_required
@permission_required(
    (
        "recruitment.view_candidate",
        "hydra_people.view_person",
        "hydra_people.change_person",
        "hydra_people.link_candidate",
    ),
    raise_exception=True,
)
def recruitment_link_person(request, candidate_id):
    candidate = unlinked_candidate_for_user(
        user=request.user,
        candidate_id=candidate_id,
    )
    form = CandidatePersonLinkForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            link_candidate(
                person=form.cleaned_data["person"],
                candidate=candidate,
                actor=request.user,
                source=PersonApplication.LinkSource.BACKFILL,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Recruitment application linked."))
            return redirect("hydra-recruitment-detail", candidate_id=candidate.pk)
    return render(
        request,
        "hydra_people/recruitment_link_person.html",
        {"form": form, "candidate": candidate},
    )
