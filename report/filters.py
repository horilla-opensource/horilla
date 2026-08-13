import django_filters

from horilla.filters import FilterSet
from report.models import ReportRunLog


class ReportAuditFilter(FilterSet):
    report_slug = django_filters.CharFilter(
        field_name="report_slug", lookup_expr="icontains"
    )
    q = django_filters.CharFilter(method="filter_by_user")

    class Meta:
        model = ReportRunLog
        fields = ["action", "report_slug", "q"]

    def filter_by_user(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(
            Q(user__username__icontains=value) | Q(user__email__icontains=value)
        )
