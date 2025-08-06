"""
horilla_views/generic/cbv/pipeline
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.views.generic import ListView
from django_filters import FilterSet

from horilla.horilla_middlewares import _thread_locals
from horilla_views.cbv_methods import get_short_uuid

from .views import HorillaCardView


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


class KanbanView(HorillaCardView):
    group_key: str = ""
    template_name: str = "generic/horilla_kanban_view.html"
    kanban_attrs: str = ""
    records_per_page: int = 10
    custom_card_content_template: str = ""
    group_actions: list = []

    def get_related_groups(self, *args, **kwargs):
        field = self.model._meta.get_field(self.group_key)

        related_model = field.related_model
        if "sequence" in [f.name for f in related_model._meta.fields]:
            related_groups = related_model.objects.all().order_by("sequence")
        else:
            related_groups = related_model.objects.all().order_by("pk")

        return related_groups

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.queryset

        app_label = self.model._meta.app_label if self.model else ""
        model_name = self.model.__name__ if self.model else ""
        context["app_label"] = app_label
        context["model_name"] = model_name

        grouped_items = {}
        paginated_groups = {}

        try:
            field = self.model._meta.get_field(self.group_key)

            if isinstance(field, models.ForeignKey):
                queryset = queryset.prefetch_related(self.group_key)

                related_groups = self.get_related_groups()
                for related_item in related_groups:
                    grouped_items[related_item.pk] = {
                        "label": related_item,
                        "items": queryset.filter(
                            **{f"{self.group_key}__pk": related_item.pk}
                        ),
                    }

                sorted_items = {}
                for related_item in related_groups:
                    if related_item.pk in grouped_items:
                        sorted_items[related_item.pk] = grouped_items[related_item.pk]

                for key, group in sorted_items.items():
                    total_count = group["items"].count()
                    ordered_items = group["items"].order_by("sequence", "pk")
                    paginator = Paginator(ordered_items, self.records_per_page)
                    page = self.request.GET.get(f"page_{key}", 1)

                    try:
                        page_obj = paginator.page(page)
                    except PageNotAnInteger:
                        page_obj = paginator.page(1)
                    except EmptyPage:
                        page_obj = paginator.page(paginator.num_pages)

                    paginated_groups[key] = {
                        "label": group["label"],
                        "page_obj": page_obj,
                        "total_count": total_count,
                    }

            context.update(
                {
                    "grouped_items": paginated_groups,
                    "actions": self.actions,
                    "filter_class": self.filter_class.__name__,
                    "group_by_field": self.group_key,
                    "kanban_attrs": self.kanban_attrs,
                }
            )

        except Exception as e:
            print(f"Error in KanbanViewItems: {e}")

        return context
