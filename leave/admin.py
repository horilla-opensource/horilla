from django.contrib import admin
from .models import *



# Register your models here.
admin.site.register(LeaveType)
admin.site.register(LeaveRequest)
admin.site.register(AvailableLeave)
admin.site.register(Holiday)
admin.site.register(CompanyLeave)

