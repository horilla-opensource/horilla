"""
admin.py

This page is used to register the model with admins site.
"""
from django.contrib import admin
from recruitment.models import Stage, Recruitment, Candidate


# Register your models here.


admin.site.register(Stage)
admin.site.register(Recruitment)
admin.site.register(Candidate)
