"""
Shared per-tab shell for Attendance's Employee-Configuration-style tab
pages: each tab loads its own dedicated Nav (Search/Filter/Create/Actions,
independent of the other tabs) followed by that tab's own list container,
instead of one Nav shared above all tabs. Reused by both the Attendances
page (attendance/cbv/attendances.py) and the Attendance Requests page
(attendance/cbv/attendance_request.py).
"""

from typing import Any

from django.utils.decorators import method_decorator

from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import TemplateView


@method_decorator(login_required, name="dispatch")
class AttendanceTabContentShell(TemplateView):
    """
    Base shell: subclasses set nav_url_name/container_id/tabs_root_id
    (and optionally selected_instances_key_id) as class attributes.
    """

    template_name = "cbv/attendances/attendance_tab_shell.html"
    nav_url_name = ""
    container_id = ""
    tabs_root_id = ""
    selected_instances_key_id = "selectedInstances"

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context["nav_url_name"] = self.nav_url_name
        context["container_id"] = self.container_id
        context["tabs_root_id"] = self.tabs_root_id
        context["selected_instances_key_id"] = self.selected_instances_key_id
        return context
