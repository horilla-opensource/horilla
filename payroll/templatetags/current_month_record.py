from datetime import date, datetime, timedelta

from django import template

register = template.Library()


@register.filter(name="current_month_record")
def current_month_record(queryset):
    current_month_start_date = datetime.now().replace(day=1)
    next_month_start_date = current_month_start_date + timedelta(days=31)

    return queryset.filter(
        start_datetime__gte=current_month_start_date,
        start_datetime__lt=next_month_start_date,
    ).order_by("start_datetime")


@register.filter
def get_item(list, i):
    try:
        return list[i]
    except:
        return None
