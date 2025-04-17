from django.contrib import admin

# Register your models here.

from dynamic_fields.models import Choice, DynamicField

admin.site.register(DynamicField)
admin.site.register(Choice)
