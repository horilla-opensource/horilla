import datetime
from typing import Any

from django import forms
from django.apps import apps
from django.contrib import messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from horilla.methods import get_horilla_model_class
from horilla_views.generic.cbv.views import HorillaFormView
from payroll.forms.component_forms import AssetFineForm, LoanAccountForm
from payroll.models.models import LoanAccount


class AssetFineFormView(HorillaFormView):
    """
    form view for create asset assign form
    """

    model = LoanAccount
    form_class = AssetFineForm
    new_display_title = _("Asset Fine")

    def form_valid(self, form: AssetFineForm) -> HttpResponse:
        if apps.is_installed("asset"):
            Asset = get_horilla_model_class(app_label="asset", model="asset")
        asset_id = self.request.GET["asset_id"]
        employee_id = self.request.GET["employee_id"]
        asset = Asset.objects.get(id=asset_id)
        employee = Employee.objects.get(id=employee_id)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.employee_id = employee
            instance.type = "fine"
            instance.provided_date = datetime.date.today()
            instance.asset_id = asset
            instance.save()
            messages.success(self.request, "Asset fine added")
            return HttpResponse(
                "<script>$('#dynamicCreateModal').toggleClass('oh-modal--show'); $('#reloadMessagesButton').click()</script>"
            )
        return super().form_valid(form)
