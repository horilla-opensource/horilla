"""
horilla_views/generic/cbv/kanban.py
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models

from horilla_views.cbv_methods import get_nested_field
from horilla_views.generic.cbv.views import HorillaCardView


class HorillaKanbanView(HorillaCardView):
    group_key: str = ""
    group_filter_class = None
    template_name: str = "generic/horilla_kanban_view.html"
    kanban_attrs: str = ""
    instance_order_by: str = "sequence"
    group_order_by: str = "sequence"
    records_per_page: int = 10
    custom_card_content_template: str = ""
    group_actions: list = []
    show_kanban_confirmation: bool = True
    folded_groups: list = []
    action_method: str = """"""

    def get_related_groups(self, *args, **kwargs):
        related_groups = self.group_filter_class(self.request.GET).qs
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
            field = get_nested_field(self.model, self.group_key)

            if isinstance(
                field, (models.ForeignKey, models.OneToOneField, models.OneToOneRel)
            ):
                queryset = queryset.prefetch_related(self.group_key)
                related_groups = self.get_related_groups()

            elif hasattr(field, "choices") and field.choices:
                related_groups = [
                    type(
                        "Choice",
                        (),
                        {"pk": choice[0], "__str__": (lambda self, val=choice[1]: val)},
                    )()
                    for choice in field.choices
                ]
                context["is_choice_group"] = True

            else:
                related_groups = []

            # Group items
            for related_item in related_groups:
                grouped_items[related_item.pk] = {
                    "label": related_item,
                    "items": queryset.filter(**{f"{self.group_key}": related_item.pk}),
                }

            # Sort groups to match original order
            sorted_items = {
                ri.pk: grouped_items[ri.pk]
                for ri in related_groups
                if ri.pk in grouped_items
            }

            # Paginate each group
            for key, group in sorted_items.items():
                try:
                    ordered_items = group["items"].order_by(self.instance_order_by)
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
