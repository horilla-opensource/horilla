from collections import defaultdict

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
    result_page = paginator.get_page(page)
    # object_list is still a lazy, unevaluated queryset here. Row templates access
    # it more than once each (once per rendered cell), and each fresh iteration of
    # an unevaluated queryset re-queries instead of reusing prefetch_related's
    # cache, turning any prefetched relation into an N+1 across the whole page.
    # Materializing it once locks in that single evaluation for every later access.
    result_page.object_list = list(result_page.object_list)
    return result_page


def _page_from_list(items, page_name, request, records_per_page, total_count=None):
    """Build a Page from an already-fetched list (optionally with a larger total)."""
    page_number = request.GET.get(page_name) if request else None
    # Paginator over the full in-memory list for this grouper; when total_count is
    # larger we still only have the current page slice in `items`.
    paginator = Paginator(
        items if total_count is None else range(total_count), records_per_page
    )
    result_page = paginator.get_page(page_number)
    if total_count is not None:
        result_page.object_list = items
    else:
        result_page.object_list = list(result_page.object_list)
    return result_page


def generate_groups(
    request,
    groupers,
    queryset,
    page_name,
    group_field,
    is_fk_field,
    records_per_page=10,
):
    """
    groups generating method

    For FK groupers, fetch all rows for the visible groupers in one query, then
    split in Python — avoids per-group COUNT/SELECT round-trips.
    """
    groups = []
    if is_fk_field:
        grouper_ids = [grouper.id for grouper in groupers]
        if not grouper_ids:
            return groups

        # Preserve select_related / prefetch_related from the parent queryset.
        rows = list(queryset.filter(**{f"{group_field}__in": grouper_ids}))
        grouped = defaultdict(list)
        fk_attname = queryset.model._meta.get_field(group_field).attname
        for row in rows:
            grouped[getattr(row, fk_attname)].append(row)

        for grouper in groupers:
            group_rows = grouped.get(grouper.id, [])
            groups.append(
                {
                    "grouper": grouper,
                    "list": _page_from_list(
                        group_rows,
                        f"dynamic_page_{page_name}{grouper.id}",
                        request,
                        records_per_page,
                    ),
                    "dynamic_name": f"dynamic_page_{page_name}{grouper.id}",
                }
            )
    else:
        for grouper in groupers:
            group_queryset = queryset.filter(**{group_field: grouper})
            groups.append(
                {
                    "grouper": grouper,
                    "list": record_queryset_paginator(
                        request,
                        group_queryset,
                        f"dynamic_page_{page_name}{grouper}".replace(" ", "_"),
                        records_per_page,
                    ),
                    "dynamic_name": f"dynamic_page_{page_name}{grouper}".replace(
                        " ", "_"
                    ),
                }
            )
    return groups


def _ordered_unique(values):
    """Preserve first-seen order while dropping nulls/duplicates."""
    return [g for g in dict.fromkeys(values) if g is not None]


def _page_of_groupers(grouper_keys, page, records_per_page):
    """
    Paginate grouper keys first so generate_groups only runs for the
    visible page (avoids N exists/count queries for every recruitment).
    """
    paginator = Paginator(grouper_keys, records_per_page)
    page_obj = paginator.get_page(page)
    return page_obj, list(page_obj.object_list)


def _resolve_fk_groupers(model, ids):
    """Fetch related objects and keep the values_list encounter order."""
    if not ids:
        return []
    by_id = model.objects.in_bulk(ids)
    return [by_id[i] for i in ids if i in by_id]


def group_by_queryset(
    queryset, group_field, page=None, page_name="page", records_per_page=None
):
    """
    This method is used to make group-by and split groups by nested pagination
    """
    from base.methods import get_pagination

    if not records_per_page:
        records_per_page = get_pagination(default=10)

    fields_split = group_field.split("__")
    splitted = len(fields_split) > 1
    model = queryset.model
    is_fk_field = isinstance(
        getattr(model, group_field, None), ForwardManyToOneDescriptor
    )
    model_copy = model

    # getting request from the thread locals
    request = getattr(_thread_locals, "request", None)
    if splitted or is_fk_field:
        for field in fields_split:
            field_obj = model_copy._meta.get_field(field)
            model_copy = field_obj.related_model
        if model_copy:
            active_ids = _ordered_unique(queryset.values_list(group_field, flat=True))
            page_obj, page_ids = _page_of_groupers(active_ids, page, records_per_page)
            groupers = _resolve_fk_groupers(model_copy, page_ids)
            groups = generate_groups(
                request,
                groupers,
                queryset,
                page_name,
                group_field,
                is_fk_field=True,
                records_per_page=records_per_page,
            )
        else:
            groupers = _ordered_unique(queryset.values_list(group_field, flat=True))
            page_obj, page_groupers = _page_of_groupers(
                groupers, page, records_per_page
            )
            groups = generate_groups(
                request,
                page_groupers,
                queryset,
                page_name,
                group_field,
                is_fk_field=False,
                records_per_page=records_per_page,
            )

    else:
        raw_groupers = _ordered_unique(queryset.values_list(group_field, flat=True))
        related_model = getattr(
            queryset.model._meta.get_field(group_field), "related_model", None
        )
        page_obj, page_keys = _page_of_groupers(raw_groupers, page, records_per_page)
        if related_model and page_keys:
            groupers = _resolve_fk_groupers(related_model, page_keys)
        else:
            groupers = page_keys
        groups = generate_groups(
            request,
            groupers,
            queryset,
            page_name,
            group_field,
            is_fk_field=False,
            records_per_page=records_per_page,
        )

    # Keep paginator metadata (count/num_pages) for all groupers while only
    # materializing the current page of group payloads.
    page_obj.object_list = groups
    return page_obj
