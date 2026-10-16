"""The import wizard: upload, match columns and check, then run and summarise."""

import io
import json
import logging
import re

import pandas as pd
from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.methods import get_session_company
from horilla.decorators import login_required

from .datasets import DATASETS, default_dataset, get_dataset
from .datasets.base import Context
from .models import ImportJob
from .parsing import (
    UploadError,
    apply_mapping,
    read_upload,
    sample_values,
    suggest_mapping,
)

logger = logging.getLogger(__name__)

STEPS = [
    (1, _("Upload"), _("Choose data and a file")),
    (2, _("Match Columns"), _("Map your columns to ours")),
    (3, _("Confirm & Import"), _("Review, fix and import")),
]
SHOWN_ERRORS = 200
SHOWN_ROWS = 200


def _allowed(request, dataset):
    return (
        bool(dataset)
        and dataset.available
        and (request.user.is_superuser or request.user.has_perm(dataset.permission))
    )


def _can_update(request, dataset):
    """Updating existing records takes the change permissions, not only the add one."""
    return request.user.is_superuser or all(
        request.user.has_perm(p) for p in getattr(dataset, "update_permissions", [])
    )


def _job_for(request, job_id):
    job = get_object_or_404(ImportJob, pk=job_id)
    if not (request.user.is_superuser or job.created_by_id == request.user.pk):
        raise Http404
    dataset = get_dataset(job.dataset)
    if not _allowed(request, dataset):
        raise Http404
    if job.mode in ("update", "both") and not _can_update(request, dataset):
        raise Http404
    return job, dataset


def _context(request):
    return Context(user=request.user, company=get_session_company(request))


def _frame(job):
    if not job.file:
        raise UploadError(
            _("The uploaded file is no longer available. Upload it again.")
        )
    job.file.open("rb")
    try:
        return read_upload(job.file)
    finally:
        job.file.close()


def _page(request, template, step, **extra):
    return render(request, template, {"steps": STEPS, "step": step, **extra})


# ---------------------------------------------------------------- step 1
@login_required
def index(request):
    dataset = get_dataset(request.GET.get("dataset", "")) or default_dataset()
    if not dataset.available:
        dataset = default_dataset()
    if not _allowed(request, dataset) and "dataset" not in request.GET:
        # Someone who may import only some data lands on the first they can.
        dataset = next((d for d in DATASETS.values() if _allowed(request, d)), dataset)
    if not _allowed(request, dataset):
        messages.error(request, _("You don't have access to import this data."))
        return redirect("/")
    return _page(
        request,
        "master_import/step_upload.html",
        1,
        datasets=[d for d in DATASETS.values() if _allowed(request, d)],
        dataset=dataset,
        fields=dataset.fields,
        can_update=_can_update(request, dataset),
        company=get_session_company(request),
    )


@login_required
def upload(request):
    dataset = get_dataset(request.POST.get("dataset", ""))
    if request.method != "POST" or not _allowed(request, dataset):
        return redirect("master-import")
    if request.POST.get("mode") in ("update", "both") and not _can_update(
        request, dataset
    ):
        messages.error(
            request, _("You don't have permission to update existing records.")
        )
        return redirect(f"{reverse('master-import')}?dataset={dataset.key}")
    file = request.FILES.get("file")
    if not file:
        messages.error(request, _("Choose a file to upload."))
        return redirect(f"{reverse('master-import')}?dataset={dataset.key}")
    try:
        frame = read_upload(file)
    except UploadError as exc:
        messages.error(request, str(exc))
        return redirect(f"{reverse('master-import')}?dataset={dataset.key}")

    file.seek(0)
    job = ImportJob(
        dataset=dataset.key,
        original_name=file.name,
        columns=list(frame.columns),
        row_count=len(frame),
        created_by=request.user,
        company_id=get_session_company(request),
        mapping=suggest_mapping(list(frame.columns), dataset.fields),
        mode=(
            request.POST.get("mode")
            if dataset.supports_update
            and request.POST.get("mode") in ("update", "both")
            else "create"
        ),
        match_keys=list(dataset.default_match_keys) if dataset.supports_update else [],
    )
    job.file.save(file.name, file, save=False)
    job.save()
    return redirect("master-import-map", job_id=job.pk)


@login_required
def template_download(request, dataset):
    spec = get_dataset(dataset)
    if not _allowed(request, spec):
        raise Http404
    frame = pd.DataFrame(
        [{f.key: f.sample for f in spec.fields}], columns=[f.key for f in spec.fields]
    )
    return _xlsx_response(frame, f"{spec.key}_template.xlsx")


def _xlsx_bytes(frame):
    """A sheet people can work in: a frozen yellow header, borders, readable widths."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    edge = Side(style="thin", color="7F7F7F")
    border = Border(left=edge, right=edge, top=edge, bottom=edge)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
        sheet = writer.sheets["Sheet1"]
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", start_color="FFFF00", end_color="FFFF00")
            cell.alignment = Alignment(vertical="center")
        # Bordered down past the sample too, so there is a grid to fill in.
        blanks = max(30 - len(frame), 0)
        for row in sheet.iter_rows(
            min_row=1, max_row=len(frame) + 1 + blanks, max_col=len(frame.columns)
        ):
            for cell in row:
                cell.border = border
        for index, column in enumerate(frame.columns, start=1):
            longest = max(
                [len(str(column))] + [len(str(v)) for v in frame[column].head(50)]
            )
            sheet.column_dimensions[get_column_letter(index)].width = min(
                max(longest + 4, 14), 50
            )
        sheet.freeze_panes = "A2"
    return buffer.getvalue()


def _xlsx_response(frame, filename):
    response = HttpResponse(
        _xlsx_bytes(frame),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------- step 2
@login_required
def map_columns(request, job_id):
    job, dataset = _job_for(request, job_id)
    if job.status == ImportJob.DONE:
        return redirect("master-import-done", job_id=job.pk)
    try:
        frame = _frame(job)
    except UploadError as exc:
        messages.error(request, str(exc))
        return redirect("master-import")

    updating = job.mode == "update"
    matching = job.mode in ("update", "both")

    def required_keys():
        if updating:
            return set(job.match_keys)
        return {f.key for f in dataset.fields if f.required}

    def unmatched():
        return [
            f.label
            for f in dataset.fields
            if f.key in required_keys()
            and not job.mapping.get(f.key)
            and not (
                f.key == "First Name" and job.mapping.get("Full Name") and not updating
            )
        ]

    if request.method == "POST":
        job.mapping = {
            f.key: request.POST.get(f"map__{f.key}", "") for f in dataset.fields
        }
        job.mapping = {k: v for k, v in job.mapping.items() if v in frame.columns}
        if matching:
            chosen = [
                k for k in request.POST.getlist("match") if k in dataset.match_choices
            ]
            chosen = [
                k
                for k in dataset.match_choices
                if k in chosen or k in dataset.locked_match_keys
            ]
            job.match_keys = chosen or list(dataset.default_match_keys)
        if not unmatched():
            job.status = ImportJob.MAPPED
            job.save(update_fields=["mapping", "status", "match_keys"])
            return redirect("master-import-review", job_id=job.pk)

    missing = unmatched()
    return _page(
        request,
        "master_import/step_map.html",
        2,
        job=job,
        dataset=dataset,
        rows=[
            {
                "field": f,
                "selected": job.mapping.get(f.key, ""),
                "required": f.key in required_keys(),
            }
            for f in dataset.fields
        ],
        updating=updating,
        matching=matching,
        match_choices=dataset.match_choices,
        locked_keys=dataset.locked_match_keys,
        match_keys=job.match_keys,
        columns=job.columns,
        samples={c: sample_values(frame, c) for c in job.columns},
        missing=missing,
    )


def _rows(job, dataset, frame):
    """The mapped rows, with whatever was corrected on the review page laid over them."""
    rows = apply_mapping(frame, job.mapping, dataset.fields)
    allowed = {f.key for f in dataset.fields}
    for row in rows:
        for field, value in (job.edits or {}).get(str(row["__row"]), {}).items():
            if field in allowed:
                row[field] = (str(value).strip() or None) if value is not None else None
    return rows


def _split(job, dataset, frame, ctx, progress=None):
    """All rows, the ones skipped by choice, and the check of the rest."""
    rows = _rows(job, dataset, frame)
    skipped_numbers = {int(n) for n in (job.skipped or [])}
    skipped = [r for r in rows if r["__row"] in skipped_numbers]
    live = [r for r in rows if r["__row"] not in skipped_numbers]
    if progress:
        progress(5)
    return (
        rows,
        skipped,
        dataset.check(
            live, ctx, progress=progress, mode=job.mode, match_keys=job.match_keys
        ),
    )


def _review(job, dataset, frame, ctx, progress=None):
    rows, skipped, checked = _split(job, dataset, frame, ctx, progress)
    # Every field that has data, in the dataset's order: what was matched, and the
    # names when they came from a single Full Name column.
    mapped = {k for k, v in job.mapping.items() if v}
    if "Full Name" in mapped:
        mapped |= {"First Name", "Last Name"}
    columns = [
        f.key for f in dataset.fields if f.key in mapped and f.key != "Full Name"
    ] or dataset.preview_columns
    # An error may be in a column the preview does not show; those are added to the error table.
    flagged = {f for e in checked.errors[:SHOWN_ROWS] for f in e["by_field"]}
    error_columns = columns + [
        f.key for f in dataset.fields if f.key in flagged and f.key not in columns
    ]

    specs = {f.key: f for f in dataset.fields}
    suggestions = dataset.suggestions()

    def choices_for(spec):
        """Fixed choices as they are; for the open ones, what already exists plus
        every distinct value this file brings, so nothing in the sheet is lost."""
        if spec.kind == "choice":
            return [{"value": c, "label": c.capitalize()} for c in spec.choices]
        names = set(suggestions.get(spec.suggest, []))
        names |= {str(r[spec.key]) for r in rows if r.get(spec.key)}
        return [{"value": n, "label": n} for n in sorted(names, key=str.lower)]

    choice_cache = {}

    def widget(field, value):
        """How one cell is edited: its kind, and the list it offers. A value the
        kind cannot show (a date that is not a date) falls back to plain text."""
        spec = specs[field]
        kind = spec.kind
        if kind == "date" and value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            kind = "text"
        if kind == "number" and value:
            try:
                float(value)
            except ValueError:
                kind = "text"
        if kind == "suggest":
            kind = "choice"
        options = []
        if kind == "choice":
            if field not in choice_cache:
                choice_cache[field] = choices_for(spec)
            options = list(choice_cache[field])
            # A value that is not on the list (one just typed over, say) is kept.
            if value and value not in {o["value"] for o in options}:
                options.append({"value": value, "label": value})
        return {"kind": kind, "options": options}

    def cell(data, field, bad=""):
        value = "" if data.get(field) is None else str(data.get(field))
        return {"field": field, "value": value, "bad": bad, **widget(field, value)}

    def cells(data):
        return [cell(data, c) for c in columns]

    return {
        "total": len(rows),
        "valid": len(checked.valid),
        "error_count": len(checked.errors),
        "errors": checked.errors[:SHOWN_ERRORS],
        "columns": columns,
        "mode": job.mode,
        "unchanged": len(checked.unchanged),
        "creating": sum(1 for r in checked.valid if r.get("__op") == "create"),
        "updating": sum(1 for r in checked.valid if r.get("__op") == "update"),
        "skipped": len(skipped),
        "skipped_rows": [
            {
                "row": r.get("__row"),
                "number": int(r.get("__row")) - 1,
                "cells": cells(r),
            }
            for r in skipped[:SHOWN_ROWS]
        ],
        "downloads": {
            kind: reverse("master-import-download", args=[job.pk, kind])
            for kind in ("valid", "errors", "skipped")
        },
        "valid_rows": [
            {
                "row": r.get("__row"),
                "number": int(r.get("__row")) - 1,
                "cells": cells(r),
                "changes": r.get("__changes", []),
            }
            for r in checked.valid[:SHOWN_ROWS]
        ],
        "error_columns": error_columns,
        "error_rows": [
            {
                "row": e["row"],
                "number": e["row"] - 1,
                "messages": e["messages"],
                "cells": [
                    cell(e["data"], c, e["by_field"].get(c, "")) for c in error_columns
                ],
            }
            for e in checked.errors[:SHOWN_ROWS]
        ],
        "shown_limit": SHOWN_ROWS,
        "will_create": [
            {
                "label": (
                    str(dataset.created_models[key]._meta.verbose_name_plural).title()
                    if key in dataset.created_models
                    else key.replace("_", " ").title()
                ),
                "names": names,
            }
            for key, names in checked.will_create.items()
            if names
        ],
    }


@login_required
def review(request, job_id):
    """Step 3: check every row, fix what needs fixing, confirm the import."""
    job, dataset = _job_for(request, job_id)
    if job.status == ImportJob.DONE:
        return redirect("master-import-done", job_id=job.pk)
    if not job.mapping:
        return redirect("master-import-map", job_id=job.pk)
    return _page(request, "master_import/step_review.html", 3, job=job, dataset=dataset)


@login_required
def save_edits(request, job_id):
    """Keep corrections made on the review page; the next check applies them."""
    job, dataset = _job_for(request, job_id)
    if request.method != "POST" or job.status == ImportJob.DONE:
        raise Http404
    try:
        payload = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"ok": False}, status=400)
    sent = payload.get("edits", {})
    allowed = {f.key for f in dataset.fields}
    edits = dict(job.edits or {})
    for row, fields in sent.items():
        if not str(row).isdigit() or not isinstance(fields, dict):
            continue
        valid = {k: v for k, v in fields.items() if k in allowed}
        if valid:
            edits.setdefault(str(row), {}).update(valid)
    job.edits = edits

    skipped = {int(n) for n in (job.skipped or [])}
    for row, on in (payload.get("skip") or {}).items():
        if str(row).isdigit():
            (skipped.add if on else skipped.discard)(int(row))
    job.skipped = sorted(skipped)
    job.save(update_fields=["edits", "skipped"])
    return JsonResponse({"ok": True})


@login_required
def check(request, job_id):
    """Check the rows for the modal: saves the mapping, reports progress, answers with the review."""
    job, dataset = _job_for(request, job_id)
    if request.method != "POST" or job.status == ImportJob.DONE:
        raise Http404
    try:
        frame = _frame(job)
    except UploadError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    job.check_progress = 0
    job.save(update_fields=["check_progress"])

    last = {"value": -1}

    def report(percent):
        # A write per change of a few points, not per row.
        if percent - last["value"] >= 3 or percent >= 100:
            last["value"] = percent
            ImportJob.objects.filter(pk=job.pk).update(check_progress=min(percent, 100))

    review = _review(job, dataset, frame, _context(request), progress=report)
    ImportJob.objects.filter(pk=job.pk).update(check_progress=100)
    return JsonResponse(
        {
            "ok": True,
            "valid": review["valid"],
            "mode": job.mode,
            "error_count": review["error_count"],
            "html": render_to_string(
                "master_import/_review.html", {"review": review}, request=request
            ),
        }
    )


@login_required
def check_progress(request, job_id):
    job, _dataset = _job_for(request, job_id)
    return JsonResponse({"percent": job.check_progress})


# ---------------------------------------------------------------- step 3
@login_required
def run(request, job_id):
    job, dataset = _job_for(request, job_id)
    if request.method != "POST" or job.status == ImportJob.DONE:
        return redirect(
            (
                "master-import-done"
                if job.status == ImportJob.DONE
                else "master-import-review"
            ),
            job_id=job.pk,
        )
    ctx = _context(request)
    ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    done_url = reverse("master-import-done", args=[job.pk])

    def finish():
        return (
            JsonResponse({"ok": True, "url": done_url}) if ajax else redirect(done_url)
        )

    ImportJob.objects.filter(pk=job.pk).update(check_progress=0)

    def report(percent):
        ImportJob.objects.filter(pk=job.pk).update(check_progress=min(percent, 100))

    try:
        frame = _frame(job)
        rows, skipped, checked = _split(job, dataset, frame, ctx)
        counts = (
            dataset.commit(checked.valid, ctx, mode=job.mode, progress=report)
            if checked.valid
            else {}
        )
    except Exception as exc:  # noqa: BLE001 - recorded on the job, shown to the user
        logger.exception("Master import %s failed", job.pk)
        job.status = ImportJob.FAILED
        job.summary = {"failure": f"{type(exc).__name__}: {exc}"}
        job.finished_at = timezone.now()
        job.save()
        messages.error(request, _("The import failed and nothing was saved."))
        return finish()

    job.summary = {
        "total": len(rows),
        "mode": job.mode,
        "imported": len(checked.valid),
        "unchanged": len(checked.unchanged),
        "skipped": len(skipped),
        "error_count": len(checked.errors),
        "counts": counts,
        "errors": [
            {k: e[k] for k in ("row", "name", "badge", "messages")}
            for e in checked.errors[:SHOWN_ERRORS]
        ],
    }
    if checked.errors:
        job.error_file.save(
            f"{dataset.key}_errors_{job.pk}.xlsx",
            ContentFile(_error_workbook(checked.errors, dataset)),
            save=False,
        )
    job.status = ImportJob.DONE
    job.finished_at = timezone.now()
    _forget(job, dataset)
    job.save()
    return finish()


MASK = "********"


def _secret_keys(dataset):
    """The fields that hold passwords: never written back out in the clear."""
    return {f.key for f in dataset.fields if f.kind == "password"}


def _masked(row, key, secret):
    value = row.get(key)
    return MASK if key in secret and value else value


def _error_workbook(errors, dataset):
    keys = [f.key for f in dataset.fields]
    secret = _secret_keys(dataset)
    frame = pd.DataFrame(
        [
            {
                "Row": e["row"],
                **{k: _masked(e["data"], k, secret) for k in keys},
                "Errors": "; ".join(e["messages"]),
            }
            for e in errors
        ]
    )
    return _xlsx_bytes(frame)


def _forget(job, dataset):
    """Once an import is done its file, corrections and any passwords are not kept."""
    job.edits = {}
    if job.file:
        job.file.delete(save=False)


@login_required
def done(request, job_id):
    job, dataset = _job_for(request, job_id)
    if job.status in (ImportJob.UPLOADED, ImportJob.MAPPED):
        return redirect("master-import-map", job_id=job.pk)
    return _page(
        request,
        "master_import/step_done.html",
        4,
        job=job,
        dataset=dataset,
        summary=job.summary,
    )


@login_required
def download_records(request, job_id, kind):
    """The valid, error or skipped rows as a sheet, with corrections applied."""
    job, dataset = _job_for(request, job_id)
    if kind not in ("valid", "errors", "skipped") or not job.mapping or not job.file:
        raise Http404
    rows, skipped, checked = _split(job, dataset, _frame(job), _context(request))
    keys = [f.key for f in dataset.fields]
    if kind == "errors":
        frame = (
            pd.read_excel(io.BytesIO(_error_workbook(checked.errors, dataset)))
            if checked.errors
            else pd.DataFrame(columns=["Row", *keys, "Errors"])
        )
    else:
        chosen = checked.valid if kind == "valid" else skipped
        frame = pd.DataFrame(
            [
                {
                    "Row": r.get("__row"),
                    **{k: _masked(r, k, _secret_keys(dataset)) for k in keys},
                }
                for r in chosen
            ],
            columns=["Row", *keys],
        )
    mapped = [
        c
        for c in frame.columns
        if c in ("Row", "Errors")
        or c in job.mapping
        and job.mapping[c]
        or (c == "First Name" or c == "Last Name")
        and job.mapping.get("Full Name")
    ]
    return _xlsx_response(
        frame[mapped] if len(frame.columns) else frame,
        f"{dataset.key}_{kind}_records.xlsx",
    )


@login_required
def error_file(request, job_id):
    job, _dataset = _job_for(request, job_id)
    if not job.error_file:
        raise Http404
    return FileResponse(
        job.error_file.open("rb"),
        as_attachment=True,
        filename=job.error_file.name.rsplit("/", 1)[-1],
    )


@login_required
def history(request):
    jobs = ImportJob.objects.all()
    if not request.user.is_superuser:
        jobs = jobs.filter(created_by=request.user)
    jobs = list(jobs.select_related("created_by")[:100])
    for job in jobs:
        spec = get_dataset(job.dataset)
        job.dataset_label = spec.label if spec else job.dataset
    return _page(request, "master_import/history.html", 0, jobs=jobs, datasets=DATASETS)
