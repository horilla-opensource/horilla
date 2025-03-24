"""
dynamic_fields/views.py
"""

from django.contrib import messages
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from dynamic_fields import forms, models
from dynamic_fields.methods import structured
from horilla.decorators import login_required, permission_required
from horilla_views.generic.cbv.views import HorillaFormView


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("dynamic_fields.change_mailautomation"), name="dispatch"
)
class ChoiceFormView(HorillaFormView):
    """
    ChoiceFormView
    """

    model = models.DynamicField
    form_class = forms.ChoiceForm
    is_dynamic_create_view = True


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("dynamic_fields.change_mailautomation"), name="dispatch"
)
class DynamicFieldFormView(HorillaFormView):
    """
    DynamicFieldFormView
    """

    model = models.DynamicField
    form_class = forms.DynamicFieldForm
    template_name = "dynamic_fields/form.html"
    # dynamic_create_fields = [
    #     ("choices", ChoiceFormView),
    # ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        setattr(self.form_class, "structured", structured)

    def form_valid(self, form: forms.DynamicFieldForm) -> HttpResponse:
        model_path = self.request.GET["df_model_path"]
        if form.is_valid():
            if not form.instance.pk:
                form.instance.model = model_path
            message = _("New field added")
            form.save()

            messages.success(self.request, message)
            return self.HttpResponse("<script>window.location.reload()</script>")
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("dynamic_fields.change_mailautomation"), name="dispatch"
)
class RemoveDf(View):
    """
    RemoveDf view
    """

    def post(self, *args, **kwargs):
        """
        Post method
        """
        pk = self.request.POST["pk"]
        df = models.DynamicField.objects.get(pk=pk)
        df.remove_column = True
        df.save()
        return HttpResponse({"type": "success"})
