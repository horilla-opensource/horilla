from django.contrib import admin
from onboarding.models import OnboardingStage, OnboardingTask, CandidateStage, CandidateTask, OnboardingPortal

admin.site.register(OnboardingStage)
admin.site.register(OnboardingTask)
admin.site.register(CandidateStage)
admin.site.register(CandidateTask)
admin.site.register(OnboardingPortal)

