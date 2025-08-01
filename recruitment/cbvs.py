from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla.decorators import login_required, permission_required
from horilla_views.generic.cbv import views
from recruitment import models
from recruitment.filters import LinkedInAccountFilter
from recruitment.forms import LinkedInAccountForm


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.view_linkedinaccount"), name="dispatch"
)
class LinkedinSettingSectionView(views.HorillaSectionView):
    """
    LinkedinSetting SectionView
    """

    nav_url = reverse_lazy("linkedin-setting-nav")
    view_url = reverse_lazy("linkedin-setting-list")
    view_container_id = "listContainer"

    # script_static_paths = [
    #     "static/automation/automation.js",
    # ]

    template_name = "settings/linkedin/linkedin_setting_section.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.view_linkedinaccount"), name="dispatch"
)
class LinkedInSettingNavView(views.HorillaNavView):
    """
    LinkedInSetting nav view
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.create_attrs = f"""
            hx-get="{reverse_lazy("create-linkedin-account")}"
            hx-target="#genericModalBody"
            data-toggle="oh-modal-toggle"
            data-target="#genericModal"
        """

    nav_title = _("LinkedIn Accounts")
    search_url = reverse_lazy("linkedin-setting-list")
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.change_linkedinaccount"), name="dispatch"
)
class LinkedInAccountFormView(views.HorillaFormView):
    """
    LinkedInForm View
    """

    form_class = LinkedInAccountForm
    model = models.LinkedInAccount
    new_display_title = _("Create") + " " + model._meta.verbose_name

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = models.LinkedInAccount.objects.filter(pk=self.kwargs["pk"]).first()
        kwargs["instance"] = instance
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = (
                _("Update") + " " + self.model._meta.verbose_name
            )
        return context

    def form_invalid(self, form: Any) -> HttpResponse:

        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: LinkedInAccountForm) -> views.HttpResponse:
        if form.is_valid():
            message = "LinkedIn account added."
            if form.instance.pk:
                message = "LinkedIn account updated."
            form.save()

            messages.success(self.request, _(message))
            return self.HttpResponse()

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("recruitment.view_linkedinaccount"), name="dispatch"
)
class LinkedInSettingListView(views.HorillaListView):
    """
    LinkedInSetting list view
    """

    model = models.LinkedInAccount
    search_url = reverse_lazy("linkedin-setting-list")
    filter_class = LinkedInAccountFilter
    action_method = "action_template"

    columns = [
        "username",
        "email",
        "company_id",
        ("Is Active", "is_active_toggle"),
    ]
