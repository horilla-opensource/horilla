"""
This page handles the cbv methods for mail template page
"""

from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from base.forms import MailTemplateForm
from base.models import HorillaMailTemplate
from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView, HorillaNavView


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.add_horillamailtemplate"), name="dispatch")
class MailTemplateFormView(HorillaFormView):
    """
    form view for create and edit mail template
    """

    form_class = MailTemplateForm
    model = HorillaMailTemplate
    template_name = "cbv/mail_template/form_inherit.html"
    new_display_title = _("Add Template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Template")

        return context

    def form_valid(self, form: MailTemplateForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Template Updated")
            else:
                message = _("Template created")
            form.save()

            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("base.add_horillamailtemplate"), name="dispatch")
class MailTemplateDuplicateForm(HorillaFormView):
    """
    from view for duplicate mail templates
    """

    model = HorillaMailTemplate
    form_class = MailTemplateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        original_object = HorillaMailTemplate.objects.get(id=self.kwargs["pk"])
        form = self.form_class(instance=original_object)

        for field_name, field in form.fields.items():
            if isinstance(field, forms.CharField):
                initial_value = form.initial.get(field_name, "")
                if initial_value:
                    initial_value += " (copy)"
                form.initial[field_name] = initial_value
                form.fields[field_name].initial = initial_value

        if hasattr(form.instance, "id"):
            form.instance.id = None

        context["form"] = form
        self.form_class.verbose_name = _("Duplicate Template")
        return context

    def form_invalid(self, form: Any) -> HttpResponse:
        self.form_class.verbose_name = _("Duplicate Template")
        if not form.is_valid():
            errors = form.errors.as_data()
            return render(
                self.request, self.template_name, {"form": form, "errors": errors}
            )
        return super().form_invalid(form)

    def form_valid(self, form: MailTemplateForm) -> HttpResponse:
        form = self.form_class(self.request.POST)
        self.form_class.verbose_name = _("Duplicate Template")
        if form.is_valid():
            message = _("Template Added")
            messages.success(self.request, message)
            form.save()
            return self.HttpResponse("<script>window.location.reload()</script>")
        return self.form_invalid(form)


class MailTemplateNavView(HorillaNavView):
    """
    Mail Template Nav View
    """

    nav_title = _("Mail Templates")
    search_url = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.create_attrs = f"""
            hx-get="{reverse_lazy('mail-template-create-form')}"
            data-toggle="oh-modal-toggle"
            data-target="#objectCreateModal"
            hx-target="#objectCreateModalTarget"
        """
