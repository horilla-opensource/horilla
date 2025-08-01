"""
This page handles the cbv methods for federal tax
"""

import math
from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.models import Holidays
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView
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
