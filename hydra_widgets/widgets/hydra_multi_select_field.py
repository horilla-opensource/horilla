"""
hydra_multi_select_field.py
This module is used to write cutom multiple select field
"""

from django import forms


class HydraMultiSelectField(forms.ModelMultipleChoiceField):
    """
    HydraMultiSelectField
    """
