"""
file_widgets.py

Patches Django's ClearableFileInput so every FileField upload widget across
Horilla shows a clean display name instead of horilla.models.upload_path's
full storage path (app_label/model_name/field_name/slug-uuid.ext).
"""

import os
import re

from django import forms

_UPLOAD_SUFFIX_RE = re.compile(r"-[0-9a-f]{8}(\.[^.]*)?$", re.IGNORECASE)


def pretty_file_name(value):
    """
    Strip the directory path and the upload_path uuid suffix from a
    FieldFile's stored name, returning a human-readable display name.
    """
    name = os.path.basename(str(value))
    return _UPLOAD_SUFFIX_RE.sub(lambda match: match.group(1) or "", name)


def patch_clearable_file_input():
    """
    Patch ClearableFileInput.get_context to expose a clean display name and
    point its template at the Horilla override.
    """
    original_get_context = forms.ClearableFileInput.get_context

    def get_context(self, name, value, attrs):
        context = original_get_context(self, name, value, attrs)
        if context["widget"].get("is_initial"):
            context["widget"]["value_name"] = pretty_file_name(value)
        return context

    forms.ClearableFileInput.get_context = get_context
    forms.ClearableFileInput.template_name = (
        "horilla_widgets/horilla_clearable_file_input.html"
    )
