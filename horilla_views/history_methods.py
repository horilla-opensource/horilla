"""
methods.py

This module is used to write methods related to the history
"""

from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render

from horilla.decorators import apply_decorators
from horilla_auth.models import HorillaUser


class Bot:
    def __init__(self) -> None:
        self.__str__()

    def __str__(self) -> str:
        return "Horilla Bot"

    def get_avatar(self):
        """
        Get avatar
        """
        return "https://ui-avatars.com/api/?name=Horilla+Bot&background=random"


def _check_and_delete(entry1, entry2, dry_run=False):
    delta = entry1.diff_against(entry2)
    if not delta.changed_fields:
        if not dry_run:
            entry1.delete()
        return 1
    return 0


def remove_duplicate_history(instance, history_related_name):
    """
    This method is used to remove duplicate entries
    """
    o_qs = getattr(instance, history_related_name).all()
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


class _SyntheticHistorySnapshot:
    """Stand-in when a live record has no simple-history rows yet."""

    def __init__(self, history_date, history_type="+"):
        self.history_date = history_date
        self.history_type = history_type
        self.history_title = None
        self.history_change_reason = None
        self.pk = None


def _actor_from_user(user):
    if not user:
        return Bot()
    try:
        return user.employee_get
    except Exception:
        return Bot()


def get_diff(instance, history_related_name):
    """
    This method is used to find the differences in the history
    """
    remove_duplicate_history(instance, history_related_name)
    history = getattr(instance, history_related_name).all()
    history_list = list(history)
    pairs = [
        [history_list[i], history_list[i + 1]] for i in range(len(history_list) - 1)
    ]
    delta_changes = []
    create_history = history.filter(history_type="+").first()
    for pair in pairs:
        delta = pair[0].diff_against(pair[1])
        diffs = []
        class_name = pair[0].instance.__class__
        for change in delta.changes:
            old = change.old
            new = change.new
            field = instance._meta.get_field(change.field)
            is_fk = False
            if (
                isinstance(field, models.fields.CharField)
                and field.choices
                and old
                and new
            ):
                choices = dict(field.choices)
                old = choices[old]
                new = choices[new]
            if isinstance(field, models.ForeignKey):
                is_fk = True
            diffs.append(
                {
                    "field": get_field_label(class_name, change.field),
                    "field_name": change.field,
                    "is_fk": is_fk,
                    "old": old,
                    "new": new,
                }
            )
        if not diffs:
            continue
        updated_by = (
            HorillaUser.objects.get(id=pair[0].history_user.id).employee_get
            if pair[0].history_user
            else Bot()
        )
        delta_changes.append(
            {
                "type": "Changes",
                "pair": pair,
                "changes": diffs,
                "updated_by": updated_by,
            }
        )
    if create_history:
        try:
            updated_by = create_history.history_user.employee_get
        except Exception:
            updated_by = Bot()
        delta_changes.append(
            {
                "type": f"{create_history.instance.__class__._meta.verbose_name.capitalize()} created",
                "pair": (create_history, create_history),
                "updated_by": updated_by,
            }
        )
    if not delta_changes and history_list:
        only = history_list[0]
        try:
            updated_by = only.history_user.employee_get if only.history_user else Bot()
        except Exception:
            updated_by = Bot()
        if only.history_type == "+":
            event_type = f"{instance._meta.verbose_name.capitalize()} created"
        elif only.history_type == "-":
            event_type = f"{instance._meta.verbose_name.capitalize()} deleted"
        else:
            event_type = f"{instance._meta.verbose_name.capitalize()} updated"
        delta_changes.append(
            {
                "type": event_type,
                "pair": (only, only),
                "updated_by": updated_by,
            }
        )
    # Records created before history was enabled (or via paths that skipped
    # simple-history) have no rows — still surface creation from HorillaModel.
    if not delta_changes:
        created_at = getattr(instance, "created_at", None)
        if created_at:
            snapshot = _SyntheticHistorySnapshot(created_at, "+")
            delta_changes.append(
                {
                    "type": f"{instance._meta.verbose_name.capitalize()} created",
                    "pair": (snapshot, snapshot),
                    "updated_by": _actor_from_user(
                        getattr(instance, "created_by", None)
                    ),
                }
            )
    if instance._meta.model_name == "employeeworkinformation":
        from horilla_audit.models import HistoryTrackingFields

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
        instance = model.objects.get(pk=obj_id)
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
