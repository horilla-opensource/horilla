from import_export import resources
from .models import Asset

class AssetResource(resources.ModelResource):
    class Meta:
        model = Asset