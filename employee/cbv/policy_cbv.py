"""
Policy  forms
"""

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.filters import PolicyFilter
from employee.forms import PolicyForm
from employee.models import Policy
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView, HorillaNavView


class PolicyFormView(HorillaFormView):
    """
    form view for create policy
    """

    form_class = PolicyForm
    model = Policy
    new_display_title = _("Policy Creation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Policy Update")
        return context

    def form_valid(self, form: PolicyForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Policy saved")
            else:
                message = _("Policy updated")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


class PoliciesNav(HorillaNavView):
    """
    Policies Nav
    """

    nav_title = _("Policies")
    search_url = reverse_lazy("search-policies")
    search_swap_target = "#policyContainer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_attrs = f"""
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
            hx-get="{reverse_lazy('create-policy')}"
            hx-target="#genericModalBody"
        """
