from django.contrib import admin

from horilla_meet import models

# Register your models here.
admin.site.register(models.GoogleCredential)
admin.site.register(models.GoogleCloudCredential)
admin.site.register(models.GoogleMeeting)
