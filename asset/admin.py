"""
Module: admin.py
Description: This module is responsible for registering models
            to be managed through the Django admin interface.
Models Registered:
- Asset: Represents a physical asset with relevant details.
- AssetCategory: Categorizes assets for better organization.
- AssetRequest: Manages requests for acquiring assets.
- AssetAssignment: Tracks the assets assigned to employees.
- AssetLot: Represents a collection of assets under a lot number.
"""

from django.contrib import admin

from .models import (
    Asset,
    AssetAssignment,
    AssetCategory,
    AssetDocuments,
    AssetLot,
    AssetReport,
    AssetRequest,
)

# Register your models here.


admin.site.register(Asset)
admin.site.register(AssetRequest)
admin.site.register(AssetCategory)
admin.site.register(AssetAssignment)
admin.site.register(AssetLot)
admin.site.register(AssetReport)
admin.site.register(AssetDocuments)
