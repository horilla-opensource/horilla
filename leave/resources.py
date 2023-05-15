from import_export import resources
from .models import Holiday


class HolidayResource(resources.ModelResource):
    class Meta:
        model = Holiday