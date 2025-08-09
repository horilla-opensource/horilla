"""
horilla_views/generic/cbv/kanban.py
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models

from horilla_views.generic.cbv.views import HorillaCardView


class KanbanView(HorillaCardView):
    group_key: str = ""
    template_name: str = "generic/horilla_kanban_view.html"
    kanban_attrs: str = ""
    records_per_page: int = 10
    custom_card_content_template: str = ""
    group_actions: list = []
    show_kanban_confirmation: bool = True
    folded_groups: list = []

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
        context["tab_id"] = self.kwargs.get("pk", None)

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
                    try:
                        ordered_items = group["items"].order_by("sequence")
                    except:
                        ordered_items = group["items"].order_by("pk")
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
