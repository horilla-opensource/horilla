from django import forms
from django.utils.translation import gettext_lazy as _

from hydra_notifications.models import (
    NotificationCategory,
    NotificationSeverity,
)


class NotificationFilterForm(forms.Form):
    STATE_CHOICES = (
        ("", _("Active notifications")),
        ("unread", _("Unread")),
        ("read", _("Read")),
        ("archived", _("Archived")),
    )

    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)
    category = forms.ChoiceField(
        choices=(("", _("All categories")),) + tuple(NotificationCategory.choices),
        required=False,
    )
    severity = forms.ChoiceField(
        choices=(("", _("All severities")),) + tuple(NotificationSeverity.choices),
        required=False,
    )


class NotificationPreferenceForm(forms.Form):
    email_enabled = forms.BooleanField(
        label=_("Send immediate email for matching notifications"),
        required=False,
    )
    email_min_severity = forms.ChoiceField(
        label=_("Minimum email severity"),
        choices=NotificationSeverity.choices,
    )
    browser_sound_enabled = forms.BooleanField(
        label=_("Play a browser sound for new notifications"),
        required=False,
    )
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput())

    def __init__(self, *args, preference, **kwargs):
        self.preference = preference
        if not args and "initial" not in kwargs:
            kwargs["initial"] = {
                "email_enabled": preference.email_enabled,
                "email_min_severity": preference.email_min_severity,
                "browser_sound_enabled": preference.browser_sound_enabled,
                "version": preference.version,
            }
        super().__init__(*args, **kwargs)
        self.fields["email_min_severity"].widget.attrs["class"] = "oh-select w-100"
