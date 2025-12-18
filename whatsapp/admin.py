from django.contrib import admin

from whatsapp.models import WhatsappCredientials, WhatsappFlowDetails

# Register your models here.
admin.site.register(WhatsappCredientials)
admin.site.register(WhatsappFlowDetails)
