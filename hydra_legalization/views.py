from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _

from hydra_legalization.forms import (
    LegalizationCaseForm,
    LegalizationDocumentForm,
    LegalizationTransitionForm,
)
from hydra_legalization.models import LegalizationCase
from hydra_legalization.selectors import (
    case_document_links_for_user,
    legalization_case_for_user,
    legalization_cases_for_user,
)
from hydra_legalization.services import (
    attach_private_document,
    create_legalization_case,
    update_legalization_case,
    transition_legalization_case,
)
from hydra_people.recruitment_selectors import linked_candidates_for_user
from hydra_people.selectors import person_for_user


def _add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error(None, error)


@login_required
@permission_required("hydra_legalization.view_legalizationcase", raise_exception=True)
def legalization_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    cases = legalization_cases_for_user(user=request.user, query=query, status=status)
    return render(
        request,
        "hydra_legalization/case_list.html",
        {
            "page_obj": Paginator(cases, 25).get_page(request.GET.get("page")),
            "query": query,
            "selected_status": status,
            "status_choices": LegalizationCase.Status.choices,
        },
    )


def _case_detail_context(*, request, case, transition_form=None, document_form=None):
    can_transition = request.user.has_perm(
        "hydra_legalization.transition_legalizationcase"
    )
    can_link = request.user.has_perms(
        (
            "hydra_legalization.link_privatedocument",
            "hydra_documents.view_privatedocument",
        )
    )
    return {
        "case": case,
        "person": case.person,
        "document_links": case_document_links_for_user(
            user=request.user, case=case
        ),
        "transition_form": transition_form
        or LegalizationTransitionForm(case=case),
        "document_form": document_form
        or LegalizationDocumentForm(actor=request.user, case=case),
        "can_transition": can_transition,
        "can_link": can_link,
        "candidate_applications": linked_candidates_for_user(user=request.user).filter(
            hydra_person_link__person=case.person
        ),
    }


@login_required
@permission_required("hydra_legalization.view_legalizationcase", raise_exception=True)
def legalization_detail(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(request=request, case=case),
    )


@login_required
@permission_required(
    (
        "hydra_legalization.add_legalizationcase",
        "hydra_legalization.view_legalizationcase",
        "hydra_people.view_person",
    ),
    raise_exception=True,
)
def legalization_create(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    form = LegalizationCaseForm(
        request.POST or None, actor=request.user, person=person
    )
    if request.method == "POST" and form.is_valid():
        case = form.save(commit=False)
        case.person = person
        try:
            case = create_legalization_case(case=case, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Legalization case created."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_form.html",
        {"form": form, "person": person, "page_title": _("Start legalization")},
    )


@login_required
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.change_legalizationcase",
    ),
    raise_exception=True,
)
def legalization_update(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    form = LegalizationCaseForm(
        request.POST or None,
        instance=case,
        actor=request.user,
        person=case.person,
    )
    if request.method == "POST" and form.is_valid():
        try:
            case = update_legalization_case(
                case=form.save(commit=False), actor=request.user
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Legalization case updated."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_form.html",
        {"form": form, "person": case.person, "case": case, "page_title": _("Edit legalization case")},
    )


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.transition_legalizationcase",
    ),
    raise_exception=True,
)
def legalization_transition(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    form = LegalizationTransitionForm(request.POST, case=case)
    if form.is_valid():
        try:
            transition_legalization_case(
                case_uuid=case.uuid,
                target_status=form.cleaned_data["target_status"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Legalization status updated."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(request=request, case=case, transition_form=form),
        status=400,
    )


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.link_privatedocument",
        "hydra_documents.view_privatedocument",
    ),
    raise_exception=True,
)
def legalization_attach_document(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    form = LegalizationDocumentForm(request.POST, actor=request.user, case=case)
    if form.is_valid():
        try:
            attach_private_document(
                case_uuid=case.uuid,
                document_uuid=form.cleaned_data["document"].uuid,
                role=form.cleaned_data["role"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Private document linked."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(request=request, case=case, document_form=form),
        status=400,
    )
