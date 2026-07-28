"""
employee/cbv/requests_nav.py

Nav views for shift request tabs inside the unified Work Requests page.
"""

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.cbv.shift_request import ShitRequestNav
from horilla_views.cbv_methods import login_required


@method_decorator(login_required, name="dispatch")
class RequestsShiftNav(ShitRequestNav):
    """Shift requests nav for the Work Requests page (without internal allocated tab)."""

    nav_title = _("Shift Requests")
    template_name = "generic/inline_nav.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = reverse("list-shift-request")


@method_decorator(login_required, name="dispatch")
class RequestsShiftInboxNav(ShitRequestNav):
    """Shift inbox nav for allocated shift requests on the Work Requests page."""

    nav_title = _("Shift Inbox")
    template_name = "generic/inline_nav.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = reverse("allocated-shift-view")
        self.create_attrs = None
