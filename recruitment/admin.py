from django.contrib import admin
from .models import Stage, Recruitment, Candidate
from simple_history.admin import SimpleHistoryAdmin


# Register your models here.

class CandidateHistoryAdmin(SimpleHistoryAdmin):
    list_display = ['name','stage_id']

admin.site.register(Stage)
admin.site.register(Recruitment)
admin.site.register(Candidate,CandidateHistoryAdmin)
