"""
this page is handling the cbv methods for the helpdesk settings page,
which lists department managers, ticket type and helpdesk tags as tabs
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import hx_request_required, login_required
from horilla_views.generic.cbv.views import HorillaTabView, TemplateView


@method_decorator(login_required, name="dispatch")
class HelpdeskSettingsView(TemplateView):
    """
    page for helpdesk settings (Department Managers / Ticket Type / Helpdesk Tags tabs)
    """

    template_name = "cbv/helpdesk_settings/helpdesk_settings_main.html"


@method_decorator(login_required, name="dispatch")
class HelpdeskSettingsTabView(HorillaTabView):
    """
    tab view for helpdesk settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Department Managers"),
                "url": f"{reverse('helpdesk-settings-department-manager-tab')}",
            },
            {
                "title": _("Ticket Type"),
                "url": f"{reverse('helpdesk-settings-ticket-type-tab')}",
            },
            {
                "title": _("Helpdesk Tags"),
                "url": f"{reverse('helpdesk-settings-tags-tab')}",
            },
        ]


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class HelpdeskSettingsDepartmentManagerTab(TemplateView):
    """
    department managers tab content, embeds the existing nav + list
    """

    template_name = "cbv/helpdesk_settings/department_manager_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class HelpdeskSettingsTicketTypeTab(TemplateView):
    """
    ticket type tab content, embeds the existing nav + list
    """

    template_name = "cbv/helpdesk_settings/ticket_type_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class HelpdeskSettingsTagsTab(TemplateView):
    """
    helpdesk tags tab content, embeds the existing nav + list
    """

    template_name = "cbv/helpdesk_settings/tags_tab.html"
