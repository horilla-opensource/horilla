from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _

from hydra_legalization.forms import (
    LegalizationAuthorityForm,
    LegalizationAuthorityEventForm,
    LegalizationCaseForm,
    LegalizationDelegationForm,
    LegalizationDelegationRevokeForm,
    LegalizationDocumentForm,
    LegalizationReassignmentForm,
    LegalizationRequirementForm,
    LegalizationRenewalLinkForm,
    LegalizationRenewalStartForm,
    LegalizationTransitionForm,
    LegalizationProcedureForm,
)
from hydra_legalization.models import (
    LegalizationAuthority,
    LegalizationCase,
    LegalizationProcedureRequirement,
    LegalizationProcedureType,
)
from hydra_legalization.selectors import (
    authority_events_for_user,
    case_document_links_for_user,
    legalization_delegations_for_user,
    legalization_case_for_user,
    legalization_cases_for_user,
    legalization_authorities_for_user,
    legalization_procedures_for_user,
    legalization_requirements_for_user,
    legalization_work_events_for_user,
    legalization_workload_for_user,
    legalization_workload_owner_choices,
    renewal_links_for_case,
    user_can_operate_legalization_case,
)
from hydra_legalization.services import (
    attach_private_document,
    case_can_start_renewal,
    create_legalization_case,
    create_legalization_renewal,
    link_existing_legalization_renewal,
    record_legalization_authority_event,
    save_legalization_authority,
    save_legalization_procedure,
    save_legalization_requirement,
    update_legalization_case,
    transition_legalization_case,
)
from hydra_legalization.workload import (
    create_legalization_delegation,
    reassign_legalization_case,
    revoke_legalization_delegation,
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


@login_required
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationworkload",
    ),
    raise_exception=True,
)
def legalization_workload(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    owner = request.GET.get("owner", "")
    attention = request.GET.get("attention", "")
    cases = legalization_workload_for_user(
        user=request.user,
        query=query,
        status=status,
        owner=owner,
        attention=attention,
    )
    owner_choices = [
        (
            user_id,
            " ".join(part for part in (first_name, last_name) if part) or username,
        )
        for user_id, first_name, last_name, username in legalization_workload_owner_choices(
            user=request.user
        )
    ]
    return render(
        request,
        "hydra_legalization/workload.html",
        {
            "page_obj": Paginator(cases, 25).get_page(request.GET.get("page")),
            "query": query,
            "selected_status": status,
            "selected_owner": owner,
            "selected_attention": attention,
            "status_choices": LegalizationCase.Status.choices,
            "owner_choices": owner_choices,
        },
    )


def _case_detail_context(
    *,
    request,
    case,
    transition_form=None,
    document_form=None,
    authority_event_form=None,
    renewal_link_form=None,
    delegation_form=None,
    reassignment_form=None,
    revocation_form=None,
):
    can_operate = user_can_operate_legalization_case(user=request.user, case=case)
    can_transition = can_operate and request.user.has_perm(
        "hydra_legalization.transition_legalizationcase"
    )
    can_link = can_operate and request.user.has_perms(
        (
            "hydra_legalization.link_privatedocument",
            "hydra_documents.view_privatedocument",
        )
    )
    can_record_authority_event = request.user.has_perms(
        (
            "hydra_legalization.view_legalizationauthorityevent",
            "hydra_legalization.record_legalizationauthorityevent",
            "hydra_legalization.view_legalizationauthority",
            "hydra_documents.view_privatedocument",
        )
    ) and can_operate
    renewal_predecessor_link, renewal_successor_link = renewal_links_for_case(
        user=request.user,
        case=case,
    )
    renewal_link_form = renewal_link_form or LegalizationRenewalLinkForm(
        actor=request.user,
        successor=case,
    )
    can_link_renewal = request.user.has_perms(
        (
            "hydra_legalization.view_legalizationrenewallink",
            "hydra_legalization.create_legalizationrenewallink",
        )
    ) and can_operate
    can_manage_delegation = request.user.has_perms(
        (
            "hydra_legalization.view_legalizationcasedelegation",
            "hydra_legalization.manage_legalizationdelegation",
        )
    ) and (request.user.is_superuser or case.responsible_id == request.user.pk)
    can_reassign = request.user.has_perms(
        (
            "hydra_legalization.change_legalizationcase",
            "hydra_legalization.assign_legalizationcase",
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
        "authority_events": authority_events_for_user(user=request.user, case=case),
        "authority_event_form": authority_event_form
        or LegalizationAuthorityEventForm(actor=request.user, case=case),
        "can_transition": can_transition,
        "can_operate": can_operate,
        "can_edit": can_operate
        and request.user.has_perm("hydra_legalization.change_legalizationcase"),
        "can_link": can_link,
        "can_record_authority_event": can_record_authority_event,
        "renewal_predecessor_link": renewal_predecessor_link,
        "renewal_successor_link": renewal_successor_link,
        "renewal_link_form": renewal_link_form,
        "can_start_renewal": case_can_start_renewal(case=case, actor=request.user),
        "can_link_renewal": can_link_renewal,
        "delegations": legalization_delegations_for_user(
            user=request.user,
            case=case,
        ),
        "work_events": legalization_work_events_for_user(
            user=request.user,
            case=case,
        ),
        "delegation_form": delegation_form
        or LegalizationDelegationForm(case=case),
        "reassignment_form": reassignment_form
        or LegalizationReassignmentForm(case=case),
        "revocation_form": revocation_form
        or LegalizationDelegationRevokeForm(),
        "can_manage_delegation": can_manage_delegation,
        "can_reassign": can_reassign,
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
        "hydra_legalization.view_legalizationproceduretype",
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
        "hydra_legalization.view_legalizationproceduretype",
    ),
    raise_exception=True,
)
def legalization_update(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    if not user_can_operate_legalization_case(user=request.user, case=case):
        raise PermissionDenied
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
        {
            "form": form,
            "person": case.person,
            "case": case,
            "page_title": _("Edit legalization case"),
        },
    )


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.change_legalizationcase",
        "hydra_legalization.assign_legalizationcase",
        "hydra_people.view_person",
    ),
    raise_exception=True,
)
def legalization_reassign(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    form = LegalizationReassignmentForm(request.POST, case=case)
    if form.is_valid():
        try:
            case, changed = reassign_legalization_case(
                case_uuid=case.uuid,
                new_responsible=form.cleaned_data["new_responsible"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if changed:
                messages.success(request, _("Responsibility transferred and audited."))
            else:
                messages.info(request, _("Responsibility was already assigned to that user."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(request=request, case=case, reassignment_form=form),
        status=400,
    )


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationcasedelegation",
        "hydra_legalization.manage_legalizationdelegation",
        "hydra_people.view_person",
    ),
    raise_exception=True,
)
def legalization_delegate(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    if not request.user.is_superuser and case.responsible_id != request.user.pk:
        raise PermissionDenied
    form = LegalizationDelegationForm(request.POST, case=case)
    if form.is_valid():
        try:
            _delegation, created = create_legalization_delegation(
                case_uuid=case.uuid,
                deputy=form.cleaned_data["deputy"],
                valid_from=form.cleaned_data["valid_from"],
                valid_until=form.cleaned_data["valid_until"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if created:
                messages.success(request, _("Deputy assignment created and audited."))
            else:
                messages.info(request, _("This deputy assignment already exists."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(request=request, case=case, delegation_form=form),
        status=400,
    )


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationcasedelegation",
        "hydra_legalization.manage_legalizationdelegation",
    ),
    raise_exception=True,
)
def legalization_revoke_delegation(request, case_uuid, delegation_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    if not request.user.is_superuser and case.responsible_id != request.user.pk:
        raise PermissionDenied
    get_object_or_404(
        legalization_delegations_for_user(user=request.user, case=case),
        uuid=delegation_uuid,
    )
    form = LegalizationDelegationRevokeForm(request.POST)
    if form.is_valid():
        try:
            _delegation, changed = revoke_legalization_delegation(
                delegation_uuid=delegation_uuid,
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if changed:
                messages.success(request, _("Deputy assignment revoked and audited."))
            else:
                messages.info(request, _("This deputy assignment was already revoked."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(request=request, case=case, revocation_form=form),
        status=400,
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


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationauthorityevent",
        "hydra_legalization.record_legalizationauthorityevent",
        "hydra_legalization.view_legalizationauthority",
        "hydra_documents.view_privatedocument",
    ),
    raise_exception=True,
)
def legalization_record_authority_event(request, case_uuid):
    case = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    form = LegalizationAuthorityEventForm(
        request.POST,
        actor=request.user,
        case=case,
    )
    if form.is_valid():
        evidence = form.cleaned_data["evidence_document"]
        try:
            _event, created = record_legalization_authority_event(
                case_uuid=case.uuid,
                event_type=form.cleaned_data["event_type"],
                occurred_on=form.cleaned_data["occurred_on"],
                authority_uuid=form.cleaned_data["authority_config"].uuid,
                channel=form.cleaned_data["channel"],
                reference_number=form.cleaned_data["reference_number"],
                response_deadline=form.cleaned_data["response_deadline"],
                valid_from=form.cleaned_data["valid_from"],
                valid_until=form.cleaned_data["valid_until"],
                evidence_document_uuid=evidence.uuid,
                details=form.cleaned_data["details"],
                idempotency_key=form.cleaned_data["idempotency_key"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if created:
                messages.success(request, _("Authority event recorded."))
            else:
                messages.info(request, _("This authority event was already recorded."))
            return redirect(case)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(
            request=request,
            case=case,
            authority_event_form=form,
        ),
        status=400,
    )


@login_required
@permission_required(
    (
        "hydra_legalization.view_legalizationproceduretype",
        "hydra_legalization.view_legalizationauthority",
        "hydra_legalization.view_legalizationprocedurerequirement",
    ),
    raise_exception=True,
)
def legalization_configuration(request):
    return render(
        request,
        "hydra_legalization/configuration.html",
        {
            "procedures": legalization_procedures_for_user(
                user=request.user, include_inactive=True
            ),
            "authorities": legalization_authorities_for_user(
                user=request.user, include_inactive=True
            ),
            "requirements": legalization_requirements_for_user(
                user=request.user, include_inactive=True
            ),
            "can_add_procedure": request.user.has_perm(
                "hydra_legalization.add_legalizationproceduretype"
            ),
            "can_change_procedure": request.user.has_perm(
                "hydra_legalization.change_legalizationproceduretype"
            ),
            "can_add_authority": request.user.has_perm(
                "hydra_legalization.add_legalizationauthority"
            ),
            "can_change_authority": request.user.has_perm(
                "hydra_legalization.change_legalizationauthority"
            ),
            "can_add_requirement": request.user.has_perm(
                "hydra_legalization.add_legalizationprocedurerequirement"
            ),
            "can_change_requirement": request.user.has_perm(
                "hydra_legalization.change_legalizationprocedurerequirement"
            ),
        },
    )


@login_required
def legalization_procedure_form(request, procedure_uuid=None):
    permission = (
        "change_legalizationproceduretype"
        if procedure_uuid
        else "add_legalizationproceduretype"
    )
    if not request.user.has_perms(
        (
            "hydra_legalization.view_legalizationproceduretype",
            "hydra_legalization.view_legalizationauthority",
            f"hydra_legalization.{permission}",
        )
    ):
        raise PermissionDenied
    procedure = None
    if procedure_uuid:
        procedure = legalization_procedures_for_user(
            user=request.user, include_inactive=True
        ).filter(uuid=procedure_uuid).first()
        if procedure is None or (procedure.company_id is None and not request.user.is_superuser):
            raise Http404
    form = LegalizationProcedureForm(
        request.POST or None,
        instance=procedure,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            save_legalization_procedure(
                actor=request.user,
                procedure=procedure or LegalizationProcedureType(),
                cleaned_data=form.cleaned_data,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Legalization procedure saved and audited."))
            return redirect("hydra-legalization-configuration")
    return render(
        request,
        "hydra_legalization/procedure_form.html",
        {"form": form, "procedure": procedure},
    )


@login_required
def legalization_authority_form(request, authority_uuid=None):
    permission = (
        "change_legalizationauthority"
        if authority_uuid
        else "add_legalizationauthority"
    )
    if not request.user.has_perms(
        (
            "hydra_legalization.view_legalizationauthority",
            f"hydra_legalization.{permission}",
        )
    ):
        raise PermissionDenied
    authority = None
    if authority_uuid:
        authority = legalization_authorities_for_user(
            user=request.user, include_inactive=True
        ).filter(uuid=authority_uuid).first()
        if authority is None or (authority.company_id is None and not request.user.is_superuser):
            raise Http404
    form = LegalizationAuthorityForm(
        request.POST or None,
        instance=authority,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            save_legalization_authority(
                actor=request.user,
                authority=authority or LegalizationAuthority(),
                cleaned_data=form.cleaned_data,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Legalization authority saved and audited."))
            return redirect("hydra-legalization-configuration")
    return render(
        request,
        "hydra_legalization/authority_form.html",
        {"form": form, "authority": authority},
    )


@login_required
def legalization_requirement_form(
    request, procedure_uuid=None, requirement_uuid=None
):
    permission = (
        "change_legalizationprocedurerequirement"
        if requirement_uuid
        else "add_legalizationprocedurerequirement"
    )
    if not request.user.has_perms(
        (
            "hydra_legalization.view_legalizationprocedurerequirement",
            "hydra_legalization.view_legalizationproceduretype",
            "hydra_documents.view_privatedocumenttype",
            f"hydra_legalization.{permission}",
        )
    ):
        raise PermissionDenied
    procedure = None
    if procedure_uuid:
        procedure = legalization_procedures_for_user(
            user=request.user, include_inactive=True
        ).filter(uuid=procedure_uuid).first()
        if procedure is None:
            raise Http404
    requirement = None
    if requirement_uuid:
        requirement = legalization_requirements_for_user(
            user=request.user, include_inactive=True
        ).filter(uuid=requirement_uuid).first()
        if requirement is None or (
            requirement.procedure.company_id is None and not request.user.is_superuser
        ):
            raise Http404
        procedure = requirement.procedure
    form = LegalizationRequirementForm(
        request.POST or None,
        instance=requirement,
        user=request.user,
        procedure=procedure,
    )
    if request.method == "POST" and form.is_valid():
        try:
            save_legalization_requirement(
                actor=request.user,
                requirement=requirement or LegalizationProcedureRequirement(),
                cleaned_data=form.cleaned_data,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Procedure requirement saved and audited."))
            return redirect("hydra-legalization-configuration")
    return render(
        request,
        "hydra_legalization/requirement_form.html",
        {"form": form, "requirement": requirement, "procedure": procedure},
    )


@login_required
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.add_legalizationcase",
        "hydra_legalization.view_legalizationrenewallink",
        "hydra_legalization.create_legalizationrenewallink",
        "hydra_people.view_person",
    ),
    raise_exception=True,
)
def legalization_start_renewal(request, case_uuid):
    predecessor = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    if request.method != "POST" and not case_can_start_renewal(
        case=predecessor,
        actor=request.user,
    ):
        raise PermissionDenied
    form = LegalizationRenewalStartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            successor, created = create_legalization_renewal(
                predecessor_uuid=predecessor.uuid,
                deadline=form.cleaned_data["deadline"],
                notes=form.cleaned_data["notes"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if created:
                messages.success(request, _("Legalization renewal created."))
            else:
                messages.info(request, _("This renewal already exists."))
            return redirect(successor)
    return render(
        request,
        "hydra_legalization/renewal_form.html",
        {
            "form": form,
            "predecessor": predecessor,
            "person": predecessor.person,
        },
        status=400 if request.method == "POST" else 200,
    )


@login_required
@require_POST
@permission_required(
    (
        "hydra_legalization.view_legalizationcase",
        "hydra_legalization.view_legalizationrenewallink",
        "hydra_legalization.create_legalizationrenewallink",
    ),
    raise_exception=True,
)
def legalization_link_renewal(request, case_uuid):
    successor = legalization_case_for_user(user=request.user, case_uuid=case_uuid)
    form = LegalizationRenewalLinkForm(
        request.POST,
        actor=request.user,
        successor=successor,
    )
    if form.is_valid():
        try:
            _link, created = link_existing_legalization_renewal(
                predecessor_uuid=form.cleaned_data["predecessor"].uuid,
                successor_uuid=successor.uuid,
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            if created:
                messages.success(request, _("Historical renewal link created."))
            else:
                messages.info(request, _("This renewal link already exists."))
            return redirect(successor)
    return render(
        request,
        "hydra_legalization/case_detail.html",
        _case_detail_context(
            request=request,
            case=successor,
            renewal_link_form=form,
        ),
        status=400,
    )
