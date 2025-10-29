from django.db import models
from django.urls import reverse

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from horilla.models import HorillaModel
from horilla_views.cbv_methods import render_template


class WhatsappCredientials(HorillaModel):
    meta_token = models.TextField()
    meta_business_id = models.CharField(max_length=255)
    meta_phone_number_id = models.CharField(max_length=255)
    meta_phone_number = models.CharField(max_length=20)
    created_templates = models.BooleanField(default=False)
    meta_webhook_token = models.CharField(
        max_length=50,
        verbose_name="Webhook Token",
        help_text="This token is used to connect webhook to the server",
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name="Company")
    is_primary = models.BooleanField(default=False)

    # objects = HorillaCompanyManager()

    def __str__(self):
        return f"WhatsApp Business {self.meta_business_id} ({self.meta_phone_number})"

    def token_render(self):

        alert = """
                    Swal.fire({
                    text: "Token copied",
                    icon: "success",
                    showConfirmButton: false,
                    timer: 2000,
                    timerProgressBar: true,
                    });
                """

        html = f"""
        <span onclick="copyToken()" title={self.meta_token}>{self.meta_token[:20]}...</span>
        <script>
            function copyToken() {{
                var token = "{self.meta_token}";
                navigator.clipboard.writeText(token).then(function() {{
                    {alert}
                }}, function(err) {{
                    console.error('Could not copy text: ', err);
                }});
            }}
        </script>
        """
        return html

    def get_update_url(self):
        url = reverse("whatsapp-credential-update", kwargs={"pk": self.pk})
        return url

    def get_publish_button(self):
        html = render_template(
            path="whatsapp/option_buttons.html", context={"instance": self}
        )
        return html

    def get_primary(self):
        if self.is_primary:
            return "style='background:#ffa60028'"

    def get_instance(self):
        """
        used to return the id of the instance
        Returns:
            id of the instance
        """
        return self.pk

    def get_delete_url(self):
        url = reverse("whatsapp-credential-delete")
        id = self.pk
        url = f"{url}?id={id}"
        return url

    def get_test_message_url(self):
        url = reverse("send-test-message")
        return url

    def get_webhook_token(self):
        placeholder = "•" * len(self.meta_webhook_token)
        html = f"""
            <style>
                .editable-span {{
                    cursor: pointer;
                }}
                .editable-span::after {{
                    content: '{placeholder}';
                }}
                .editable-span:hover::after {{
                    content: '{self.meta_webhook_token}';
                }}
            </style>
            <span class="editable-span"></span>
            """
        return html


class WhatsappFlowDetails(models.Model):
    template = models.CharField(max_length=50)
    flow_id = models.CharField(max_length=50)
    whatsapp_id = models.ForeignKey(WhatsappCredientials, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.template
