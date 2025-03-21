"""
This page handles the mail server page in settings
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.filters import MailServerFilter
from base.forms import DynamicMailConfForm
from base.models import DynamicEmailConfiguration
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="base.view_dynamicemailconfiguration"), name="dispatch"
)
class MailServerListView(HorillaListView):
    """
    List view of the resticted days page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.action_method = "actions_col"
        self.view_id = "mail-server-cont"
        self.search_url = reverse("mail-server-list")

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        primary_mail_not_exist = True
        if DynamicEmailConfiguration.objects.filter(is_primary=True).exists():
            primary_mail_not_exist = False
        context["primary_mail_not_exist"] = primary_mail_not_exist
        return context

    model = DynamicEmailConfiguration
    filter_class = MailServerFilter
    template_name = "cbv/settings/extended_mail_server.html"

    columns = [
        (_("Host User"), "username"),
        (_("Host"), "host"),
        (_("Compnay"), "company_id"),
    ]

    header_attrs = {
        "action": """
                    style="width:200px !important"
                   """
    }

    row_attrs = "{highlight_cell}"
    action_method = "action_col"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="base.view_dynamicemailconfiguration"), name="dispatch"
)
class MailServerNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("mail-server-list")
        if self.request.user.has_perm("base.add_dynamicemailconfiguration"):
            self.create_attrs = f"""
                                onclick = "event.stopPropagation();"
                                data-toggle="oh-modal-toggle"
                                data-target="#genericModal"
                                hx-target="#genericModalBody"
                                hx-get="{reverse('create-mail-server')}"
                            """

    nav_title = _("Mail Servers")
    filter_instance = MailServerFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="base.add_dynamicemailconfiguration"), name="dispatch"
)
class MailServerFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = DynamicEmailConfiguration
    form_class = DynamicMailConfForm
    new_display_title = _("Create Mail Server")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Mail Server")
        return context

    def form_valid(self, form: DynamicMailConfForm) -> HttpResponse:

        if form.is_valid():
            if form.instance.pk:
                message = _("Mail server updated successfully.")
            else:
                message = _("Mail server created successfully.")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
