from django.contrib import admin

# Register your models here.
from .models import LDAPSettings

admin.site.register(LDAPSettings)
