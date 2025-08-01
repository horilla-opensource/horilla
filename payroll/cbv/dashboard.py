"""
This page handles the cbv methods for payroll dashboard
"""

import calendar
from typing import Any

from django.db.models import F, Sum, Value
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.filters import DepartmentViewFilter
from base.models import Department
from horilla_views.generic.cbv.views import HorillaListView
from payroll.filters import ContractFilter
from payroll.models.models import Contract


class DashboardDepartmentPayslip(HorillaListView):
    """
    list view for total department payslip
    """

    model = Department
    filter_class = DepartmentViewFilter
    show_filter_tags = False
    bulk_select_option = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-department-chart")
        self.view_id = "dashboadDepartment"

    def get_queryset(self):

        month_year = self.request.GET.get("monthYearField")
        current_year = month_year.split("-")[0]
        current_month = month_year.split("-")[1]

        month_name = calendar.month_name[int(current_month)]
        queryset = (
            super()
            .get_queryset()
            .filter(
                employeeworkinformation__employee_id__payslip__start_date__year=current_year,
                employeeworkinformation__employee_id__payslip__start_date__month=current_month,
            )
            .annotate(
                total_net_pay=Sum(
                    "employeeworkinformation__employee_id__payslip__net_pay"
                ),
                department_id=F("employeeworkinformation__department_id__department"),
                month=Value(current_month),
            )
        )
        return queryset

    columns = [
        (_("Department"), "department_id"),
        (_("Total Net Pay"), "total_net_pay"),
    ]

    row_attrs = """
                onclick="window.location.href='/payroll/view-payslip/?department={department_id}&month={month}&department={department_id}'"
                """


class DashboardContractList(HorillaListView):
    """
    list view for contract ending this month
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-contract-ending")

    model = Contract
    filter_class = ContractFilter
    show_filter_tags = None
    bulk_select_option = False
    template_name = "cbv/dashboard/contract_ending.html"
    show_toggle_form = False

    def get_queryset(self):
        queryset = super().get_queryset()
        month_year = self.request.GET.get("monthYearField")
        current_date = timezone.now()
        current_year = current_date.year
        current_month = current_date.month
        year = month_year.split("-")[0]
        month = month_year.split("-")[1]
        input_month_year = (int(year), int(month))
        current_month_year = (current_year, current_month)

        if input_month_year < current_month_year:
            month = current_month
            year = current_year
        queryset = queryset.filter(
            contract_end_date__month=int(month), contract_end_date__year=int(year)
        )
        return queryset

    columns = [
        (_("Contract"), "contract_name"),
        (_("Ending Date"), "contract_end_date"),
    ]

    header_attrs = {
        "contract_name": """
                              style="width:200px !important;"
                              """
    }
    row_attrs = """
                hx-get='{contracts_detail}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """


class DashboardContractListExpired(HorillaListView):
    """
    list view for contract ending this month
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("dashboard-contract-expired")

    model = Contract
    filter_class = ContractFilter
    show_filter_tags = None
    bulk_select_option = False
    template_name = "cbv/dashboard/contract_expired.html"
    show_toggle_form = False

    def get_queryset(self):
        queryset = super().get_queryset()
        month_year = self.request.GET.get("monthYearField")
        current_date = timezone.now()
        current_year = current_date.year
        current_month = current_date.month
        year = month_year.split("-")[0]
        month = month_year.split("-")[1]
        input_month_year = (int(year), int(month))
        current_month_year = (current_year, current_month)
        if input_month_year >= current_month_year:
            if current_month == 1:
                month = 12
                year = current_year - 1
            else:
                month = current_month - 1
                year = current_year
        queryset = queryset.filter(
            contract_end_date__month=int(month), contract_end_date__year=int(year)
        )
        return queryset

    columns = [
        (_("Contract"), "contract_name"),
        (_("Expired Date"), "contract_end_date"),
    ]

    header_attrs = {
        "contract_name": """
                              style="width:200px !important;"
                              """
    }
    row_attrs = """
                hx-get='{contracts_detail}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
