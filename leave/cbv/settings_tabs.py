"""
this page is handling the cbv methods for the leave settings page,
which lists restrict leaves as a tab
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import hx_request_required, login_required
from horilla_views.generic.cbv.views import HorillaTabView, TemplateView


@method_decorator(login_required, name="dispatch")
class LeaveSettingsView(TemplateView):
    """
    page for leave settings (Restrict Leaves tab)
    """

    template_name = "cbv/leave_settings/leave_settings_main.html"


@method_decorator(login_required, name="dispatch")
class LeaveSettingsTabView(HorillaTabView):
    """
    tab view for leave settings, shows restrict leaves as a tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Restrict Leaves"),
                "url": f"{reverse('leave-settings-restrict-leaves-tab')}",
            },
        ]


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class LeaveSettingsRestrictLeavesTab(TemplateView):
    """
    restrict leaves tab content, embeds the existing nav + list
    """

    template_name = "cbv/leave_settings/restrict_leaves_tab.html"
