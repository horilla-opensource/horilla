"""
this page is handling the cbv methods for the performance settings page,
which lists bonus point setting as a tab
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import hx_request_required, login_required
from horilla_views.generic.cbv.views import HorillaTabView, TemplateView


@method_decorator(login_required, name="dispatch")
class PerformanceSettingsView(TemplateView):
    """
    page for performance settings (Bonus Point Setting tab)
    """

    template_name = "cbv/performance_settings/performance_settings_main.html"


@method_decorator(login_required, name="dispatch")
class PerformanceSettingsTabView(HorillaTabView):
    """
    tab view for performance settings, shows bonus point setting as a tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Bonus Point Setting"),
                "url": f"{reverse('performance-settings-bonus-point-tab')}",
            },
        ]


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PerformanceSettingsBonusPointTab(TemplateView):
    """
    bonus point setting tab content, embeds the existing nav + list
    """

    template_name = "cbv/performance_settings/bonus_point_tab.html"
