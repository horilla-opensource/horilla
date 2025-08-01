from django.core.paginator import Paginator
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor

from horilla.horilla_middlewares import _thread_locals


def record_queryset_paginator(request, queryset, page_name, records_per_page=10):
    """
    Returns paginated results with safe ordering.
    """
    # 803
    if not queryset.ordered:
        if hasattr(queryset.model, "created_at"):
            queryset = queryset.order_by("-created_at")
        else:
            queryset = queryset.order_by("-id")

    page = request.GET.get(page_name)
    paginator = Paginator(queryset, records_per_page)
    return paginator.get_page(page)


def generate_groups(request, groupers, queryset, page_name, group_field, is_fk_field):
    """
    groups generating method
    """
    groups = []
    if is_fk_field:
        for grouper in groupers:
            group_queryset = queryset.filter(**{group_field: grouper.id})
            # to avoid zero records groupings
            if group_queryset.count():
                group_info = {
                    "grouper": grouper,
                    "list": record_queryset_paginator(
                        request,
                        group_queryset,
                        f"dynamic_page_{page_name}{grouper.id}",
                    ),
                    "dynamic_name": f"dynamic_page_{page_name}{grouper.id}",
                }
                groups.append(group_info)
    else:
        for grouper in groupers:
            group_queryset = queryset.filter(**{group_field: grouper})
            # to avoid zero records groupings
            if group_queryset.count():
                group = {
                    "grouper": grouper,
                    "list": record_queryset_paginator(
                        request,
                        group_queryset,
                        f"dynamic_page_{page_name}{grouper}".replace(" ", "_"),
                    ),
                    "dynamic_name": f"dynamic_page_{page_name}{grouper}".replace(
                        " ", "_"
                    ),
                }
                groups.append(group)
    return groups


def group_by_queryset(
    queryset, group_field, page=None, page_name="page", records_per_page=10
):
    """
    This method is used to make group-by and split groups by nested pagination
    """
    from base.methods import get_pagination

    if get_pagination() != 50:
        records_per_page = get_pagination()

    fields_split = group_field.split("__")
    splitted = len(fields_split) > 1
    model = queryset.model
    is_fk_field = isinstance(
        getattr(model, group_field, None), ForwardManyToOneDescriptor
    )
    model_copy = model
    field_obj = None

    # getting request from the thread locals
    request = getattr(_thread_locals, "request", None)
    if splitted or is_fk_field:
        for field in fields_split:
            field_obj = model_copy._meta.get_field(field)
            model_copy = field_obj.related_model
        if model_copy:
            groupers = model_copy.objects.all()
            groups = generate_groups(
                request,
                groupers,
                queryset,
                page_name,
                group_field,
                is_fk_field=True,
            )
        else:
            groupers = [
                item
                for index, item in enumerate(
                    queryset.values_list(group_field, flat=True)
                )
                if item not in queryset.values_list(group_field, flat=True)[:index]
            ]
            groups = generate_groups(
                request, groupers, queryset, page_name, group_field, is_fk_field=False
            )

    else:
        # making unique | not using set(groupers) due to ordering issue
        groupers = [
            item
            for index, item in enumerate(queryset.values_list(group_field, flat=True))
            if item not in queryset.values_list(group_field, flat=True)[:index]
        ]
        # getting related queryset
        related_model = queryset.model._meta.get_field(group_field).related_model
        if related_model:
            groupers = related_model.objects.filter(id__in=groupers)
        groups = generate_groups(
            request, groupers, queryset, page_name, group_field, is_fk_field=False
        )

    groups = Paginator(groups, records_per_page)
    return groups.get_page(page)
