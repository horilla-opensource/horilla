"""
methods.py

This module is used to write methods related to the history
"""

from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render
from django.utils.translation import gettext as _

from horilla.decorators import apply_decorators
from horilla.http.response import HorillaRedirect
from horilla_auth.models import HorillaUser


class Bot:
    def __init__(self) -> None:
        self.__str__()

    def __str__(self) -> str:
        return "Horilla Bot"

    def get_avatar(self):
        return "https://ui-avatars.com/api/?name=Horilla+Bot&background=random"


def _check_and_delete(entry1, entry2, dry_run=False):
    delta = entry1.diff_against(entry2)
    if not delta.changed_fields:
        if not dry_run:
            entry1.delete()
        return 1
    return 0


def remove_duplicate_history(instance):
    """
    This method is used to remove duplicate entries
    """
    o_qs = instance.history_set.all()
    entries_deleted = 0
    # ordering is ('-history_date', '-history_id') so this is ok
    f1 = o_qs.first()
    if not f1:
        return
    for f2 in o_qs[1:]:
        entries_deleted += _check_and_delete(
            f1,
            f2,
        )
        f1 = f2


def get_field_label(model_class, field_name):
    # Check if the field exists in the model class
    if hasattr(model_class, field_name):
        field = model_class._meta.get_field(field_name)
        return field.verbose_name.capitalize()
    # Return None if the field does not exist
    return None


def filter_history(histories, track_fields):
    filtered_histories = []
    for history in histories:
        changes = history.get("changes") or []
        if not changes:
            continue
        filtered_changes = [
            change for change in changes if change.get("field_name", "") in track_fields
        ]
        if filtered_changes:
            history["changes"] = filtered_changes
            filtered_histories.append(history)
    return filtered_histories


# Fields that should never appear in the employee History tab diffs.
EXCLUDED_HISTORY_FIELDS = {
    "id",
    "pk",
    "history_id",
    "history_date",
    "history_change_reason",
    "history_type",
    "history_user",
    "history_user_id",
    "history_relation",
    "history_title",
    "history_description",
    "history_highlight",
    "created_at",
    "updated_at",
    "created_by",
    "created_by_id",
    "modified_by",
    "modified_by_id",
    "is_active",
    "additional_info",
    "is_from_onboarding",
    "is_directly_converted",
    "experience",
    "employee_id",
}


def _history_display_value(history_record, field_name, raw_value, field):
    """Human-readable value for a historical field change."""
    if isinstance(field, models.ForeignKey):
        try:
            related = getattr(history_record, field_name, None)
            if related is not None:
                return str(related)
        except Exception:
            pass
        if raw_value in (None, ""):
            return "—"
        return f"{raw_value} (deleted)"
    if raw_value is None or raw_value == "":
        return "—"
    return str(raw_value)


def get_diff(instance):
    """
    This method is used to find the differences in the history
    """
    remove_duplicate_history(instance)
    history = instance.history_set.all()
    if hasattr(instance.history_set.model, "history_tags"):
        history = history.prefetch_related("history_tags")
    history_list = list(history)
    # Pair consecutive versions: [newer, older]
    pairs = [
        [history_list[i], history_list[i + 1]] for i in range(len(history_list) - 1)
    ]
    delta_changes = []
    for pair in pairs:
        newer, older = pair[0], pair[1]
        delta = newer.diff_against(older)
        diffs = []
        class_name = newer.instance.__class__
        for change in delta.changes:
            if change.field in EXCLUDED_HISTORY_FIELDS:
                continue
            try:
                field = instance._meta.get_field(change.field)
            except Exception:
                continue
            old = change.old
            new = change.new
            if (
                isinstance(field, models.fields.CharField)
                and field.choices
                and old
                and new
            ):
                choices = dict(field.choices)
                old = choices.get(old, old)
                new = choices.get(new, new)
            is_fk = isinstance(field, models.ForeignKey)
            diffs.append(
                {
                    "field": get_field_label(class_name, change.field),
                    "field_label": get_field_label(class_name, change.field),
                    "field_name": change.field,
                    "is_fk": is_fk,
                    "old": old,
                    "new": new,
                    "old_value": _history_display_value(
                        older, change.field, old, field
                    ),
                    "new_value": _history_display_value(
                        newer, change.field, new, field
                    ),
                }
            )
        if not diffs:
            # Nothing user-facing changed — skip (no placeholder entry).
            continue
        updated_by = (
            HorillaUser.objects.get(id=newer.history_user.id).employee_get
            if newer.history_user
            else Bot()
        )
        delta_changes.append(
            {
                "type": "Changes",
                "pair": pair,
                "changes": diffs,
                "updated_by": updated_by,
                "change_reason": getattr(newer, "history_title", None)
                or getattr(newer, "history_change_reason", None),
                "history_tags": (
                    list(newer.history_tags.all())
                    if hasattr(newer, "history_tags")
                    else []
                ),
            }
        )
    if instance._meta.model_name == "employeeworkinformation":
        from .models import HistoryTrackingFields

        history_tracking_instance = HistoryTrackingFields.for_company(
            getattr(instance, "company_id", None)
        )
        if (
            history_tracking_instance is None
            or not history_tracking_instance.work_info_track
        ):
            return []
        if history_tracking_instance.tracking_fields:
            track_fields = history_tracking_instance.tracked_field_names()
            if track_fields:
                delta_changes = filter_history(delta_changes, track_fields)
    return delta_changes


def history_tracking(request, obj_id, **kwargs):
    model = kwargs.get("model")
    decorator_strings = kwargs.get("decorators", [])

    @apply_decorators(decorator_strings)
    def _history_tracking(request, obj_id, model):
        instance = model.objects.filter(pk=obj_id).first()
        if not instance:
            return HorillaRedirect(request, message=_("Object not found"))
        histories = instance.horilla_history.all()
        page_number = request.GET.get("page", 1)
        paginator = Paginator(histories, 4)
        page_obj = paginator.get_page(page_number)
        context = {
            "histories": page_obj,
            "model_name": model,
        }
        return render(
            request,
            "horilla_audit/history_tracking.html",
            context,
        )

    return _history_tracking(request, obj_id, model)
