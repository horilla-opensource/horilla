"""
outlook_auth/cbv.py

"""

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv import views
from outlook_auth import filters, forms, models


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="outlook_auth.view_azureapi"), name="dispatch"
)
class ServerNav(views.HorillaNavView):
    """
    ServerList
    """

    model = models.AzureApi
    search_url = reverse_lazy("outlook_server_list")

    def __init__(self, **kwargs):
        self.create_attrs = f"""
            onclick = "event.stopPropagation();"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
            hx-target="#genericModalBody"
            hx-get="{reverse_lazy('outlook_server_create')}"
        """
        super().__init__(**kwargs)

    nav_title = _("Mail Servers")
    filter_instance = filters.AzureApiFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="outlook_auth.view_azureapi"), name="dispatch"
)
class ServerList(views.HorillaListView):
    """
    ServerList
    """

    model = models.AzureApi
    view_id = "listContainer"
    columns = [
        (_("Name"), "outlook_display_name"),
        (_("Email"), "outlook_email"),
        (_("Company"), "company"),
        (_("Token Expire"), "token_expire"),
        (_("Primary"), "is_primary"),
    ]
    show_filter_tags = False
    filter_class = filters.AzureApiFilter
    search_url = reverse_lazy("outlook_server_list")
    action_method = "actions"
    selected_instances_key_id = "selectedRecords"
    header_attrs = {
        "action": """
            style = "width:298px !important"
        """,
    }


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="outlook_auth.add_azureapi"), name="dispatch"
)
class ServerForm(views.HorillaFormView):
    """
    ServerForm
    """

    model = models.AzureApi
    form_class = forms.OutlookServerForm
    new_display_title = _("Create Mail Server")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Mail Server")
        return context

    def form_valid(self, form: forms.OutlookServerForm) -> HttpResponse:

        if form.is_valid():
            if form.instance.pk:
                message = _("Mail server updated successfully.")
            else:
                message = _("Mail server created successfully.")
            form.save()
            messages.success(self.request, _(message))
            return self.HttpResponse()
        return super().form_valid(form)
