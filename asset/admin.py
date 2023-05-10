from django.contrib import admin
from .models import Asset,AssetCategory,AssetRequest,AssetAssignment,AssetLot
# Register your models here.


admin.site.register(Asset)
admin.site.register(AssetRequest)
admin.site.register(AssetCategory)
admin.site.register(AssetAssignment)
admin.site.register(AssetLot)