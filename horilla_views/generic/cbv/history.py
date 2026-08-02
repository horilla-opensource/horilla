"""
horilla_views/generic/cbv/history.py
"""

from django.apps import apps
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import DetailView
from simple_history.utils import get_history_model_for_model

from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import hx_request_required, login_required
from horilla_views.generic.cbv.views import HorillaFormView
from horilla_views.history_methods import get_diff


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class HorillaHistoryView(DetailView):
    """
    GenericHorillaHistoryView
    """

    template_name = "generic/horilla_history_view.html"
    has_perm_to_revert = False
    fields: list = []
    history_related_name = "history"

    def get_context_data(self, **kwargs):
        """
        Get context data
        """
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        if self.history_related_name:
            context["tracking"] = get_diff(instance, self.history_related_name)
            context["log_entries"] = None
        else:
            context["tracking"] = None
            context["log_entries"] = instance.horilla_history.all().order_by(
                "-timestamp"
            )
        context["model"] = (
            f"{self.model._meta.app_label}.{self.model._meta.object_name}"
        )
        context["has_perm_to_revert"] = self.has_perm_to_revert
        return context

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request

    def get(self, request, *args, **kwargs):
        """
        Resolve the model dynamically when a subclass hasn't set one, so a
        single URL/view can serve the history sidebar for any model.
        """
        if not self.model:
            model_param = request.GET.get("model")
            if model_param:
                app_label, model_name = model_param.split(".")
                self.model = apps.get_model(app_label, model_name)
        if hasattr(self.model, "history_set"):
            self.history_related_name = "history_set"
        elif hasattr(self.model, "history"):
            self.history_related_name = "history"
        else:
            self.history_related_name = None
        return super().get(request, *args, **kwargs)

    def post(self, request, history_id, *args, **kwargs):
        """
        Revert
        """
        app, model = request.GET["model"].split(".")
        self.model = apps.get_model(app, model)

        history = get_history_model_for_model(self.model).objects.get(
            history_id=history_id
        )
        history.instance.save()
        messages.success(request, _("History reverted"))

        return HorillaFormView.HttpResponse()
