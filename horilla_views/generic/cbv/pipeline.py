"""
horilla_views/generic/cbv/pipeline
"""

from django.db import models
from django.views.generic import ListView
from django_filters import FilterSet

from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import get_short_uuid


class Pipeline(ListView):
    """
    Pipeline
    """

    model: models.Model = None
    filter_class: FilterSet = None
    field: str = ""
    field_filter_class: FilterSet = None
    field_model: models.Model = None
    selected_instances_key_name: str = ""
    allowed_fields: list = []
    columns: list = []
    view_id: str = get_short_uuid(10, "pipeline")
    actions: list = []

    template_name = "generic/pipeline/pipeline.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.request = getattr(_thread_locals, "request", None)
        self.grouper = self.request.GET.get("grouper", self.grouper)
        if kwargs.get("view") == "kanban":
            self.template_name = "generic/pipeline/kanban.html"
        for allowed_field in self.allowed_fields:
            if self.grouper == allowed_field["field"]:
                self.field_model = allowed_field["model"]
                self.field_filter_class = allowed_field["filter"]
                self.url = allowed_field["url"]
                self.parameters = allowed_field["parameters"]
                self.actions = allowed_field["actions"]

    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            # Inject URL params into initkwargs
            initkwargs_with_url = {**initkwargs, **kwargs}
            self = cls(**initkwargs_with_url)
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        return view

    def get_queryset(self):
        if self.kwargs.get("view"):
            del self.kwargs["view"]

        if not self.queryset:
            self.queryset = self.field_filter_class(self.request.GET).qs.filter(
                **self.kwargs
            )
        return self.queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context["groups"] = self.queryset
        context["view_id"] = self.view_id
        context["allowed_fields"] = self.allowed_fields
        context["url"] = self.url
        context["parameters"] = self.parameters
        context["actions"] = self.actions
        context["selected_instances_key_name"] = self.selected_instances_key_name
        return context
