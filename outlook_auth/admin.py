"""
outlook_auth/admin.py
"""

from django.contrib import admin

from outlook_auth import models

# Register your models here.


admin.site.register(
    [
        models.AzureApi,
    ]
)
