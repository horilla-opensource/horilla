"""
horilla_views/generic/cbv/history.py
"""

from django.apps import apps
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from simple_history.utils import get_history_model_for_model

from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import hx_request_required
from horilla_views.generic.cbv.views import HorillaFormView
from horilla_views.history_methods import get_diff


@method_decorator(hx_request_required, name="dispatch")
class HorillaHistoryView(DetailView):
    """
    GenericHorillaProfileView
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
        context["tracking"] = get_diff(instance, self.history_related_name)
        context["model"] = (
            f"{self.model._meta.app_label}.{self.model._meta.object_name}"
        )
        context["has_perm_to_revert"] = self.has_perm_to_revert
        return context

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request

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
        messages.success(request, "History reverted")

        return HorillaFormView.HttpResponse()
