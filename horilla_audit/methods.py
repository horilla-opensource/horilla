"""
methods.py

This module is used to write methods related to the history
"""
from django.db import models
from django.contrib.auth.models import User


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


def get_diff(instance):
    """
    This method is used to find the differences in the history
    """
    remove_duplicate_history(instance)
    history = instance.history_set.all()
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
            if isinstance(field, models.ForeignKey):
                is_fk = True
                # old = getattr(pair[0], change.field)
                # new = getattr(pair[1], change.field)
            diffs.append(
                {
                    "field": get_field_label(class_name, change.field),
                    "field_name": change.field,
                    "is_fk": is_fk,
                    "old": old,
                    "new": new,
                }
            )
        updated_by = (
            User.objects.get(id=pair[0].history_user.id).employee_get
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
        updated_by = create_history.history_user.employee_get
        delta_changes.append(
            {
                "type": f"{create_history.instance.__class__._meta.verbose_name.capitalize()} created",
                "pair": (create_history, create_history),
                "updated_by": updated_by,
            }
        )
    return delta_changes
