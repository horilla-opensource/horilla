import django_filters

from horilla.filters import HorillaFilterSet
from whatsapp.models import WhatsappCredientials


class CredentialsViewFilter(HorillaFilterSet):
    search = django_filters.CharFilter(
        field_name="meta_phone_number", lookup_expr="icontains"
    )

    class Meta:
        model = WhatsappCredientials
        fields = ["meta_phone_number", "search"]
