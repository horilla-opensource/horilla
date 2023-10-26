"""
admin.py
"""
from django.contrib import admin
from horilla_audit.models import HorillaAuditLog, HorillaAuditInfo, AuditTag

# Register your models here.

admin.site.register(AuditTag)
