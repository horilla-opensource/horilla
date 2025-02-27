from django.contrib import admin

from dynamic_fields.models import Choice, DynamicField

# Register your models here.


admin.site.register(DynamicField)
admin.site.register(Choice)
