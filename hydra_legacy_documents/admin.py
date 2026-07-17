from django.contrib import admin

from hydra_legacy_documents.models import Document, DocumentRequest

# Register your models here.
admin.site.register(Document)
admin.site.register(DocumentRequest)
