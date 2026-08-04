"""
this page is handling the cbv methods for the helpdesk settings page,
which lists department managers, ticket type and helpdesk tags as tabs
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.models import Tags
from helpdesk.filter import DepartmentManagerFilter, TagsFilter, TicketTypeFilter
from helpdesk.models import DepartmentManager, TicketType
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

        query_string = self.request.GET.urlencode()

        def with_query(url):
            return f"{url}?{query_string}" if query_string else url

        department_manager_count = DepartmentManagerFilter(
            self.request.GET, queryset=DepartmentManager.objects.all()
        ).qs.count()
        ticket_type_count = TicketTypeFilter(
            self.request.GET, queryset=TicketType.objects.all()
        ).qs.count()
        tags_count = TagsFilter(
            self.request.GET, queryset=Tags.objects.all()
        ).qs.count()

        self.tabs = [
            {
                "title": _("Department Managers"),
                "url": with_query(reverse("helpdesk-settings-department-manager-tab")),
                "badge": department_manager_count,
            },
            {
                "title": _("Ticket Types"),
                "url": with_query(reverse("helpdesk-settings-ticket-type-tab")),
                "badge": ticket_type_count,
            },
            {
                "title": _("Helpdesk Tags"),
                "url": with_query(reverse("helpdesk-settings-tags-tab")),
                "badge": tags_count,
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
