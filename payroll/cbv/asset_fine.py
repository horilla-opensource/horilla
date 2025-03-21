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
        if form.is_valid():
            form.save()
            messages.success(self.request, "Asset fine added")
            return HttpResponse("<script>$('#reloadMessagesButton').click()</script>")
        return super().form_valid(form)
