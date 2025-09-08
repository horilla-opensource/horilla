"""
This page handles the cbv methods for federal tax
"""

import math
from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.models import Holidays
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.pipeline import Pipeline
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from payroll.filters import FilingStatusFilter, TaxBracketFilter
from payroll.forms.tax_forms import FilingStatusForm, TaxBracketForm
from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.add_filingstatus"), name="dispatch")
class FederalTaxFormView(HorillaFormView):
    """
    form view for create button
    """

    form_class = FilingStatusForm
    model = FilingStatus
    template_name = "cbv/federal_tax/form_inherit.html"
    new_display_title = _("Create Filing Status")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Filing Status")

        return context

    def form_valid(self, form: FilingStatusForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Filing Status Updated Successfully")
            else:
                message = _("Filing StatusCreated Successfully")
            form.save()

            messages.success(self.request, _(message))
            return self.HttpResponse("<script>location.reload();</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.add_taxbracket"), name="dispatch")
class TaxBracketCreateForm(HorillaFormView):
    """
    from view for create and edit tax brackets
    """

    model = TaxBracket
    form_class = TaxBracketForm
    new_display_title = _("Create Tax Bracket")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            tax_bracket = TaxBracket.find(self.form.instance.pk)
            filing_status_id = tax_bracket.filing_status_id.id
            self.form_class.verbose_name = _("Update Tax Bracket")
        else:
            filing_status_id = self.kwargs.get("filing_status_id")
            filling = FilingStatus.objects.get(id=filing_status_id)
            self.form.fields["filing_status_id"].initial = filling
            context["is_create"] = True

        context["form"] = self.form
        return context

    def form_valid(self, form: TaxBracketForm) -> HttpResponse:
        if form.is_valid():
            max_income = self.form.cleaned_data.get("max_income")
            if not max_income:
                messages.info(self.request, _("The maximum income will be infinite"))
                self.form.instance.max_income = math.inf
            if form.instance.pk:
                messages.success(
                    self.request, _("The tax bracket has been updated successfully.")
                )
            else:
                messages.success(
                    self.request, _("The tax bracket was created successfully.")
                )
            filing_status_id = self.form.cleaned_data.get("filing_status_id")
            context = {
                "filing_status_id": filing_status_id.id,
                "form_instance": form.instance.pk,
            }
            template = "cbv/federal_tax/tax_bracket.html"
            html = render_to_string(template, context)
            form.save()
            return HttpResponse(html)
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_taxbracket"), name="dispatch")
class TaxBracketNavView(HorillaNavView):
    """
    Nav view for tax bracket list
    """

    nav_title = _("Filing Status")
    search_swap_target = "#FilingStatusList"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = f"{reverse_lazy('filing-status-search')}"
        self.create_attrs = f"""
            data-toggle="oh-modal-toggle"
            data-target="#objectCreateModal"
            hx-get="{reverse_lazy('create-filing-status')}"
            hx-target="#objectCreateModalTarget"
        """


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_taxbracket"), name="dispatch")
class FilingStatusPipeline(Pipeline):
    """
    Pipeline class for FilingStatus model.
    """

    model = TaxBracket
    filter_class = TaxBracketFilter
    grouper = "filing_status_id"
    template_name = "cbv/federal_tax/pipeline.html"

    allowed_fields = [
        {
            "field": "filing_status_id",
            "model": FilingStatus,
            "filter": FilingStatusFilter,
            "url": reverse_lazy("filing-status-list"),
            "parameters": [
                "filing_status_id={pk}",
            ],
            "actions": [
                {
                    "action": _("Create"),
                    "attrs": """
                        class="oh-dropdown__link oh-dropdown__link"
                        data-toggle="oh-modal-toggle"
                        data-target="#objectCreateModal"
                        hx-get="{get_create_url}"
                        hx-target="#objectCreateModalTarget"
                    """,
                },
                {
                    "action": _("Edit"),
                    "attrs": """
                        class="oh-dropdown__link oh-dropdown__link"
                        data-toggle="oh-modal-toggle"
                        data-target="#objectCreateModal"
                        hx-get="{get_update_url}"
                        hx-target="#objectCreateModalTarget"
                    """,
                },
                {
                    "action": _("Delete"),
                    "attrs": """
                        class="oh-dropdown__link oh-dropdown__link--danger"
                        data-toggle="oh-modal-toggle"
                        data-target="#deleteConfirmation"
                        hx-get="{get_delete_url}"
                        hx-target="#deleteConfirmationBody"
                    """,
                },
            ],
        }
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_taxbracket"), name="dispatch")
class TaxBracketListView(HorillaListView):
    """
    List view for tax brackets
    """

    model = TaxBracket
    filter_class = TaxBracketFilter
    bulk_select_option = False
    template_name = "cbv/federal_tax/tax_bracket_list.html"

    columns = [
        (_("Tax Rate (%)"), "tax_rate"),
        (_("Min. Income"), "min_income"),
        (_("Max. Income"), "get_display_max_income"),
    ]

    filter_keys_to_remove = ["filing_status_id"]
    actions = [
        {
            "action": _("Edit"),
            "icon": "create-outline",
            "attrs": """
                class="oh-btn oh-btn--light-bkg w-100"
                data-toggle="oh-modal-toggle"
                data-target="#objectCreateModal"
                hx-get="{get_update_url}"
                hx-target="#objectCreateModalTarget"
            """,
        },
        {
            "action": _("delete"),
            "icon": "trash-outline",
            "attrs": """
                class="oh-btn oh-btn--danger-outline w-100"
                data-toggle="oh-modal-toggle"
                data-target="#objectCreateModal"
                hx-get="{get_delete_url}"
                hx-target="#objectCreateModalTarget"
            """,
        },
    ]

    def get_queryset(self, queryset=None, filtered=False, *args, **kwargs):
        queryset = super().get_queryset(queryset, filtered, *args, **kwargs)
        queryset = queryset.filter(
            filing_status_id__pk=self.request.GET.get("filing_status_id")
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filing_status_id = self.request.GET.get("filing_status_id")
        filing_status = FilingStatus.objects.get(pk=filing_status_id)
        context["filing_status"] = filing_status
        return context
