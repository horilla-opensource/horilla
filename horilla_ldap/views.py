from django.shortcuts import render

# Create your views here.

from horilla.decorators import login_required
from .models import LDAPSettings
from .forms import LDAPSettingsForm
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django.contrib import messages


@login_required
def ldap_settings_view(request):
    settings = LDAPSettings.objects.first()
    if request.method == "POST":
        form = LDAPSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, _("Configuration updated successfully."))
            return render(request, "ldap_settings.html", {"form": form})
    else:
        form = LDAPSettingsForm(instance=settings)

    return render(request, "ldap_settings.html", {"form": form})
