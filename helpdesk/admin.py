from django.contrib import admin

from helpdesk.models import (
    FAQ,
    Attachment,
    Comment,
    DepartmentManager,
    FAQCategory,
    Ticket,
    TicketType,
)

# Register your models here.
admin.site.register(Ticket)
admin.site.register(TicketType)
admin.site.register(Comment)
admin.site.register(FAQ)
admin.site.register(FAQCategory)
admin.site.register(Attachment)
admin.site.register(DepartmentManager)
