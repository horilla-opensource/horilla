"""
outlook_auth/models.py
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company
from horilla_views.cbv_methods import render_template
from outlook_auth.methods import sec_to_hm

# Create your models here.


class AzureApi(models.Model):
    """
    AzureApi
    """

    outlook_client_id = models.CharField(max_length=200, verbose_name=_("Client ID"))
    outlook_client_secret = models.CharField(
        max_length=200, verbose_name=_("Client Secret")
    )
    outlook_tenant_id = models.CharField(max_length=200, verbose_name=_("Tenant ID"))
    outlook_email = models.EmailField(verbose_name=_("Email"))
    outlook_display_name = models.CharField(
        max_length=25, verbose_name=_("Display Name")
    )
    outlook_redirect_uri = models.URLField(verbose_name=("Redirect URi"))
    outlook_authorization_url = models.URLField(
        default="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        verbose_name="OAuth authorization endpoint",
    )
    outlook_token_url = models.URLField(
        default="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        verbose_name="OAuth token endpoint",
    )
    outlook_api_endpoint = models.URLField(
        default="https://graph.microsoft.com/v1.0",
        verbose_name="Microsoft Graph API endpoint",
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    token = models.JSONField(editable=False, default=dict)
    oauth_state = models.CharField(editable=False, max_length=100, null=True)
    last_refreshed = models.DateTimeField(null=True, editable=False)

    def save(self, *args, **kwargs):
        if self.is_primary:
            AzureApi.objects.filter(is_primary=True).update(is_primary=False)
        elif not AzureApi.objects.filter(is_primary=True).first():
            self.is_primary = True
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.outlook_display_name} <{self.outlook_email}>"

    def actions(self):
        return render_template("outlook/actions.html", {"instance": self})

    def token_expire(self):
        """
        last authenticated
        """

        if self.last_refreshed:
            duration_seconds = (timezone.now() - self.last_refreshed).seconds
            display = sec_to_hm(duration_seconds)
            expires_in_seconds = self.token.get("expires_in")
            if duration_seconds > expires_in_seconds:
                return _("Expired⚠️")
            return f"{display}/{sec_to_hm(expires_in_seconds)}"

    def is_token_expired(self):
        """
        is token expired
        """
        if self.last_refreshed:
            duration_seconds = (timezone.now() - self.last_refreshed).seconds
            expires_in_seconds = self.token.get("expires_in")
            if duration_seconds > expires_in_seconds:
                return True
            return False
