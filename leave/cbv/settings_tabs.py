"""
this page is handling the cbv methods for the leave settings page,
which lists leave types and multiple approval rules as tabs
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
    page for leave settings (Leave Types and Multiple Approval Rules tabs)
    """

    template_name = "cbv/leave_settings/leave_settings_main.html"


@method_decorator(login_required, name="dispatch")
class LeaveSettingsTabView(HorillaTabView):
    """
    tab view for leave settings, shows leave types and approval rules as tabs
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Leave Types"),
                "url": f"{reverse('leave-settings-leave-types-tab')}",
            },
            {
                "title": _("Multiple Approval Rules"),
                "url": f"{reverse('leave-settings-approvals-tab')}",
            },
        ]


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class LeaveSettingsLeaveTypesTab(TemplateView):
    """
    leave types tab content, embeds the existing nav + list
    """

    template_name = "cbv/leave_settings/leave_types_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class LeaveSettingsApprovalsTab(TemplateView):
    """
    multiple approval rules tab content, embeds the existing nav + list
    """

    template_name = "cbv/leave_settings/multiple_approval_tab.html"
