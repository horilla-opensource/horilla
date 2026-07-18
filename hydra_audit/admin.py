"""
admin.py
"""

from django.contrib import admin

from hydra_audit.models import AuditTag, HydraAuditInfo, HydraAuditLog

# Register your models here.

admin.site.register(AuditTag)
