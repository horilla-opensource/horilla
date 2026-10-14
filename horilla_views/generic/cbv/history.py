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
from horilla.http.response import HorillaRedirect
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
        tracking = None
        log_entries = None
        if self.history_related_name:
            tracking = get_diff(instance, self.history_related_name)
        # Prefer simple-history when it produced entries; otherwise use auditlog.
        if tracking:
            context["tracking"] = tracking
            context["log_entries"] = None
        elif hasattr(instance, "horilla_history"):
            context["tracking"] = None
            context["log_entries"] = instance.horilla_history.all().order_by(
                "-timestamp"
            )
        else:
            context["tracking"] = tracking
            context["log_entries"] = log_entries
        context["model"] = (
            f"{self.model._meta.app_label}.{self.model._meta.object_name}"
        )
        context["has_perm_to_revert"] = self.has_perm_to_revert
        return context

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        request = getattr(_thread_locals, "request", None)
        self.request = request

    def get_queryset(self):
        """
        The company-scoped queryset. It already covers "All my companies"
        (every company the user belongs to); _base_manager, used before,
        reached other companies' rows. get_queryset(), not all(): the
        manager's all() also hides inactive employees' records.
        """
        if self.model is not None:
            return self.model._default_manager.get_queryset()
        return super().get_queryset()

    def history_owner(self, instance):
        """
        The employee a record belongs to, so they and their managers can see
        its history without the model's view permission. Subclasses override
        this where the link to the employee is indirect.
        """
        from employee.models import Employee

        if isinstance(instance, Employee):
            return instance
        owner = getattr(instance, "employee_id", None)
        return owner if isinstance(owner, Employee) else None

    def can_view_history(self, instance):
        """
        This view serves any model from ?model=, so it can't rely on a
        per-model decorator: the model's view permission, or the record being
        the user's own or someone's they manage. Only logging in was checked
        before, so any employee could read (and revert) any record's history.
        """
        from base.methods import check_manager

        user = self.request.user
        opts = instance._meta
        if user.has_perm(f"{opts.app_label}.view_{opts.model_name}"):
            return True
        employee = getattr(user, "employee_get", None)
        owner = self.history_owner(instance)
        return bool(
            employee and owner and (owner == employee or check_manager(employee, owner))
        )

    def _resolve_model(self, request):
        """The model named by ?model=app.Model, or None if it isn't one."""
        try:
            app_label, model_name = request.GET.get("model", "").split(".")
            return apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            return None

    def get(self, request, *args, **kwargs):
        """
        Resolve the model dynamically when a subclass hasn't set one, so a
        single URL/view can serve the history sidebar for any model.
        """
        if not self.model:
            self.model = self._resolve_model(request)
        if not self.model:
            # No ?model=app.Model on the request and no subclass default --
            # get_queryset() has nothing to query, and Django's own
            # fallback raises ImproperlyConfigured (an unhandled 500)
            # rather than a normal response.
            messages.error(request, _("Invalid model parameter format."))
            return HorillaFormView.HttpResponse()
        # Prefer HistoryManager when present; history_set is only the reverse FK.
        if hasattr(self.model, "history") and hasattr(
            getattr(self.model, "history"), "model"
        ):
            self.history_related_name = "history"
        elif hasattr(self.model, "history_set"):
            self.history_related_name = "history_set"
        elif hasattr(self.model, "history"):
            self.history_related_name = "history"
        else:
            self.history_related_name = None
        instance = self.get_queryset().filter(pk=kwargs.get("pk")).first()
        if instance is None or not self.can_view_history(instance):
            messages.info(request, _("You don't have permission."))
            return HorillaFormView.HttpResponse()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Revert
        """
        history_id = kwargs.get("history_id")
        self.model = self._resolve_model(request)
        if not self.model:
            messages.error(request, _("Missing model parameter."))
            return HorillaRedirect(request)
        opts = self.model._meta
        instance = self.get_queryset().filter(pk=kwargs.get("pk")).first()
        # Reverting rewrites the record, so it takes the change permission,
        # on a record the user can reach -- only logging in was checked, and
        # the <pk> in the URL was ignored entirely.
        if instance is None or not request.user.has_perm(
            f"{opts.app_label}.change_{opts.model_name}"
        ):
            messages.info(request, _("You don't have permission."))
            return HorillaFormView.HttpResponse()
        try:
            history_model = get_history_model_for_model(self.model)
        except Exception:
            history_model = None
        history = (
            history_model.objects.filter(history_id=history_id).first()
            if history_model
            else None
        )
        # The snapshot must be of this record, not any row of the model.
        if not history or history.instance.pk != instance.pk:
            messages.error(request, _("History record not found."))
            return HorillaRedirect(request)
        history.instance.save()
        messages.success(request, _("History reverted"))

        return HorillaFormView.HttpResponse()
