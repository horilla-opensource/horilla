from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _trans

from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from whatsapp.filters import CredentialsViewFilter
from whatsapp.forms import WhatsappForm
from whatsapp.models import WhatsappCredientials
from whatsapp.utils import send_text_message


class CredentialListView(HorillaListView):

    model = WhatsappCredientials
    filter_class = CredentialsViewFilter
    show_filter_tags = False

    columns = [
        (_trans("Phone Number"), "meta_phone_number"),
        (_trans("Phone Number ID"), "meta_phone_number_id"),
        (_trans("Bussiness ID"), "meta_business_id"),
        (_trans("Webhook Token"), "get_webhook_token"),
        (_trans("Token"), "token_render"),
    ]
    # sortby_mapping = [("Bussiness ID", "meta_business_id")]
    row_attrs = """
                    id = "credential{get_instance}"
                """
    option_method = "get_publish_button"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_url = reverse("whatsapp-credential-list")
        self.view_id = "CredentialList"
        self.actions = [
            {
                "action": "Edit",
                "icon": "create-outline",
                "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100"
                        data-toggle="oh-modal-toggle"
                        data-target = "#genericModal"
                        hx-target = "#genericModalBody"
                        hx-get = "{get_update_url}"
                        """,
            },
            {
                "action": "Test test message",
                "icon": "link-outline",
                "attrs": """
                        class="oh-btn oh-btn--light-bkg w-100"
                        data-toggle="oh-modal-toggle"
                        data-target = "#genericModal"
                        hx-target = "#genericModalBody"
                        hx-get = "{get_test_message_url}"
                        """,
            },
            {
                "action": "Delete",
                "icon": "trash-outline",
                "attrs": """
                        class="oh-btn oh-btn--danger-outline w-100"
                        hx-confirm = "Are you sure you want to delete this credential?"
                        hx-post = "{get_delete_url}"
                        hx-target = "#credential{get_instance}"
                        hx-swap = "outerHTML"
                        """,
            },
        ]

        self.row_attrs = """
        id="credential{get_instance}"
        {get_primary}
        """


class CredentialNav(HorillaNavView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_url = reverse("whatsapp-credential-list")
        self.create_attrs = f"""
                                data-toggle="oh-modal-toggle"
                                data-target = "#genericModal"
                                hx-target = "#genericModalBody"
                                hx-get = "{reverse('whatsapp-credential-create')}"
                            """

    nav_title = "Whatsapp Credentials"
    search_swap_target = "#listContainer"
    filter_instance = CredentialsViewFilter()


class CredentialForm(HorillaFormView):
    model = WhatsappCredientials
    form_class = WhatsappForm
    new_display_title = "Create whatsapp"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = "Update Credentials"
        return context

    def form_valid(self, form: WhatsappForm) -> HttpResponse:
        if form.is_valid():
            if self.form.instance.pk:
                messages.success(self.request, "Crediential updated successfully")
            else:
                messages.success(self.request, "Crediential created successfully")
            form.save()
            return self.HttpResponse()
        return super().form_valid(form)


def delete_credentials(request):
    id = request.GET.get("id")
    crediential = WhatsappCredientials.objects.filter(id=id).first()
    count = WhatsappCredientials.objects.count()
    crediential.delete()
    messages.success(request, f"Crediential deleted.")
    if count == 1:
        return HttpResponse("<script>$('.reload-record').click();</script>")
    return HttpResponse("<script>$('#reloadMessagesButton').click();</script>")


def send_test_message(request):
    message = "This is a test message"
    if request.method == "POST":
        number = request.POST.get("number")
        response = send_text_message(number, message)
        print(response)
        if response:
            messages.success(request, "Message sent successfully")
        else:
            messages.error(request, "message not send")
        return HttpResponse("<script>window.location.reload()</script>")

    return render(request, "whatsapp/send_test_message_form.html")
