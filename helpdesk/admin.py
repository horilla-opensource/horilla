from django.contrib import admin

from helpdesk.models import (
    Ticket,
    TicketType,
    Comment,
    FAQ,
    FAQCategory,
    Attachment,
    DepartmentManager,
)

# Register your models here.
admin.site.register(Ticket)
admin.site.register(TicketType)
admin.site.register(Comment)
admin.site.register(FAQ)
admin.site.register(FAQCategory)
admin.site.register(Attachment)
admin.site.register(DepartmentManager)
