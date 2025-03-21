from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from attendance.filters import AttendanceGeneralSettingFilter
from attendance.models import AttendanceGeneralSetting
from horilla_views.generic.cbv.views import HorillaListView, HorillaNavView


class CheckInCheckOutListView(HorillaListView):
    """
    List view of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "check-in-check-out"

    model = AttendanceGeneralSetting
    filter_class = AttendanceGeneralSettingFilter

    columns = [
        (_("Company"), "company_col"),
        (_("Check in/Check out"), "check_in_check_out_col"),
    ]

    header_attrs = {
        "company_col": """
                   style = "width:100px !important"
                   """,
    }

    bulk_select_option = False


class CheckInCheckOutNavBar(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # self.search_url = reverse("check-in-check-out-list")

    nav_title = _("Enable Check In/Check out")
    filter_instance = AttendanceGeneralSettingFilter()
    search_swap_target = "#listContainer"
