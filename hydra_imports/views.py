from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from hydra_imports.forms import CandidateImportUploadForm
from hydra_imports.selectors import (
    candidate_import_session_for_user,
    candidate_import_sessions_for_user,
)
from hydra_imports.services import (
    IMPORT_PERMISSIONS,
    PURGE_PERMISSIONS,
    apply_candidate_import,
    discard_candidate_import_data,
    preview_candidate_import,
)


def _detail_context(*, request, session):
    sensitive_data_available = session.sensitive_data_available
    rows = session.rows.select_related("created_person", "created_candidate")
    if not sensitive_data_available:
        rows = rows.only(
            "row_number",
            "outcome",
            "created_person",
            "created_candidate",
        )
    return {
        "session": session,
        "import_rows": rows,
        "sensitive_data_available": sensitive_data_available,
        "can_discard": request.user.has_perms(PURGE_PERMISSIONS)
        and (
            request.user.is_superuser
            or session.created_by_id == request.user.pk
        ),
    }


def _add_validation_error(form, error):
    if hasattr(error, "message_dict"):
        messages_list = [
            str(message)
            for field_messages in error.message_dict.values()
            for message in field_messages
        ]
    else:
        messages_list = [str(message) for message in error.messages]
    for message in messages_list:
        form.add_error("workbook", message)


@login_required
@permission_required(IMPORT_PERMISSIONS, raise_exception=True)
def candidate_import_upload(request):
    form = CandidateImportUploadForm(
        request.POST or None,
        request.FILES or None,
        actor=request.user,
    )
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            session = preview_candidate_import(
                workbook=form.cleaned_data["workbook"],
                recruitment=form.cleaned_data["recruitment"],
                job_position=form.cleaned_data["job_position"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_error(form, error)
            status = 400
        else:
            messages.success(request, _("Candidate import preview created."))
            return redirect(session)
    return render(
        request,
        "hydra_imports/candidate_import_upload.html",
        {
            "form": form,
            "recent_sessions": candidate_import_sessions_for_user(
                user=request.user
            )[:10],
        },
        status=status,
    )


@login_required
@permission_required(
    (
        "hydra_imports.view_candidateimportsession",
        "hydra_imports.import_candidate",
    ),
    raise_exception=True,
)
def candidate_import_detail(request, session_uuid):
    session = candidate_import_session_for_user(
        user=request.user,
        session_uuid=session_uuid,
    )
    return render(
        request,
        "hydra_imports/candidate_import_detail.html",
        _detail_context(request=request, session=session),
    )


@login_required
@require_POST
@permission_required(IMPORT_PERMISSIONS, raise_exception=True)
def candidate_import_apply(request, session_uuid):
    session = candidate_import_session_for_user(
        user=request.user,
        session_uuid=session_uuid,
    )
    try:
        session = apply_candidate_import(
            session_uuid=session.uuid,
            actor=request.user,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(
            request,
            _("Candidate import applied: %(count)s applications created.")
            % {"count": session.valid_count},
        )
    return redirect(session)


@login_required
@require_POST
@permission_required(PURGE_PERMISSIONS, raise_exception=True)
def candidate_import_discard(request, session_uuid):
    session = candidate_import_session_for_user(
        user=request.user,
        session_uuid=session_uuid,
    )
    session, created = discard_candidate_import_data(
        session_uuid=session.uuid,
        actor=request.user,
    )
    if created:
        messages.success(
            request,
            _("Candidate import source data was redacted; its audit record was retained."),
        )
    else:
        messages.info(request, _("Candidate import source data was already redacted."))
    return redirect(session)


@login_required
@permission_required("hydra_imports.import_candidate", raise_exception=True)
def candidate_import_template(request):
    template_path = (
        Path(__file__).resolve().parent
        / "static"
        / "hydra_imports"
        / "Hydra_Candidate_Import_Template.xlsx"
    )
    response = FileResponse(
        template_path.open("rb"),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        'attachment; filename="Hydra_Candidate_Import_Template.xlsx"'
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
