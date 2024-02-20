"""
tax_views.py

This module contains view functions for handling federal tax-related operations.

The functions in this module handle various tasks related to payroll, including creating
filing status, managing tax brackets, calculating federal tax, and more. These functions
utilize the Django framework and make use of the render and redirect functions from the
django.shortcuts module.

"""

import math
from urllib.parse import parse_qs
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from horilla.decorators import permission_required, login_required
from base.methods import get_key_instances
from payroll.models.tax_models import (
    TaxBracket,
)
from payroll.forms.tax_forms import (
    FilingStatusForm,
    TaxBracketForm,
)
from payroll.models.models import FilingStatus


@login_required
@permission_required("payroll.view_filingstatus")
def filing_status_view(request):
    """
    Display the filing status view.

    This view retrieves all filing statuses from the database and renders the
    'payroll/tax/filing_status_view.html' template with the filing status data.

    """
    status = FilingStatus.objects.all()
    template = "payroll/tax/filing_status_view.html"
    context = {"status": status}
    return render(request, template, context)


@login_required
@permission_required("payroll.add_filingstatus")
def create_filing_status(request):
    """
    Create a filing status record for tax bracket based on user input.

    If the request method is POST and the form data is valid, save the filing status form
    and redirect to the create-filing-status page.

    """
    filing_status_form = FilingStatusForm()
    if request.method == "POST":
        filing_status_form = FilingStatusForm(request.POST)
        if filing_status_form.is_valid():
            filing_status_form.save()
            messages.success(request, _("Filing status created successfully "))
            filing_status_form = FilingStatusForm()
    return render(
        request,
        "payroll/tax/filing_status_creation.html",
        {
            "form": filing_status_form,
        },
    )


@login_required
@permission_required("payroll.change_filingstatus")
def update_filing_status(request, filing_status_id):
    """
    Update an existing filing status record based on user input.

    If the request method is POST and the form data is valid, update the filing status form
    and redirect to the update-filing-status page.

    :param tax_bracket_id: The ID of the filing status to update.
    """
    filing_status = FilingStatus.objects.get(id=filing_status_id)
    filing_status_form = FilingStatusForm(instance=filing_status)
    if request.method == "POST":
        response = render(
            request,
            "payroll/tax/filing_status_edit.html",
            {
                "form": filing_status_form,
            },
        )
        filing_status_form = FilingStatusForm(request.POST, instance=filing_status)
        if filing_status_form.is_valid():
            filing_status_form.save()
            messages.success(request, _("Filing status updated successfully."))
    return render(
        request,
        "payroll/tax/filing_status_edit.html",
        {
            "form": filing_status_form,
        },
    )


@login_required
@permission_required("payroll.delete_filingstatus")
def filing_status_delete(request, filing_status_id):
    """
    Delete a filing status.

    This view deletes a filing status with the given `filing_status_id` from the
    database and redirects to the filing status view.

    """
    try:
        filing_status = FilingStatus.objects.get(id=filing_status_id)
        filing_status.delete()
        messages.info(request, _("Filing status successfully deleted."))
    except:
        messages.error(request, _("This filing status not found"))

    return redirect(filing_status_search)


@login_required
@permission_required("payroll.view_filingstatus")
def filing_status_search(request):
    search = request.GET.get("search") if request.GET.get("search") else ""
    status = FilingStatus.objects.filter(filing_status__icontains=search)
    previous_data = request.GET.urlencode()
    data_dict = parse_qs(previous_data)
    get_key_instances(FilingStatus, data_dict)
    context = {
        "status": status,
        "pd": previous_data,
        "filter_dict": data_dict,
    }
    return render(request, "payroll/tax/filing_status_list.html", context)


@login_required
@permission_required("payroll.view_taxbracket")
def tax_bracket_list(request, filing_status_id):
    """
    Display a list of tax brackets for a specific filing status.

    This view retrieves all tax brackets associated with the given `filing_status_id`
    and renders them in the "tax_bracket_view.html" template.

    Args:
        request: The HTTP request object.
        filing_status_id: The ID of the filing status for which to display tax brackets.

    Returns:
        The rendered "tax_bracket_view.html" template with the tax brackets for the
        specified filing status.
    """
    tax_brackets = TaxBracket.objects.filter(
        filing_status_id=filing_status_id
    ).order_by("max_income")
    context = {
        "tax_brackets": tax_brackets,
    }
    return render(request, "payroll/tax/tax_bracket_view.html", context)


@login_required
@permission_required("payroll.add_taxbracket")
def create_tax_bracket(request, filing_status_id):
    """
    Create a tax bracket record for federal tax calculation based on user input.

    If the request method is POST and the form data is valid, save the tax bracket form
    and redirect to the tax-bracket-create page.

    """
    tax_bracket_form = TaxBracketForm(initial={"filing_status_id": filing_status_id})
    context = {
        "form": tax_bracket_form,
        "filing_status_id": filing_status_id,
    }
    if request.method == "POST":
        tax_bracket_form = TaxBracketForm(
            request.POST, initial={"filing_status_id": filing_status_id}
        )
        if tax_bracket_form.is_valid():
            max_income = tax_bracket_form.cleaned_data.get("max_income")
            if not max_income:
                messages.info(request, _("The maximum income will be infinite"))
                tax_bracket_form.instance.max_income = math.inf
            tax_bracket_form.save()
            messages.success(request, _("The tax bracket was created successfully."))
            return redirect(create_tax_bracket, filing_status_id=filing_status_id)

        context["form"] = tax_bracket_form

    return render(request, "payroll/tax/tax_bracket_creation.html", context)


@login_required
@permission_required("payroll.change_taxbracket")
def update_tax_bracket(request, tax_bracket_id):
    """
    Update an existing tax bracket record based on user input.

    If the request method is POST and the form data is valid, update the tax bracket form
    and redirect to the tax-bracket-create page.

    :param tax_bracket_id: The ID of the tax bracket to update.
    """
    tax_bracket = TaxBracket.objects.get(id=tax_bracket_id)
    filing_status_id = tax_bracket.filing_status_id.id
    tax_bracket_form = TaxBracketForm(instance=tax_bracket)

    if request.method == "POST":
        tax_bracket_form = TaxBracketForm(request.POST, instance=tax_bracket)
        if tax_bracket_form.is_valid():
            max_income = tax_bracket_form.cleaned_data.get("max_income")
            if not max_income:
                messages.info(request, _("The maximum income will be infinite"))
                tax_bracket_form.instance.max_income = math.inf
            tax_bracket_form.save()
            messages.success(
                request, _("The tax bracket has been updated successfully.")
            )

    context = {
        "form": tax_bracket_form,
        "filing_status_id": filing_status_id,
    }
    return render(request, "payroll/tax/tax_bracket_edit.html", context)


@login_required
@permission_required("payroll.delete_taxbracket")
def delete_tax_bracket(request, tax_bracket_id):
    """
    Delete an existing tax bracket record.

    Retrieve the tax bracket with the specified ID and delete it from the database.
    Then, redirect to the tax-bracket-create page.

    :param tax_bracket_id: The ID of the tax bracket to delete.
    """
    try:
        tax_bracket = TaxBracket.objects.get(id=tax_bracket_id)
        filing_status_id = tax_bracket.filing_status_id.id
        tax_bracket.delete()
        messages.success(request, _("Tax bracket successfully deleted."))
    except:
        messages.error(request, _("Tax bracket not found"))
    return redirect(tax_bracket_list, filing_status_id=filing_status_id)
