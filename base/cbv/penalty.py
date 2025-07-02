from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from base.filters import PenaltyFilter
from base.models import PenaltyAccounts
from horilla_views.generic.cbv.views import HorillaListView


class ViewPenaltyList(HorillaListView):
    """
    List view of penalty
    """

    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("view-penalties")
        self.view_id = "view-penalty"

    model = PenaltyAccounts
    filter_class = PenaltyFilter
    columns = [
        (_("Penalty amount"), "penalty_amount"),
        (_("Created Date"), "created_at"),
    ]

    header_attrs = {
        "penalty_amount": """
                            style="width:180px !important;"
                            """,
        "created_at": """
                            style="width:180px !important;"
                            """,
    }
