from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaCardView,
    HorillaListView,
    HorillaNavView,
    TemplateView,
)
from payroll.filters import DeductionFilter
from payroll.models.models import Deduction


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="payroll.view_deduction"), name="dispatch")
class DeductionView(TemplateView):

    template_name = "cbv/deduction/deduction.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="payroll.view_deduction"), name="dispatch")
class DeductionNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("deduction-view-list")
        self.create_attrs = f"""
                          href={reverse('create-deduction')}
                          """
        self.view_types = [
            {
                "type": "list",
                "icon": "list-outline",
                "url": reverse("deduction-view-list"),
                "attrs": """
                            title='List'
                            """,
            },
            {
                "type": "card",
                "icon": "grid-outline",
                "url": reverse("deduction-view-card"),
                "attrs": """
                            title='Card'
                            """,
            },
        ]

    nav_title = _("Deductions")
    filter_body_template = "cbv/deduction/filter.html"
    filter_instance = DeductionFilter()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="payroll.view_deduction"), name="dispatch")
class DeductionListView(HorillaListView):
    """
    list view for deduction tab
    """

    model = Deduction
    filter_class = DeductionFilter

    bulk_update_fields = [
        "specific_employees",
        "exclude_employees",
        "is_pretax",
        "is_fixed",
        "amount",
        "based_on",
        "rate",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "deduct-container"
        if self.request.user.has_perm(
            "payroll.change_deduction"
        ) or self.request.user.has_perm("payroll.change_deduction"):
            self.action_method = "deduct_actions"
        else:
            self.action_method = None
        self.search_url = reverse("deduction-view-list")

    row_attrs = """
                {diff_cell}
                hx-get='{deduction_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """

    row_status_indications = [
        (
            "pretax--dot",
            _("Pretax"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_pretax]').val('true');
                $('[name=is_fixed]').val('unknown').change();
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "fixed--dot",
            _("Fixed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_fixed]').val('true');
                $('[name=is_pretax]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "not-fixed--dot",
            _("Not Fixed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_fixed]').val('false');
                $('[name=is_pretax]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    # row_status_class = "pretax-{is_pretax} fixed-{is_fixed}"

    columns = [
        (_("Deduction"), "title"),
        (_("Specific Employees"), "specific_employees_col"),
        (_("Excluded Employees"), "excluded_employees_col"),
        (_("Is Pretax"), "get_is_pretax_display"),
        (_("Is Condition Based"), "get_is_condition_based_display"),
        (_("Condition"), "condition_based_col"),
        (_("Is Fixed"), "get_is_fixed_display"),
        (_("Amount"), "amount"),
        (_("Based On"), "get_based_on_display"),
        (_("Rate"), "rate"),
    ]

    header_attrs = {
        "title": """style="width:180px !important;" """,
        "excluded_employees_col": """ style="width:180px !important;" """,
    }

    sortby_mapping = [
        ("Deduction", "title"),
        ("Specific Employees", "specific_employees_col"),
        ("Excluded Employees", "excluded_employees_col"),
        ("Amount", "amount"),
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        # queryset = queryset.exclude(only_show_under_employee=True)
        return queryset.exclude(only_show_under_employee=True)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required(perm="payroll.view_deduction"), name="dispatch")
class DeductionCardView(HorillaCardView):
    """
    card view
    """

    model = Deduction
    filter_class = DeductionFilter

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "deduct-container"
        # if self.request.user.has_perm(
        #     "payroll.change_deduction"
        # ) or self.request.user.has_perm("payroll.change_deduction"):
        #     self.action_method = "deduct_actions"
        # else:
        #     self.action_method = None
        # self.search_url = reverse("deduction-view-card")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(only_show_under_employee=True)
        return queryset

    details = {
        "image_src": "get_avatar",
        "title": "{title}",
        "subtitle": "Amount : <br> {amount_col} <br> Is Pretax : {get_is_pretax_display} <br> One Time deduction : {get_one_time_deduction}",
    }

    card_status_indications = [
        (
            "pretax--dot",
            _("Pretax"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_pretax]').val('true');
                $('[name=is_fixed]').val('unknown').change();
                $('#applyFilter').click();
            "
            """,
        ),
        (
            "fixed--dot",
            _("Fixed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_fixed]').val('true');
                $('[name=is_pretax]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
        (
            "not-fixed--dot",
            _("Not Fixed"),
            """
            onclick="
                $('#applyFilter').closest('form').find('[name=is_fixed]').val('false');
                $('[name=is_pretax]').val('unknown').change();
                $('#applyFilter').click();

            "
            """,
        ),
    ]

    card_attrs = """
                hx-get='{deduction_detail_view}?instance_ids={ordered_ids}'
                data-toggle="oh-modal-toggle"
                data-target="#genericModal"
                hx-target="#genericModalBody"
                """

    actions = [
        {
            "action": _("Edit"),
            "attrs": """
            class="oh-dropdown__link"
            onclick="window.location.href='{get_update_url}' "
            """,
        },
        {
            "action": _("Delete"),
            "attrs": """
                    onclick="event.stopPropagation()"
                    hx-get="{get_delete_url}?model=payroll.Deduction&pk={pk}"
                    data-toggle="oh-modal-toggle"
                    data-target="#deleteConfirmation"
                    hx-target="#deleteConfirmationBody"
                    class="oh-dropdown__link"
                    style="cursor: pointer;"

                    """,
        },
    ]

    records_per_page = 10
