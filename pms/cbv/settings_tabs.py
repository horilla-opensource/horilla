"""
this page is handling the cbv methods for the performance settings page,
which lists bonus point setting, objective templates, question template
and period as tabs
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import hx_request_required, login_required
from horilla_views.generic.cbv.views import HorillaTabView, TemplateView
from pms.cbv.objectives import ObjectiveTemplateList, ObjectiveTemplateNav
from pms.cbv.period import PeriodList, PeriodNav
from pms.cbv.question_template import QuestionTemplateList, QuestionTemplateNav


@method_decorator(login_required, name="dispatch")
class PerformanceSettingsView(TemplateView):
    """
    page for performance settings (Bonus Point Setting, Objective Templates,
    Question Template and Period tabs)
    """

    template_name = "cbv/performance_settings/performance_settings_main.html"


@method_decorator(login_required, name="dispatch")
class PerformanceSettingsTabView(HorillaTabView):
    """
    tab view for performance settings
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Objective Templates"),
                "url": f"{reverse('performance-settings-objective-template-tab')}",
            },
            {
                "title": _("Question Template"),
                "url": f"{reverse('performance-settings-question-template-tab')}",
            },
            {
                "title": _("Period"),
                "url": f"{reverse('performance-settings-period-tab')}",
            },
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


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PerformanceSettingsObjectiveTemplateTab(TemplateView):
    """
    objective template tab content, embeds the existing nav + list
    """

    template_name = "cbv/performance_settings/objective_template_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PerformanceSettingsQuestionTemplateTab(TemplateView):
    """
    question template tab content, embeds the existing nav + list
    """

    template_name = "cbv/performance_settings/question_template_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PerformanceSettingsPeriodTab(TemplateView):
    """
    period tab content, embeds the existing nav + list
    """

    template_name = "cbv/performance_settings/period_tab.html"


# The nav/list pairs below reuse the existing Objective Template / Question
# Template / Period nav bars and list views as-is, only overriding the ids
# they render (list container, bulk-select store, view id) to be unique to
# this settings tab. This is necessary because HorillaTabView keeps every
# visited tab's content in the DOM at once (hidden via CSS, not destroyed),
# so the originals' shared "#listContainer" / "#selectedInstances" ids would
# silently collide across tabs the moment more than one has been opened.
# The original classes/URLs are left untouched since their own standalone
# pages still use them.


class PerformanceSettingsObjectiveTemplateList(ObjectiveTemplateList):
    """Objective Template list, scoped to this settings tab."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "objectiveTemplateSettingsContainer"

    selected_instances_key_id = "objectiveTemplateSettingsSelectedInstances"


class PerformanceSettingsObjectiveTemplateNav(ObjectiveTemplateNav):
    """Objective Template nav bar, scoped to this settings tab."""

    search_swap_target = "#objectiveTemplateSettingsListContainer"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("performance-settings-objective-template-list")


class PerformanceSettingsQuestionTemplateList(QuestionTemplateList):
    """Question Template list, scoped to this settings tab."""

    selected_instances_key_id = "questionTemplateSettingsSelectedInstances"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "questionTemplateSettingsList"


class PerformanceSettingsQuestionTemplateNav(QuestionTemplateNav):
    """Question Template nav bar, scoped to this settings tab."""

    search_swap_target = "#questionTemplateSettingsListContainer"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("performance-settings-question-template-list")


class PerformanceSettingsPeriodList(PeriodList):
    """Period list, scoped to this settings tab."""

    selected_instances_key_id = "periodSettingsSelectedInstances"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "periodSettingsListTable"


class PerformanceSettingsPeriodNav(PeriodNav):
    """Period nav bar, scoped to this settings tab."""

    search_swap_target = "#periodSettingsListContainer"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("performance-settings-period-list")
