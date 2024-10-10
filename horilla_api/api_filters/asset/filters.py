import django_filters
from django_filters import FilterSet

from asset.models import *


class AssetCategoryFilter(FilterSet):

    search = django_filters.CharFilter(
        field_name="asset_category_name", lookup_expr="icontains"
    )

    class Meta:
        model = AssetCategory
        fields = "__all__"
