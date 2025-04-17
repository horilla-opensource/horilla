"""
outlook_auth/forms.py
"""

from base.forms import ModelForm
from outlook_auth import models


class OutlookServerForm(ModelForm):
    """
    OutlookServerForm
    """

    class Meta:
        """
        Meta
        """

        model = models.AzureApi
        fields = "__all__"
